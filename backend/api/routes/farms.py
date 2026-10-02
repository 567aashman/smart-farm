"""
SmartFarm - Farms API Routes (Phase 2)
Farm, soil, and field management endpoints.
"""
import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Farm, SoilProfile, Field, User
from backend.schemas.schemas import (
    FarmCreate, FarmUpdate, FarmResponse,
    SoilProfileCreate, SoilProfileResponse,
    FieldCreate, FieldResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/farms", tags=["Farms"])


# ─── FARM CRUD ───

@router.post("/", response_model=FarmResponse, status_code=status.HTTP_201_CREATED)
def create_farm(payload: FarmCreate, user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    from backend.models.models import IrrigationMethod, WaterSource
    farm = Farm(
        user_id=user_id,
        name=payload.name,
        location=payload.location,
        latitude=payload.latitude,
        longitude=payload.longitude,
        total_area_acres=payload.total_area_acres,
        state=payload.state,
        country=payload.country,
        irrigation_method=IrrigationMethod(payload.irrigation_method),
        water_source=WaterSource(payload.water_source),
    )
    db.add(farm)
    db.commit()
    db.refresh(farm)
    logger.info(f"Farm created: {farm.id} ({farm.name}) for user {user_id}")
    return farm


@router.get("/user/{user_id}", response_model=List[FarmResponse])
def get_user_farms(user_id: int, db: Session = Depends(get_db)):
    return db.query(Farm).filter(Farm.user_id == user_id).all()


@router.get("/{farm_id}", response_model=FarmResponse)
def get_farm(farm_id: int, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    return farm


@router.put("/{farm_id}", response_model=FarmResponse)
def update_farm(farm_id: int, payload: FarmUpdate, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "irrigation_method":
            from backend.models.models import IrrigationMethod
            value = IrrigationMethod(value)
        elif field == "water_source":
            from backend.models.models import WaterSource
            value = WaterSource(value)
        setattr(farm, field, value)

    db.commit()
    db.refresh(farm)
    return farm


@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm(farm_id: int, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")
    db.delete(farm)
    db.commit()


# ─── SOIL PROFILE ───

@router.post("/{farm_id}/soil", response_model=SoilProfileResponse, status_code=status.HTTP_201_CREATED)
def create_soil_profile(farm_id: int, payload: SoilProfileCreate, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    existing = db.query(SoilProfile).filter(SoilProfile.farm_id == farm_id).first()
    if existing:
        # Update existing
        for field, value in payload.model_dump(exclude_none=True).items():
            if field == "soil_type":
                from backend.models.models import SoilType
                value = SoilType(value)
            setattr(existing, field, value)
        db.commit()
        db.refresh(existing)
        return existing

    from backend.models.models import SoilType
    soil = SoilProfile(
        farm_id=farm_id,
        soil_type=SoilType(payload.soil_type),
        ph_level=payload.ph_level,
        organic_matter_percent=payload.organic_matter_percent,
        nitrogen_kg_per_ha=payload.nitrogen_kg_per_ha,
        phosphorus_kg_per_ha=payload.phosphorus_kg_per_ha,
        potassium_kg_per_ha=payload.potassium_kg_per_ha,
        water_holding_capacity=payload.water_holding_capacity,
        notes=payload.notes,
    )
    db.add(soil)
    db.commit()
    db.refresh(soil)
    return soil


@router.get("/{farm_id}/soil", response_model=SoilProfileResponse)
def get_soil_profile(farm_id: int, db: Session = Depends(get_db)):
    soil = db.query(SoilProfile).filter(SoilProfile.farm_id == farm_id).first()
    if not soil:
        raise HTTPException(status_code=404, detail="Soil profile not found")
    return soil


# ─── FIELDS ───

@router.post("/{farm_id}/fields", response_model=FieldResponse, status_code=status.HTTP_201_CREATED)
def create_field(farm_id: int, payload: FieldCreate, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    field = Field(farm_id=farm_id, name=payload.name, area_acres=payload.area_acres, notes=payload.notes)
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.get("/{farm_id}/fields", response_model=List[FieldResponse])
def get_fields(farm_id: int, db: Session = Depends(get_db)):
    return db.query(Field).filter(Field.farm_id == farm_id).all()


@router.delete("/{farm_id}/fields/{field_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_field(farm_id: int, field_id: int, db: Session = Depends(get_db)):
    field = db.query(Field).filter(Field.id == field_id, Field.farm_id == farm_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    db.delete(field)
    db.commit()


# ─── ANALYTICS ───

@router.get("/{farm_id}/analytics")
def get_farm_analytics(farm_id: int, db: Session = Depends(get_db)):
    from datetime import datetime, timedelta
    from backend.models import IrrigationRecord, FarmTask, WeatherRecord

    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    since_30 = datetime.utcnow() - timedelta(days=30)

    active_crops = [
        {"crop_name": c.crop_name, "area_acres": c.area_acres, "stage": c.current_stage.value if c.current_stage else "unknown"}
        for field in farm.fields for c in field.crops if c.status.value == "active"
    ]

    irr_events = (
        db.query(IrrigationRecord)
        .filter(IrrigationRecord.farm_id == farm_id, IrrigationRecord.created_at >= since_30)
        .count()
    )

    water_used = (
        db.query(IrrigationRecord)
        .filter(IrrigationRecord.farm_id == farm_id, IrrigationRecord.completed == True, IrrigationRecord.created_at >= since_30)
        .all()
    )
    total_water = sum((r.actual_amount_mm or 0) for r in water_used)

    weather_recs = (
        db.query(WeatherRecord)
        .filter(WeatherRecord.farm_id == farm_id, WeatherRecord.recorded_at >= since_30)
        .all()
    )
    total_rainfall = sum((r.rainfall_mm or 0) for r in weather_recs)

    pending = db.query(FarmTask).filter(FarmTask.farm_id == farm_id, FarmTask.status == "pending").count()
    overdue = (
        db.query(FarmTask)
        .filter(FarmTask.farm_id == farm_id, FarmTask.status == "pending",
                FarmTask.due_date < datetime.utcnow().date())
        .count()
    )

    return {
        "farm_id": farm_id,
        "farm_name": farm.name,
        "total_area_acres": farm.total_area_acres,
        "active_crops": len(active_crops),
        "crop_details": active_crops,
        "irrigation_events_last_30_days": irr_events,
        "estimated_water_used_mm": round(total_water, 1),
        "total_rainfall_mm": round(total_rainfall, 1),
        "pending_tasks": pending,
        "overdue_tasks": overdue,
        "active_risks": 0,  # filled by risk engine on demand
        "generated_at": datetime.utcnow().isoformat(),
    }
