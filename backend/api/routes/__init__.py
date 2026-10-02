"""API routes package."""
from .users import router as users_router
from .farms import router as farms_router
from .crops import router as crops_router
from .main_routes import (
    weather_router, irrigation_router, risk_router,
    plan_router, ai_router, market_router, telegram_router, tasks_router
)

__all__ = [
    "users_router", "farms_router", "crops_router",
    "weather_router", "irrigation_router", "risk_router",
    "plan_router", "ai_router", "market_router", "telegram_router", "tasks_router"
]
