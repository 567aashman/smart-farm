"""
SmartFarm - Telegram Service (Phases 13, 14, 15)
Telegram bot integration for reminders and FarmAI assistant.
"""
import logging
import secrets
from datetime import datetime
from typing import Optional
import httpx

from sqlalchemy.orm import Session
from backend.config import settings
from backend.models import User, Notification, NotificationType, NotificationChannel

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


class TelegramService:
    """
    Telegram notification and bot service.
    Uses direct HTTP calls — no heavy library needed for basic sending.
    """

    def is_configured(self) -> bool:
        return bool(settings.telegram_bot_token)

    async def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """Send a Telegram message. Returns True on success."""
        if not self.is_configured():
            logger.warning("Telegram bot token not configured")
            return False

        url = f"{TELEGRAM_API}/sendMessage"
        payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    logger.info(f"Telegram message sent to {chat_id}")
                    return True
                else:
                    logger.error(f"Telegram API error {resp.status_code}: {resp.text}")
                    return False
            except Exception as e:
                logger.error(f"Telegram send failed: {e}")
                return False

    def generate_link_code(self) -> str:
        """Generate a unique 8-character linking code."""
        return secrets.token_urlsafe(6).upper()[:8]

    async def link_account(self, db: Session, user_id: int) -> dict:
        """Generate a Telegram linking code for a user."""
        from datetime import datetime, timedelta
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")

        code = self.generate_link_code()
        expires_in = 15
        user.telegram_link_code = code
        user.telegram_link_expires = datetime.utcnow() + timedelta(minutes=expires_in)
        db.commit()

        logger.info(f"Generated link code {code} for user {user_id}, expires at {user.telegram_link_expires}")

        bot_username = await self._get_bot_username()
        deep_link = f"https://t.me/{bot_username}?start={code}"

        return {
            "code": code,
            "deep_link": deep_link,
            "bot_username": bot_username,
            "expires_in_minutes": expires_in,
            "instructions": (
                f"1. Open Telegram\n"
                f"2. Search for @{bot_username}\n"
                f"3. Send: /start {code}\n"
                f"4. Your account will be connected!"
            )
        }

    async def _get_bot_username(self) -> str:
        if not self.is_configured():
            return "annadata_bot"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{TELEGRAM_API}/getMe")
                if resp.status_code == 200:
                    return resp.json()["result"]["username"]
        except Exception:
            pass
        return "annadata_bot"

    async def handle_webhook(self, db: Session, update: dict, farm_ai_agent=None, weather_service=None) -> bool:
        """
        Handle incoming Telegram webhook update.
        Supports: /start, /link <code>, FarmAI questions.
        """
        message = update.get("message", {})
        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "").strip()

        if not chat_id or not text:
            return False

        # ── /start [code] ──
        if text.startswith("/start"):
            parts = text.split()
            if len(parts) > 1:
                code = parts[1].strip()
                from datetime import datetime
                user = db.query(User).filter(User.telegram_link_code == code).first()
                if user and user.telegram_link_expires and user.telegram_link_expires > datetime.utcnow():
                    user.telegram_chat_id = chat_id
                    user.telegram_connected = True
                    user.telegram_link_code = None
                    user.telegram_link_expires = None
                    db.commit()
                    logger.info(f"User {user.id} linked to chat_id {chat_id}")
                    await self.send_message(
                        chat_id,
                        f"✅ <b>Account linked successfully!</b>\n\n"
                        f"Hello {user.name}! 🌾\n\n"
                        f"You'll now receive:\n"
                        f"• Irrigation reminders\n"
                        f"• Weather alerts\n"
                        f"• Crop updates\n\n"
                        f"You can also ask me farming questions directly!"
                    )
                else:
                    await self.send_message(chat_id, "❌ Invalid or expired linking code. Please generate a new one from the dashboard.")
            else:
                await self.send_message(
                    chat_id,
                    "🌾 <b>Welcome to SmartFarm!</b>\n\n"
                    "I can help you with:\n"
                    "• Irrigation reminders\n"
                    "• Weather alerts\n"
                    "• Crop advice\n\n"
                    "To connect your farm account, use the SmartFarm dashboard to get your link."
                )
            return True

        # ── FarmAI assistant ──
        if farm_ai_agent:
            user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
            if user:
                await self.send_message(chat_id, "🌱 Let me check your farm data...")
                try:
                    # Get user's first farm
                    farm = user.farms[0] if user.farms else None
                    if not farm:
                        await self.send_message(chat_id, "❌ No farm found. Please set up your farm on the dashboard first.")
                        return True

                    result = await farm_ai_agent.chat(
                        user_message=text,
                        farm_id=farm.id,
                        user_id=user.id,
                        db=db,
                        weather_service=weather_service,
                    )
                    reply = result["reply"]
                    # Telegram max message length
                    if len(reply) > 4000:
                        reply = reply[:4000] + "..."
                    await self.send_message(chat_id, f"🤖 <b>FarmAI:</b>\n\n{reply}")
                except Exception as e:
                    logger.error(f"FarmAI Telegram error: {e}")
                    await self.send_message(chat_id, "⚠️ FarmAI is temporarily unavailable. Please try again later.")
            else:
                await self.send_message(
                    chat_id,
                    "⚠️ Your account is not linked yet.\n"
                    "Use <code>/link YOUR-CODE</code> to connect your SmartFarm account."
                )
        return True

    async def send_irrigation_reminder(
        self, chat_id: str, farm_name: str, crop_name: str,
        amount_mm: float, recommended_time: str, reason: str
    ) -> bool:
        text = (
            f"🌾 <b>SMARTFARM IRRIGATION REMINDER</b>\n\n"
            f"<b>Farm:</b> {farm_name}\n"
            f"<b>Crop:</b> {crop_name}\n\n"
            f"💧 Your {crop_name} may require irrigation.\n\n"
            f"<b>Recommended time:</b> {recommended_time}\n"
            f"<b>Estimated amount:</b> {amount_mm:.0f} mm\n\n"
            f"<b>Reason:</b> {reason}"
        )
        return await self.send_message(chat_id, text)

    async def send_weather_alert(
        self, chat_id: str, farm_name: str, alert_title: str, description: str, action: str
    ) -> bool:
        text = (
            f"🌧️ <b>WEATHER ALERT — {farm_name}</b>\n\n"
            f"<b>{alert_title}</b>\n\n"
            f"{description}\n\n"
            f"<b>Recommended action:</b>\n{action}"
        )
        return await self.send_message(chat_id, text)

    async def send_crop_reminder(
        self, chat_id: str, farm_name: str, crop_name: str, stage: str, action: str
    ) -> bool:
        text = (
            f"🌱 <b>CROP REMINDER — {farm_name}</b>\n\n"
            f"Your <b>{crop_name}</b> is in the <b>{stage.replace('_', ' ').title()}</b> stage.\n\n"
            f"<b>Today's recommended action:</b>\n{action}"
        )
        return await self.send_message(chat_id, text)

    async def send_daily_summary(
        self, chat_id: str, farm_name: str, summary: str
    ) -> bool:
        text = f"📊 <b>DAILY FARM SUMMARY — {farm_name}</b>\n\n{summary}"
        return await self.send_message(chat_id, text)

    def create_notification_record(
        self, db: Session, user_id: int, farm_id: Optional[int],
        notif_type: NotificationType, title: str, message: str,
        channel: NotificationChannel = NotificationChannel.dashboard,
        dedup_key: Optional[str] = None
    ) -> Optional[Notification]:
        """Create a notification record, preventing duplicates by dedup_key."""
        if dedup_key:
            existing = db.query(Notification).filter(
                Notification.dedup_key == dedup_key
            ).first()
            if existing:
                logger.debug(f"Skipping duplicate notification: {dedup_key}")
                return None

        notif = Notification(
            user_id=user_id,
            farm_id=farm_id,
            notification_type=notif_type,
            channel=channel,
            title=title,
            message=message,
            dedup_key=dedup_key,
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif


# Module-level singleton
telegram_service = TelegramService()
