"""
SmartFarm - Main FastAPI Application
Phase 0: Project Foundation

Startup:
  uvicorn backend.main:app --reload --port 8000
"""
import json
import logging
import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# ── Ensure project root is on the path ──
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from backend.config import settings
from backend.database import init_db, engine
from backend.api.routes import (
    users_router, farms_router, crops_router,
    weather_router, irrigation_router, risk_router,
    plan_router, ai_router, market_router, telegram_router, tasks_router
)

# ── Logging Setup ──
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("smartfarm.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"


# ── Database Seeder ──
def seed_crop_catalog():
    """Seed the crop catalog from data/crops/crops.json if empty."""
    from backend.database import SessionLocal
    from backend.models import CropCatalog
    from backend.models.models import Season
    import json as _json

    db = SessionLocal()
    try:
        count = db.query(CropCatalog).count()
        if count > 0:
            logger.info(f"Crop catalog already has {count} entries — skipping seed.")
            return

        data_path = os.path.join(os.path.dirname(__file__), "..", "data", "crops", "crops.json")
        with open(data_path, "r") as f:
            crops = _json.load(f)

        for c in crops:
            catalog = CropCatalog(
                crop_name=c["crop_name"],
                local_name=c.get("local_name"),
                season=Season(c["season"]),
                temperature_min_c=c["temperature_min_c"],
                temperature_max_c=c["temperature_max_c"],
                rainfall_requirement_mm=c["rainfall_requirement_mm"],
                water_requirement_mm_per_day=c["water_requirement_mm_per_day"],
                growth_duration_days=c["growth_duration_days"],
                soil_preferences=_json.dumps(c.get("soil_preferences", [])),
                sowing_window_start=c.get("sowing_window_start"),
                sowing_window_end=c.get("sowing_window_end"),
                growth_stages=_json.dumps(c.get("growth_stages", [])),
                description=c.get("description"),
                market_name=c.get("market_name"),
            )
            db.add(catalog)

        db.commit()
        logger.info(f"Seeded {len(crops)} crops into catalog.")
    except FileNotFoundError:
        logger.warning("Crop catalog file not found — skipping seed.")
    except Exception as e:
        logger.error(f"Failed to seed crop catalog: {e}")
        db.rollback()
    finally:
        db.close()


# ── Startup / Shutdown ──
@asynccontextmanager
async def lifespan(app: FastAPI):
    import threading
    from backend.notifications.run_bot import main as run_telegram_bot
    
    logger.info(f"🌾 SmartFarm v{APP_VERSION} starting...")

    # Start Telegram bot in background thread if token is present
    if settings.telegram_bot_token:
        bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
        bot_thread.start()
        logger.info("✅ Telegram bot background thread started.")

    # Initialize database tables
    try:
        init_db()
        logger.info("✅ Database initialized.")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")

    # Seed crop catalog
    seed_crop_catalog()

    # Start scheduler
    try:
        from backend.scheduler.scheduler import farm_scheduler
        from backend.services.weather_service import weather_service
        farm_scheduler.set_weather_service(weather_service)
        farm_scheduler.start()
        logger.info("✅ Scheduler started.")
    except Exception as e:
        logger.error(f"⚠️ Scheduler failed to start: {e}")

    logger.info(f"✅ SmartFarm is ready. Env: {settings.app_env}")
    yield

    # Shutdown
    try:
        from backend.scheduler.scheduler import farm_scheduler
        farm_scheduler.shutdown()
    except Exception:
        pass
    logger.info("SmartFarm shutdown complete.")


# ── App Instance ──
app = FastAPI(
    title="SmartFarm",
    description="Agricultural decision-support system for Indian farmers",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── CORS ──
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],  # permissive for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again."},
    )


# ── Health Endpoint (Phase 0) ──
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    Returns: {"status": "ok"}
    """
    from sqlalchemy import text
    db_status = "ok"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"

    weather_status = "configured" if settings.weather_api_key else "not_configured"
    groq_status = "configured" if settings.groq_api_key else "not_configured"
    telegram_status = "configured" if settings.telegram_bot_token else "not_configured"

    return {
        "status": "ok",
        "version": APP_VERSION,
        "database": db_status,
        "weather_api": weather_status,
        "groq_api": groq_status,
        "telegram": telegram_status,
    }


# ── Register All Routers ──
app.include_router(users_router, prefix="/api")
app.include_router(farms_router, prefix="/api")
app.include_router(crops_router, prefix="/api")
app.include_router(weather_router, prefix="/api")
app.include_router(irrigation_router, prefix="/api")
app.include_router(risk_router, prefix="/api")
app.include_router(plan_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(market_router, prefix="/api")
app.include_router(telegram_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")

# Serve frontend static files
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ── Entry point for direct run ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
    )
