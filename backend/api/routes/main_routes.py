"""
SmartFarm - Weather, Irrigation, Risk, Action Plan, AI and Market Routes
"""
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Farm, Crop, IrrigationRecord, FarmTask
from backend.models.models import TaskStatus, TaskType
from backend.services.weather_service import weather_service, WeatherServiceError
from backend.services.market_service import market_service
from backend.agriculture.irrigation_engine import irrigation_engine
from backend.agriculture.risk_engine import risk_engine
from backend.agriculture.action_plan import action_plan_engine
from backend.agents.ask_shyam import ask_shyam_agent, AskShyamError
from backend.notifications.telegram_service import telegram_service
from backend.schemas.schemas import AskShyamRequest

logger = logging.getLogger(__name__)

weather_router = APIRouter(prefix="/weather", tags=["Weather"])
irrigation_router = APIRouter(prefix="/irrigation", tags=["Irrigation"])
risk_router = APIRouter(prefix="/risks", tags=["Risks"])
plan_router = APIRouter(prefix="/plan", tags=["Action Plan"])
ai_router = APIRouter(prefix="/ai", tags=["Ask Shyam"])
market_router = APIRouter(prefix="/market", tags=["Market"])
telegram_router = APIRouter(prefix="/telegram", tags=["Telegram"])
tasks_router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ─────────────────────────────────────────────
# WEATHER ROUTES (Phase 3)
# ─────────────────────────────────────────────

@weather_router.get("/current/farm/{farm_id}")
async def get_farm_weather(farm_id: int, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    try:
        return await weather_service.get_current_weather(farm.location)
    except WeatherServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))


@weather_router.get("/current")
async def get_weather_by_location(location: str = Query(..., description="City name, e.g. 'Nagpur,IN'")):
    try:
        return await weather_service.get_current_weather(location)
    except WeatherServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))


@weather_router.get("/forecast/farm/{farm_id}")
async def get_farm_forecast(farm_id: int, days: int = 5, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    try:
        return await weather_service.get_forecast(farm.location, min(days, 5))
    except WeatherServiceError as e:
        raise HTTPException(status_code=503, detail=str(e))


# ─────────────────────────────────────────────
# IRRIGATION ROUTES (Phase 4)
# ─────────────────────────────────────────────

@irrigation_router.get("/recommend/farm/{farm_id}")
async def get_irrigation_recommendation(farm_id: int, crop_id: Optional[int] = None, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    soil = farm.soil_profile
    soil_type = soil.soil_type.value if soil else "loamy"

    # Find target crop
    crop = None
    if crop_id:
        crop = db.query(Crop).filter(Crop.id == crop_id).first()
    else:
        for field in farm.fields:
            for c in field.crops:
                if c.status.value == "active":
                    crop = c
                    break
            if crop:
                break

    if not crop:
        raise HTTPException(status_code=404, detail="No active crop found on farm")

    water_req = 5.0
    if crop.catalog:
        water_req = crop.catalog.water_requirement_mm_per_day

    # Get weather
    current_weather = {}
    forecast_days = []
    try:
        current_weather = await weather_service.get_current_weather(farm.location)
        forecast = await weather_service.get_forecast(farm.location, 3)
        forecast_days = forecast.get("days", [])
    except WeatherServiceError:
        logger.warning(f"Weather unavailable for farm {farm_id} — irrigation calculated without weather")

    # Last irrigation
    last_irr = (
        db.query(IrrigationRecord)
        .filter(IrrigationRecord.farm_id == farm_id, IrrigationRecord.completed == True)
        .order_by(IrrigationRecord.actual_date.desc())
        .first()
    )

    return irrigation_engine.calculate(
        crop_name=crop.crop_name,
        crop_stage=crop.current_stage.value if crop.current_stage else "vegetative",
        area_acres=crop.area_acres,
        soil_type=soil_type,
        irrigation_method=farm.irrigation_method.value if farm.irrigation_method else "flood",
        water_requirement_mm_per_day=water_req,
        forecast_days=forecast_days,
        current_weather=current_weather,
        last_irrigation_date=last_irr.actual_date if last_irr else None,
    )


@irrigation_router.post("/records")
def log_irrigation(
    farm_id: int, crop_id: Optional[int] = None,
    amount_mm: float = 0, method: str = "flood",
    db: Session = Depends(get_db)
):
    from datetime import date
    rec = IrrigationRecord(
        farm_id=farm_id,
        crop_id=crop_id,
        scheduled_date=date.today(),
        actual_date=date.today(),
        actual_amount_mm=amount_mm,
        method=method,
        completed=True,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return {"id": rec.id, "message": "Irrigation logged successfully"}


@irrigation_router.get("/history/farm/{farm_id}")
def get_irrigation_history(farm_id: int, limit: int = 10, db: Session = Depends(get_db)):
    records = (
        db.query(IrrigationRecord)
        .filter(IrrigationRecord.farm_id == farm_id)
        .order_by(IrrigationRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "scheduled_date": r.scheduled_date.isoformat(),
            "actual_date": r.actual_date.isoformat() if r.actual_date else None,
            "amount_mm": r.actual_amount_mm,
            "completed": r.completed,
            "skipped": r.skipped,
        }
        for r in records
    ]

@irrigation_router.delete("/records/{record_id}")
def delete_irrigation_record(record_id: int, db: Session = Depends(get_db)):
    rec = db.query(IrrigationRecord).filter(IrrigationRecord.id == record_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(rec)
    db.commit()
    return {"message": "Record deleted"}


# ─────────────────────────────────────────────
# RISK ROUTES (Phase 7)
# ─────────────────────────────────────────────

@risk_router.get("/farm/{farm_id}")
async def get_farm_risks(farm_id: int, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    current_weather = {}
    forecast_days = []
    try:
        current_weather = await weather_service.get_current_weather(farm.location)
        forecast = await weather_service.get_forecast(farm.location, 5)
        forecast_days = forecast.get("days", [])
    except WeatherServiceError as e:
        logger.warning(f"Weather unavailable: {e}")

    active_crops = [
        {"crop_name": c.crop_name, "current_stage": c.current_stage.value if c.current_stage else "vegetative", "area_acres": c.area_acres}
        for field in farm.fields for c in field.crops if c.status.value == "active"
    ]

    return risk_engine.analyse(
        farm_id=farm_id,
        location=farm.location,
        current_weather=current_weather,
        forecast_days=forecast_days,
        active_crops=active_crops,
    )


# ─────────────────────────────────────────────
# ACTION PLAN (Phase 8)
# ─────────────────────────────────────────────

@plan_router.get("/farm/{farm_id}")
async def get_action_plan(farm_id: int, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    active_crops = [
        {"crop_name": c.crop_name, "current_stage": c.current_stage.value if c.current_stage else "vegetative", "area_acres": c.area_acres}
        for field in farm.fields for c in field.crops if c.status.value == "active"
    ]

    current_weather = {}
    forecast_days = []
    try:
        current_weather = await weather_service.get_current_weather(farm.location)
        forecast = await weather_service.get_forecast(farm.location, 7)
        forecast_days = forecast.get("days", [])
    except WeatherServiceError:
        pass

    # Irrigation recommendation for first active crop
    irr_rec = {"irrigation_required": False, "reason": "Weather data unavailable", "skip_reason": "Weather data unavailable"}
    try:
        irr_rec = await get_irrigation_recommendation(farm_id, None, db)
    except Exception:
        pass

    risk_result = risk_engine.analyse(
        farm_id=farm_id, location=farm.location,
        current_weather=current_weather, forecast_days=forecast_days,
        active_crops=active_crops
    )

    pending_tasks = (
        db.query(FarmTask)
        .filter(FarmTask.farm_id == farm_id, FarmTask.status == "pending")
        .limit(20)
        .all()
    )
    tasks_data = [
        {"title": t.title, "description": t.description, "due_date": t.due_date.isoformat() if t.due_date else None, "priority": t.priority}
        for t in pending_tasks
    ]

    return action_plan_engine.generate(
        farm_id=farm_id,
        farm_name=farm.name,
        active_crops=active_crops,
        irrigation_recommendation=irr_rec,
        weather_forecast=forecast_days,
        current_weather=current_weather,
        risk_analysis=risk_result,
        pending_tasks=tasks_data,
    )


# ─────────────────────────────────────────────
# FARMAI (Phase 10)
# ─────────────────────────────────────────────

@ai_router.post("/chat")
async def chat_with_farmai(payload: AskShyamRequest, db: Session = Depends(get_db)):
    try:
        user_message = payload.message or ""
        
        # 1. Process Voice Input if provided
        if payload.voice_base64:
            import tempfile
            import base64
            from groq import Groq
            from backend.config import settings
            import os
            
            # Decode audio
            audio_data = base64.b64decode(payload.voice_base64)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tf:
                tf.write(audio_data)
                temp_path = tf.name
            
            try:
                client = Groq(api_key=settings.groq_api_key)
                with open(temp_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(os.path.basename(temp_path), file.read()),
                        model="whisper-large-v3-turbo",
                        response_format="text",
                    )
                user_message = str(transcription).strip() + " " + user_message
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        
        # 2. Get AI Response
        result = await ask_shyam_agent.chat(
            user_message=user_message.strip() or "Hello",
            farm_id=payload.farm_id,
            user_id=payload.user_id,
            db=db,
            conversation_history=payload.conversation_history,
            weather_service=weather_service,
            market_service=market_service,
            image_base64=payload.image_base64,
            language=payload.language,
        )
        
        # 3. Generate Audio Output if requested
        if payload.generate_audio:
            import edge_tts
            import base64
            import tempfile
            import os
            try:
                # Use a masculine Hindi voice (MadhurNeural)
                voice = "en-IN-PrabhatNeural" if payload.language == "en" else "hi-IN-MadhurNeural"
                communicate = edge_tts.Communicate(result["reply"], voice)
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tf:
                    temp_path = tf.name
                
                await communicate.save(temp_path)
                
                with open(temp_path, "rb") as f:
                    audio_b64 = base64.b64encode(f.read()).decode("utf-8")
                result["audio_base64"] = audio_b64
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                logger.error(f"TTS error: {e}")
                
        return result
    except AskShyamError as e:
        raise HTTPException(status_code=503, detail=f"Ask Shyam is temporarily unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Ask Shyam error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="Ask Shyam is temporarily unavailable. Please try again.")


# ─────────────────────────────────────────────
# MARKET ROUTES (Phase 16)
# ─────────────────────────────────────────────

@market_router.get("/prices")
async def get_mandi_prices(crop: str = Query(...), location: str = Query(...)):
    return await market_service.get_prices(crop, location)


@market_router.get("/prices/farm/{farm_id}")
async def get_farm_crop_prices(farm_id: int, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    crop_names = list(set(
        c.crop_name.lower()
        for field in farm.fields
        for c in field.crops
        if c.status.value == "active"
    ))

    if not crop_names:
        return {"location": farm.location, "prices": [], "fetched_at": "N/A"}

    return await market_service.get_multiple_prices(crop_names, farm.location)


# ─────────────────────────────────────────────
# TELEGRAM ROUTES (Phase 13)
# ─────────────────────────────────────────────

@telegram_router.post("/link-code")
async def link_telegram(user_id: int, db: Session = Depends(get_db)):
    try:
        return await telegram_service.link_account(db, user_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@telegram_router.get("/status")
def telegram_status(user_id: int, db: Session = Depends(get_db)):
    from backend.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"connected": user.telegram_connected}


@telegram_router.post("/webhook")
async def telegram_webhook(update: dict, db: Session = Depends(get_db)):
    """Receive Telegram webhook updates."""
    try:
        await telegram_service.handle_webhook(
            db=db, update=update,
            ask_shyam_agent=ask_shyam_agent,
            weather_service=weather_service,
        )
        return {"ok": True}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"ok": False}


# ─────────────────────────────────────────────
# TASKS ROUTES
# ─────────────────────────────────────────────

@tasks_router.get("/farm/{farm_id}")
def get_farm_tasks(farm_id: int, status: Optional[str] = None, db: Session = Depends(get_db)):
    q = db.query(FarmTask).filter(FarmTask.farm_id == farm_id)
    if status:
        q = q.filter(FarmTask.status == status)
    tasks = q.order_by(FarmTask.due_date.asc()).limit(50).all()
    return [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "task_type": t.task_type.value,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "status": t.status.value,
            "priority": t.priority,
            "auto_generated": t.auto_generated,
        }
        for t in tasks
    ]


@tasks_router.put("/{task_id}/complete")
def complete_task(task_id: int, db: Session = Depends(get_db)):
    from datetime import datetime
    task = db.query(FarmTask).filter(FarmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = TaskStatus.completed
    task.completed_at = datetime.utcnow()
    db.commit()
    return {"message": "Task marked as completed"}


@tasks_router.put("/{task_id}/skip")
def skip_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(FarmTask).filter(FarmTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = TaskStatus.skipped
    db.commit()
    return {"message": "Task skipped"}
