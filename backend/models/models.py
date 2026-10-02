"""
SmartFarm AI - All Database Models
Phase 1: Complete data model for the farming application.

Relationship tree:
  User
   └── Farm
        ├── SoilProfile
        ├── Field
        │    └── Crop
        │         └── CropStage
        ├── IrrigationRecord
        ├── FarmTask
        └── Notification

WeatherRecord and CropCatalog are independent tables.
"""
import enum
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, Boolean, Text, DateTime, Date,
    ForeignKey, Enum as SAEnum, JSON, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database.connection import Base


# ─────────────────────────────────────────────
# ENUMERATIONS
# ─────────────────────────────────────────────

class SoilType(str, enum.Enum):
    sandy = "sandy"
    loamy = "loamy"
    clay = "clay"
    silty = "silty"
    peaty = "peaty"
    chalky = "chalky"
    sandy_loam = "sandy_loam"
    clay_loam = "clay_loam"


class IrrigationMethod(str, enum.Enum):
    drip = "drip"
    flood = "flood"
    sprinkler = "sprinkler"
    furrow = "furrow"
    rainfed = "rainfed"


class WaterSource(str, enum.Enum):
    canal = "canal"
    borewell = "borewell"
    river = "river"
    rainwater = "rainwater"
    pond = "pond"
    well = "well"


class Season(str, enum.Enum):
    kharif = "kharif"       # June–November (monsoon)
    rabi = "rabi"           # November–April (winter)
    zaid = "zaid"           # April–June (summer)
    perennial = "perennial"


class CropStatus(str, enum.Enum):
    planned = "planned"
    active = "active"
    harvested = "harvested"
    failed = "failed"


class GrowthStage(str, enum.Enum):
    land_preparation = "land_preparation"
    sowing = "sowing"
    germination = "germination"
    vegetative = "vegetative"
    flowering = "flowering"
    maturity = "maturity"
    harvest = "harvest"


class TaskStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    skipped = "skipped"


class TaskType(str, enum.Enum):
    irrigation = "irrigation"
    fertilization = "fertilization"
    pest_control = "pest_control"
    inspection = "inspection"
    harvesting = "harvesting"
    land_prep = "land_prep"
    sowing = "sowing"
    general = "general"


class NotificationType(str, enum.Enum):
    irrigation = "irrigation"
    weather_alert = "weather_alert"
    crop_reminder = "crop_reminder"
    risk_alert = "risk_alert"
    daily_summary = "daily_summary"
    market_info = "market_info"


class NotificationChannel(str, enum.Enum):
    telegram = "telegram"
    dashboard = "dashboard"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class SuitabilityLevel(str, enum.Enum):
    highly_suitable = "highly_suitable"
    suitable = "suitable"
    moderate = "moderate"
    not_suitable = "not_suitable"


# ─────────────────────────────────────────────
# USER MODEL
# ─────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(200), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    # Telegram
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    telegram_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    telegram_link_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    telegram_link_expires: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Notification Preferences
    notify_irrigation: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_weather: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_crops: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_risks: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_daily_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    preferred_notify_time: Mapped[str] = mapped_column(String(5), default="07:00")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    farms: Mapped[List["Farm"]] = relationship("Farm", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User id={self.id} name={self.name!r}>"


# ─────────────────────────────────────────────
# FARM MODEL
# ─────────────────────────────────────────────

class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)  # city/district name
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_area_acres: Mapped[float] = mapped_column(Float, nullable=False)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[str] = mapped_column(String(100), default="India")

    irrigation_method: Mapped[IrrigationMethod] = mapped_column(
        SAEnum(IrrigationMethod), default=IrrigationMethod.flood
    )
    water_source: Mapped[WaterSource] = mapped_column(
        SAEnum(WaterSource), default=WaterSource.borewell
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="farms")
    soil_profile: Mapped[Optional["SoilProfile"]] = relationship(
        "SoilProfile", back_populates="farm", cascade="all, delete-orphan", uselist=False
    )
    fields: Mapped[List["Field"]] = relationship("Field", back_populates="farm", cascade="all, delete-orphan")
    irrigation_records: Mapped[List["IrrigationRecord"]] = relationship(
        "IrrigationRecord", back_populates="farm", cascade="all, delete-orphan"
    )
    farm_tasks: Mapped[List["FarmTask"]] = relationship(
        "FarmTask", back_populates="farm", cascade="all, delete-orphan"
    )
    weather_records: Mapped[List["WeatherRecord"]] = relationship(
        "WeatherRecord", back_populates="farm", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Farm id={self.id} name={self.name!r} location={self.location!r}>"


# ─────────────────────────────────────────────
# SOIL PROFILE
# ─────────────────────────────────────────────

class SoilProfile(Base):
    __tablename__ = "soil_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    farm_id: Mapped[int] = mapped_column(Integer, ForeignKey("farms.id"), nullable=False, unique=True)

    soil_type: Mapped[SoilType] = mapped_column(SAEnum(SoilType), default=SoilType.loamy)
    ph_level: Mapped[Optional[float]] = mapped_column(Float, nullable=True)           # 0–14
    organic_matter_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    nitrogen_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    phosphorus_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    potassium_kg_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    water_holding_capacity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # low/medium/high
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    farm: Mapped["Farm"] = relationship("Farm", back_populates="soil_profile")

    def __repr__(self):
        return f"<SoilProfile farm_id={self.farm_id} type={self.soil_type} pH={self.ph_level}>"


# ─────────────────────────────────────────────
# FIELD MODEL
# ─────────────────────────────────────────────

class Field(Base):
    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    farm_id: Mapped[int] = mapped_column(Integer, ForeignKey("farms.id"), nullable=False)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    area_acres: Mapped[float] = mapped_column(Float, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="fields")
    crops: Mapped[List["Crop"]] = relationship("Crop", back_populates="field", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Field id={self.id} name={self.name!r} area={self.area_acres}ac>"


# ─────────────────────────────────────────────
# CROP CATALOG (reference data, not farm-specific)
# ─────────────────────────────────────────────

class CropCatalog(Base):
    """
    Static crop reference information.
    Seeded at startup from data/crops/crops.json.
    """
    __tablename__ = "crop_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    crop_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    local_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    season: Mapped[Season] = mapped_column(SAEnum(Season), nullable=False)
    temperature_min_c: Mapped[float] = mapped_column(Float, nullable=False)
    temperature_max_c: Mapped[float] = mapped_column(Float, nullable=False)
    rainfall_requirement_mm: Mapped[float] = mapped_column(Float, nullable=False)
    water_requirement_mm_per_day: Mapped[float] = mapped_column(Float, nullable=False)
    growth_duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    soil_preferences: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON-encoded list
    sowing_window_start: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # MM-DD
    sowing_window_end: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    growth_stages: Mapped[Optional[str]] = mapped_column(Text, nullable=True)      # JSON-encoded list
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    market_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # name for mandi lookup

    def __repr__(self):
        return f"<CropCatalog name={self.crop_name!r} season={self.season}>"


# ─────────────────────────────────────────────
# CROP (farm-specific planting)
# ─────────────────────────────────────────────

class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    field_id: Mapped[int] = mapped_column(Integer, ForeignKey("fields.id"), nullable=False)
    catalog_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crop_catalog.id"), nullable=True)

    crop_name: Mapped[str] = mapped_column(String(100), nullable=False)
    variety: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    area_acres: Mapped[float] = mapped_column(Float, nullable=False)
    sowing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_harvest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[CropStatus] = mapped_column(SAEnum(CropStatus), default=CropStatus.active)
    current_stage: Mapped[GrowthStage] = mapped_column(SAEnum(GrowthStage), default=GrowthStage.sowing)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    field: Mapped["Field"] = relationship("Field", back_populates="crops")
    catalog: Mapped[Optional["CropCatalog"]] = relationship("CropCatalog")
    crop_stages: Mapped[List["CropStage"]] = relationship("CropStage", back_populates="crop", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Crop id={self.id} name={self.crop_name!r} status={self.status}>"


# ─────────────────────────────────────────────
# CROP STAGE TRACKING
# ─────────────────────────────────────────────

class CropStage(Base):
    __tablename__ = "crop_stages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    crop_id: Mapped[int] = mapped_column(Integer, ForeignKey("crops.id"), nullable=False)

    stage: Mapped[GrowthStage] = mapped_column(SAEnum(GrowthStage), nullable=False)
    started_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expected_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    actual_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    crop: Mapped["Crop"] = relationship("Crop", back_populates="crop_stages")

    def __repr__(self):
        return f"<CropStage crop_id={self.crop_id} stage={self.stage}>"


# ─────────────────────────────────────────────
# IRRIGATION RECORD
# ─────────────────────────────────────────────

class IrrigationRecord(Base):
    __tablename__ = "irrigation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    farm_id: Mapped[int] = mapped_column(Integer, ForeignKey("farms.id"), nullable=False)
    crop_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crops.id"), nullable=True)

    scheduled_date: Mapped[date] = mapped_column(Date, nullable=False)
    actual_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    recommended_amount_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    actual_amount_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    method: Mapped[Optional[IrrigationMethod]] = mapped_column(SAEnum(IrrigationMethod), nullable=True)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_reason: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="irrigation_records")
    crop: Mapped[Optional["Crop"]] = relationship("Crop")

    def __repr__(self):
        return f"<IrrigationRecord farm_id={self.farm_id} date={self.scheduled_date} mm={self.recommended_amount_mm}>"


# ─────────────────────────────────────────────
# FARM TASK
# ─────────────────────────────────────────────

class FarmTask(Base):
    __tablename__ = "farm_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    farm_id: Mapped[int] = mapped_column(Integer, ForeignKey("farms.id"), nullable=False)
    crop_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("crops.id"), nullable=True)

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    task_type: Mapped[TaskType] = mapped_column(SAEnum(TaskType), default=TaskType.general)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.pending)
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1=high, 2=medium, 3=low
    auto_generated: Mapped[bool] = mapped_column(Boolean, default=False)

    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    farm: Mapped["Farm"] = relationship("Farm", back_populates="farm_tasks")
    crop: Mapped[Optional["Crop"]] = relationship("Crop")

    def __repr__(self):
        return f"<FarmTask id={self.id} title={self.title!r} status={self.status}>"


# ─────────────────────────────────────────────
# WEATHER RECORD
# ─────────────────────────────────────────────

class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    farm_id: Mapped[int] = mapped_column(Integer, ForeignKey("farms.id"), nullable=False)

    recorded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    temperature_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feels_like_c: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_speed_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    wind_direction: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    cloud_cover_percent: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    weather_description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    weather_icon: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    rain_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationship
    farm: Mapped["Farm"] = relationship("Farm", back_populates="weather_records")

    __table_args__ = (
        UniqueConstraint("farm_id", "recorded_at", name="uq_weather_farm_time"),
    )

    def __repr__(self):
        return f"<WeatherRecord farm_id={self.farm_id} at={self.recorded_at} temp={self.temperature_c}°C>"


# ─────────────────────────────────────────────
# NOTIFICATION
# ─────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    farm_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("farms.id"), nullable=True)

    notification_type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType), nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(SAEnum(NotificationChannel), default=NotificationChannel.dashboard)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    sent: Mapped[bool] = mapped_column(Boolean, default=False)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    dedup_key: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, index=True)  # prevent duplicates

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification id={self.id} type={self.notification_type} sent={self.sent}>"
