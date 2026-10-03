"""
SmartFarm - Pydantic Schemas
Request/response validation for all API endpoints.
"""
from datetime import datetime, date
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, Field, field_validator


# ─────────────────────────────────────────────
# USER SCHEMAS
# ─────────────────────────────────────────────

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notify_irrigation: Optional[bool] = None
    notify_weather: Optional[bool] = None
    notify_crops: Optional[bool] = None
    notify_risks: Optional[bool] = None
    notify_daily_summary: Optional[bool] = None
    preferred_notify_time: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: Optional[str]
    phone: Optional[str]
    telegram_connected: bool
    telegram_chat_id: Optional[str]
    notify_irrigation: bool
    notify_weather: bool
    notify_crops: bool
    notify_risks: bool
    notify_daily_summary: bool
    preferred_notify_time: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# FARM SCHEMAS
# ─────────────────────────────────────────────

class FarmCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    location: str = Field(..., min_length=1, max_length=200)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    total_area_acres: float = Field(..., gt=0, le=100000)
    state: Optional[str] = None
    country: str = "India"
    irrigation_method: str = "flood"
    water_source: str = "borewell"


class FarmUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    total_area_acres: Optional[float] = None
    state: Optional[str] = None
    irrigation_method: Optional[str] = None
    water_source: Optional[str] = None


class FarmResponse(BaseModel):
    id: int
    user_id: int
    name: str
    location: str
    latitude: Optional[float]
    longitude: Optional[float]
    total_area_acres: float
    state: Optional[str]
    country: str
    irrigation_method: str
    water_source: str
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# SOIL PROFILE SCHEMAS
# ─────────────────────────────────────────────

class SoilProfileCreate(BaseModel):
    soil_type: str = "loamy"
    ph_level: Optional[float] = Field(None, ge=0, le=14)
    organic_matter_percent: Optional[float] = Field(None, ge=0, le=100)
    nitrogen_kg_per_ha: Optional[float] = Field(None, ge=0)
    phosphorus_kg_per_ha: Optional[float] = Field(None, ge=0)
    potassium_kg_per_ha: Optional[float] = Field(None, ge=0)
    water_holding_capacity: Optional[str] = None
    notes: Optional[str] = None


class SoilProfileResponse(BaseModel):
    id: int
    farm_id: int
    soil_type: str
    ph_level: Optional[float]
    organic_matter_percent: Optional[float]
    nitrogen_kg_per_ha: Optional[float]
    phosphorus_kg_per_ha: Optional[float]
    potassium_kg_per_ha: Optional[float]
    water_holding_capacity: Optional[str]
    notes: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# FIELD SCHEMAS
# ─────────────────────────────────────────────

class FieldCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    area_acres: float = Field(..., gt=0)
    notes: Optional[str] = None


class FieldResponse(BaseModel):
    id: int
    farm_id: int
    name: str
    area_acres: float
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# CROP CATALOG SCHEMAS
# ─────────────────────────────────────────────

class CropCatalogResponse(BaseModel):
    id: int
    crop_name: str
    local_name: Optional[str]
    season: str
    temperature_min_c: float
    temperature_max_c: float
    rainfall_requirement_mm: float
    water_requirement_mm_per_day: float
    growth_duration_days: int
    soil_preferences: Optional[str]
    sowing_window_start: Optional[str]
    sowing_window_end: Optional[str]
    description: Optional[str]

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# CROP SCHEMAS
# ─────────────────────────────────────────────

class CropCreate(BaseModel):
    field_id: int
    crop_name: str = Field(..., min_length=1, max_length=100)
    variety: Optional[str] = None
    area_acres: float = Field(..., gt=0)
    sowing_date: Optional[date] = None
    notes: Optional[str] = None


class CropUpdate(BaseModel):
    variety: Optional[str] = None
    area_acres: Optional[float] = None
    sowing_date: Optional[date] = None
    expected_harvest_date: Optional[date] = None
    status: Optional[str] = None
    current_stage: Optional[str] = None
    notes: Optional[str] = None


class CropResponse(BaseModel):
    id: int
    field_id: int
    crop_name: str
    variety: Optional[str]
    area_acres: float
    sowing_date: Optional[date]
    expected_harvest_date: Optional[date]
    status: str
    current_stage: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# IRRIGATION SCHEMAS
# ─────────────────────────────────────────────

class IrrigationRecommendation(BaseModel):
    irrigation_required: bool
    recommended_date: Optional[str]
    recommended_time: str = "06:00"
    estimated_requirement_mm: Optional[float]
    duration_hours: Optional[float]
    reason: str
    confidence: str  # low / medium / high
    skip_reason: Optional[str] = None
    weather_factor: Optional[str] = None


class IrrigationRecordCreate(BaseModel):
    farm_id: int
    crop_id: Optional[int] = None
    scheduled_date: date
    recommended_amount_mm: Optional[float] = None
    method: Optional[str] = None
    notes: Optional[str] = None


class IrrigationRecordResponse(BaseModel):
    id: int
    farm_id: int
    crop_id: Optional[int]
    scheduled_date: date
    actual_date: Optional[date]
    recommended_amount_mm: Optional[float]
    actual_amount_mm: Optional[float]
    completed: bool
    skipped: bool
    skip_reason: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# FARM TASK SCHEMAS
# ─────────────────────────────────────────────

class FarmTaskCreate(BaseModel):
    farm_id: int
    crop_id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=300)
    description: Optional[str] = None
    task_type: str = "general"
    due_date: Optional[date] = None
    priority: int = Field(2, ge=1, le=3)


class FarmTaskUpdate(BaseModel):
    status: Optional[str] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class FarmTaskResponse(BaseModel):
    id: int
    farm_id: int
    crop_id: Optional[int]
    title: str
    description: Optional[str]
    task_type: str
    due_date: Optional[date]
    status: str
    priority: int
    auto_generated: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# WEATHER SCHEMAS
# ─────────────────────────────────────────────

class CurrentWeatherResponse(BaseModel):
    location: str
    temperature_c: float
    feels_like_c: float
    humidity_percent: float
    rainfall_mm: float
    wind_speed_kmh: float
    wind_direction: str
    cloud_cover_percent: int
    description: str
    icon: str
    sunrise: str
    sunset: str
    rain_probability: float
    recorded_at: str


class ForecastDay(BaseModel):
    date: str
    day_of_week: str
    temp_max_c: float
    temp_min_c: float
    humidity_percent: float
    rainfall_mm: float
    rain_probability: float
    description: str
    icon: str


class ForecastResponse(BaseModel):
    location: str
    days: List[ForecastDay]


# ─────────────────────────────────────────────
# CROP RECOMMENDATION SCHEMAS
# ─────────────────────────────────────────────

class CropRecommendation(BaseModel):
    crop_name: str
    local_name: Optional[str]
    season: str
    suitability: str  # highly_suitable / suitable / moderate / not_suitable
    suitability_score: float  # 0–100
    reasons: List[str]
    soil_match: bool
    temp_match: bool
    rainfall_match: bool
    sowing_window: Optional[str]
    growth_duration_days: int


class CropRecommendationResponse(BaseModel):
    location: str
    season: str
    current_month: int
    recommendations: List[CropRecommendation]
    generated_at: str


# ─────────────────────────────────────────────
# RISK SCHEMAS
# ─────────────────────────────────────────────

class RiskAlert(BaseModel):
    risk_type: str
    title: str
    description: str
    level: str  # low / medium / high / critical
    recommended_action: str
    affected_crops: List[str]


class RiskAnalysisResponse(BaseModel):
    farm_id: int
    location: str
    risks: List[RiskAlert]
    overall_risk_level: str
    generated_at: str


# ─────────────────────────────────────────────
# ACTION PLAN SCHEMAS
# ─────────────────────────────────────────────

class DayAction(BaseModel):
    icon: str
    title: str
    description: str
    priority: int  # 1=high, 2=medium, 3=low
    category: str  # irrigation / weather / crop / risk / general


class DayPlan(BaseModel):
    date: str
    day_label: str  # "TODAY", "TOMORROW", "Day 3", etc.
    weather_summary: str
    actions: List[DayAction]
    irrigation_needed: bool


class ActionPlanResponse(BaseModel):
    farm_id: int
    farm_name: str
    days: List[DayPlan]
    generated_at: str


# ─────────────────────────────────────────────
# FARM AI SCHEMAS
# ─────────────────────────────────────────────

class AskShyamRequest(BaseModel):
    user_id: int
    farm_id: int
    message: str = Field(..., min_length=1, max_length=2000)
    image_base64: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = []


class AskShyamResponse(BaseModel):
    reply: str
    tools_used: List[str]
    sources: List[str]


# ─────────────────────────────────────────────
# NOTIFICATION SCHEMAS
# ─────────────────────────────────────────────

class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    channel: str
    title: str
    message: str
    sent: bool
    sent_at: Optional[datetime]
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ─────────────────────────────────────────────
# MARKET/MANDI SCHEMAS
# ─────────────────────────────────────────────

class MandiPrice(BaseModel):
    crop_name: str
    market_name: str
    price_per_quintal: Optional[float]
    unit: str = "quintal"
    date: Optional[str]
    source: str
    available: bool
    note: Optional[str] = None


class MandiPricesResponse(BaseModel):
    location: str
    prices: List[MandiPrice]
    fetched_at: str


# ─────────────────────────────────────────────
# TELEGRAM SCHEMAS
# ─────────────────────────────────────────────

class TelegramLinkRequest(BaseModel):
    user_id: int


class TelegramLinkResponse(BaseModel):
    link_code: str
    bot_username: str
    instructions: str


class TelegramWebhookUpdate(BaseModel):
    update_id: int
    message: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────
# ANALYTICS SCHEMAS
# ─────────────────────────────────────────────

class FarmAnalytics(BaseModel):
    farm_id: int
    farm_name: str
    total_area_acres: float
    active_crops: int
    crop_details: List[Dict[str, Any]]
    irrigation_events_last_30_days: int
    estimated_water_used_mm: float
    total_rainfall_mm: float
    pending_tasks: int
    overdue_tasks: int
    active_risks: int
    generated_at: str


# ─────────────────────────────────────────────
# GENERAL / HEALTH
# ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    weather_api: str
    groq_api: str
    telegram: str
