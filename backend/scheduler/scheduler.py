"""
SmartFarm AI - Scheduler (Phase 14)
APScheduler-based reminder system for irrigation, weather, and crop alerts.
"""
import logging
from datetime import datetime, date
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models import User, Farm, Notification, NotificationType, NotificationChannel
from backend.notifications.telegram_service import telegram_service
from backend.agriculture.irrigation_engine import irrigation_engine
from backend.agriculture.risk_engine import risk_engine

logger = logging.getLogger(__name__)


class FarmScheduler:
    """
    Manages scheduled notification jobs.
    Runs in-process with APScheduler (no Redis/Celery needed).
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
        self._weather_service = None

    def set_weather_service(self, ws):
        self._weather_service = ws

    def start(self):
        """Add all jobs and start the scheduler."""
        # Morning irrigation check — 6:00 AM IST
        self.scheduler.add_job(
            self._run_irrigation_check,
            "cron", hour=6, minute=0,
            id="irrigation_check",
            replace_existing=True,
        )

        # Weather alert check — every 3 hours
        self.scheduler.add_job(
            self._run_weather_alerts,
            "cron", hour="6,9,12,15,18",
            id="weather_alerts",
            replace_existing=True,
        )

        # Daily crop reminder — 7:00 AM IST
        self.scheduler.add_job(
            self._run_crop_reminders,
            "cron", hour=7, minute=0,
            id="crop_reminders",
            replace_existing=True,
        )

        # Daily summary — 8:00 PM IST
        self.scheduler.add_job(
            self._run_daily_summary,
            "cron", hour=20, minute=0,
            id="daily_summary",
            replace_existing=True,
        )

        self.scheduler.start()
        logger.info("FarmScheduler started with 4 jobs.")

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("FarmScheduler stopped.")

    # ── Jobs ──

    async def _run_irrigation_check(self):
        """Check all farms and send irrigation reminders if needed."""
        logger.info("Scheduler: Running irrigation check")
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                User.telegram_connected == True,
                User.notify_irrigation == True,
            ).all()

            for user in users:
                for farm in user.farms:
                    try:
                        await self._process_irrigation_for_farm(db, user, farm)
                    except Exception as e:
                        logger.error(f"Irrigation check failed for farm {farm.id}: {e}")
        finally:
            db.close()

    async def _process_irrigation_for_farm(self, db: Session, user: User, farm: "Farm"):
        current_weather = {}
        forecast_days = []
        if self._weather_service:
            try:
                current_weather = await self._weather_service.get_current_weather(farm.location)
                forecast = await self._weather_service.get_forecast(farm.location, 3)
                forecast_days = forecast.get("days", [])
            except Exception as e:
                logger.warning(f"Weather unavailable for {farm.location}: {e}")
                return

        soil = farm.soil_profile
        soil_type = soil.soil_type.value if soil else "loamy"

        for field in farm.fields:
            for crop in field.crops:
                if crop.status.value != "active":
                    continue

                water_req = 5.0
                if crop.catalog:
                    water_req = crop.catalog.water_requirement_mm_per_day

                rec = irrigation_engine.calculate(
                    crop_name=crop.crop_name,
                    crop_stage=crop.current_stage.value if crop.current_stage else "vegetative",
                    area_acres=crop.area_acres,
                    soil_type=soil_type,
                    irrigation_method=farm.irrigation_method.value if farm.irrigation_method else "flood",
                    water_requirement_mm_per_day=water_req,
                    forecast_days=forecast_days,
                    current_weather=current_weather,
                )

                if rec.get("irrigation_required"):
                    dedup_key = f"irr_{farm.id}_{crop.id}_{date.today().isoformat()}"

                    # Record notification (prevents duplicates)
                    notif = telegram_service.create_notification_record(
                        db=db, user_id=user.id, farm_id=farm.id,
                        notif_type=NotificationType.irrigation,
                        title=f"Irrigation reminder: {crop.crop_name}",
                        message=rec.get("reason", ""),
                        channel=NotificationChannel.telegram,
                        dedup_key=dedup_key,
                    )

                    if notif and user.telegram_chat_id:
                        sent = await telegram_service.send_irrigation_reminder(
                            chat_id=user.telegram_chat_id,
                            farm_name=farm.name,
                            crop_name=crop.crop_name,
                            amount_mm=rec.get("estimated_requirement_mm", 0) or 0,
                            recommended_time=rec.get("recommended_time", "06:00"),
                            reason=rec.get("reason", ""),
                        )
                        if sent:
                            notif.sent = True
                            notif.sent_at = datetime.utcnow()
                            db.commit()

    async def _run_weather_alerts(self):
        """Check for weather risks and send alerts."""
        logger.info("Scheduler: Running weather alert check")
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                User.telegram_connected == True,
                User.notify_weather == True,
            ).all()

            for user in users:
                for farm in user.farms:
                    try:
                        await self._process_weather_alerts_for_farm(db, user, farm)
                    except Exception as e:
                        logger.error(f"Weather alert failed for farm {farm.id}: {e}")
        finally:
            db.close()

    async def _process_weather_alerts_for_farm(self, db: Session, user: User, farm: "Farm"):
        if not self._weather_service:
            return

        try:
            current_weather = await self._weather_service.get_current_weather(farm.location)
            forecast = await self._weather_service.get_forecast(farm.location, 3)
            forecast_days = forecast.get("days", [])
        except Exception:
            return

        active_crops = [
            {"crop_name": c.crop_name, "current_stage": c.current_stage.value if c.current_stage else "vegetative", "area_acres": c.area_acres}
            for field in farm.fields
            for c in field.crops
            if c.status.value == "active"
        ]

        risk_result = risk_engine.analyse(
            farm_id=farm.id, location=farm.location,
            current_weather=current_weather, forecast_days=forecast_days,
            active_crops=active_crops
        )

        for risk in risk_result.get("risks", []):
            if risk["level"] in ["high", "critical"]:
                dedup_key = f"risk_{farm.id}_{risk['risk_type']}_{date.today().isoformat()}"

                notif = telegram_service.create_notification_record(
                    db=db, user_id=user.id, farm_id=farm.id,
                    notif_type=NotificationType.weather_alert,
                    title=risk["title"],
                    message=risk["description"],
                    channel=NotificationChannel.telegram,
                    dedup_key=dedup_key,
                )

                if notif and user.telegram_chat_id:
                    sent = await telegram_service.send_weather_alert(
                        chat_id=user.telegram_chat_id,
                        farm_name=farm.name,
                        alert_title=risk["title"],
                        description=risk["description"],
                        action=risk["recommended_action"],
                    )
                    if sent:
                        notif.sent = True
                        notif.sent_at = datetime.utcnow()
                        db.commit()

    async def _run_crop_reminders(self):
        """Send crop stage reminders."""
        logger.info("Scheduler: Running crop reminders")
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                User.telegram_connected == True,
                User.notify_crops == True,
            ).all()

            for user in users:
                for farm in user.farms:
                    for field in farm.fields:
                        for crop in field.crops:
                            if crop.status.value != "active":
                                continue
                            try:
                                stage = crop.current_stage.value if crop.current_stage else "vegetative"
                                dedup_key = f"crop_{farm.id}_{crop.id}_{date.today().isoformat()}"

                                from backend.agriculture.crop_calendar import STAGE_TASKS
                                action = STAGE_TASKS.get(stage, ["Inspect the crop"])[0]

                                notif = telegram_service.create_notification_record(
                                    db=db, user_id=user.id, farm_id=farm.id,
                                    notif_type=NotificationType.crop_reminder,
                                    title=f"{crop.crop_name} — {stage.replace('_', ' ').title()} stage",
                                    message=action,
                                    channel=NotificationChannel.telegram,
                                    dedup_key=dedup_key,
                                )

                                if notif and user.telegram_chat_id:
                                    sent = await telegram_service.send_crop_reminder(
                                        chat_id=user.telegram_chat_id,
                                        farm_name=farm.name,
                                        crop_name=crop.crop_name,
                                        stage=stage,
                                        action=action,
                                    )
                                    if sent:
                                        notif.sent = True
                                        notif.sent_at = datetime.utcnow()
                                        db.commit()
                            except Exception as e:
                                logger.error(f"Crop reminder failed: {e}")
        finally:
            db.close()

    async def _run_daily_summary(self):
        """Send daily farm summary."""
        logger.info("Scheduler: Running daily summary")
        db = SessionLocal()
        try:
            users = db.query(User).filter(
                User.telegram_connected == True,
                User.notify_daily_summary == True,
            ).all()

            for user in users:
                for farm in user.farms:
                    try:
                        active_crops = sum(
                            1 for f in farm.fields for c in f.crops if c.status.value == "active"
                        )
                        pending_tasks = sum(
                            1 for t in farm.farm_tasks if t.status.value == "pending"
                        )

                        summary = (
                            f"🌱 Active crops: {active_crops}\n"
                            f"📋 Pending tasks: {pending_tasks}\n\n"
                            f"Check your SmartFarm dashboard for detailed recommendations."
                        )

                        dedup_key = f"summary_{farm.id}_{date.today().isoformat()}"
                        notif = telegram_service.create_notification_record(
                            db=db, user_id=user.id, farm_id=farm.id,
                            notif_type=NotificationType.daily_summary,
                            title="Daily Farm Summary",
                            message=summary,
                            channel=NotificationChannel.telegram,
                            dedup_key=dedup_key,
                        )

                        if notif and user.telegram_chat_id:
                            sent = await telegram_service.send_daily_summary(
                                chat_id=user.telegram_chat_id,
                                farm_name=farm.name,
                                summary=summary,
                            )
                            if sent:
                                notif.sent = True
                                notif.sent_at = datetime.utcnow()
                                db.commit()
                    except Exception as e:
                        logger.error(f"Daily summary failed for farm {farm.id}: {e}")
        finally:
            db.close()


# Module-level singleton
farm_scheduler = FarmScheduler()
