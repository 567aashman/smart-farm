"""
SmartFarm - Crops API Routes (Phases 2, 5, 6)
Crop management, catalog, calendar, and recommendations.
"""
import logging
import json
from datetime import date
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Crop, Field, CropCatalog, Farm
from backend.models.models import CropStatus, GrowthStage
from backend.schemas.schemas import CropCreate, CropUpdate, CropResponse, CropCatalogResponse
from backend.agriculture.crop_calendar import crop_calendar_service
from backend.agriculture.crop_recommendation import crop_recommendation_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/crops", tags=["Crops"])


# ─── CATALOG ───

@router.get("/catalog", response_model=List[CropCatalogResponse])
def get_crop_catalog(db: Session = Depends(get_db)):
    """List all crops in the reference catalog."""
    return db.query(CropCatalog).all()


@router.get("/catalog/{crop_name}")
def get_catalog_crop(crop_name: str, db: Session = Depends(get_db)):
    crop = db.query(CropCatalog).filter(CropCatalog.crop_name.ilike(crop_name)).first()
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_name}' not in catalog")
    return crop


# ─── FARM CROPS ───

@router.post("/", response_model=CropResponse, status_code=status.HTTP_201_CREATED)
def create_crop(payload: CropCreate, db: Session = Depends(get_db)):
    """Add a crop to a field."""
    field = db.query(Field).filter(Field.id == payload.field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    # Link to catalog if exists
    catalog = db.query(CropCatalog).filter(CropCatalog.crop_name.ilike(payload.crop_name)).first()

    # Calculate expected harvest date
    expected_harvest = None
    if payload.sowing_date and catalog:
        from datetime import timedelta
        expected_harvest = payload.sowing_date + timedelta(days=catalog.growth_duration_days)

    crop = Crop(
        field_id=payload.field_id,
        catalog_id=catalog.id if catalog else None,
        crop_name=payload.crop_name.title(),
        variety=payload.variety,
        area_acres=payload.area_acres,
        sowing_date=payload.sowing_date,
        expected_harvest_date=expected_harvest,
        notes=payload.notes,
        status=CropStatus.active,
        current_stage=GrowthStage.sowing if payload.sowing_date else GrowthStage.land_preparation,
    )
    db.add(crop)
    db.commit()
    db.refresh(crop)

    # Auto-generate calendar tasks if sowing date is set
    if payload.sowing_date and crop.field:
        _auto_generate_tasks(db, crop, field.farm_id)

    logger.info(f"Crop created: {crop.id} ({crop.crop_name}) in field {payload.field_id}")
    return crop


@router.get("/field/{field_id}", response_model=List[CropResponse])
def get_field_crops(field_id: int, db: Session = Depends(get_db)):
    return db.query(Crop).filter(Crop.field_id == field_id).all()


@router.get("/farm/{farm_id}")
def get_farm_crops(farm_id: int, db: Session = Depends(get_db)):
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    result = []
    for field in farm.fields:
        for crop in field.crops:
            result.append({
                "crop_id": crop.id,
                "crop_name": crop.crop_name,
                "variety": crop.variety,
                "field_name": field.name,
                "field_id": field.id,
                "area_acres": crop.area_acres,
                "sowing_date": crop.sowing_date.isoformat() if crop.sowing_date else None,
                "expected_harvest_date": crop.expected_harvest_date.isoformat() if crop.expected_harvest_date else None,
                "status": crop.status.value,
                "current_stage": crop.current_stage.value if crop.current_stage else None,
            })
    return result


@router.get("/{crop_id}", response_model=CropResponse)
def get_crop(crop_id: int, db: Session = Depends(get_db)):
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    return crop


@router.put("/{crop_id}", response_model=CropResponse)
def update_crop(crop_id: int, payload: CropUpdate, db: Session = Depends(get_db)):
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        if field == "status":
            value = CropStatus(value)
        elif field == "current_stage":
            value = GrowthStage(value)
        setattr(crop, field, value)

    db.commit()
    db.refresh(crop)
    return crop


@router.delete("/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crop(crop_id: int, db: Session = Depends(get_db)):
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    db.delete(crop)
    db.commit()


# ─── CROP CALENDAR ───

@router.get("/{crop_id}/calendar")
def get_crop_calendar(crop_id: int, db: Session = Depends(get_db)):
    """Get crop growth calendar and upcoming tasks."""
    crop = db.query(Crop).filter(Crop.id == crop_id).first()
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    if not crop.sowing_date:
        raise HTTPException(status_code=400, detail="Sowing date not set for this crop")

    return crop_calendar_service.generate_calendar(
        crop_name=crop.crop_name,
        sowing_date=crop.sowing_date,
        field_name=crop.field.name if crop.field else "Field",
        area_acres=crop.area_acres,
    )


# ─── CROP RECOMMENDATIONS ───

@router.get("/recommendations/farm/{farm_id}")
def get_crop_recommendations(farm_id: int, month: int = None, db: Session = Depends(get_db)):
    """Get crop recommendations for a farm based on soil, season, and weather."""
    farm = db.query(Farm).filter(Farm.id == farm_id).first()
    if not farm:
        raise HTTPException(status_code=404, detail="Farm not found")

    soil = farm.soil_profile
    soil_type = soil.soil_type.value if soil else "loamy"

    # Use default temperature and rainfall (updated via weather service in production)
    return crop_recommendation_engine.recommend(
        location=farm.location,
        soil_type=soil_type,
        temperature_c=25.0,
        rainfall_mm=500.0,
        month=month,
        water_availability="medium" if farm.water_source else "low",
    )


# ─── HELPERS ───

def _auto_generate_tasks(db: Session, crop: Crop, farm_id: int):
    """Generate FarmTasks from crop calendar when a crop is created."""
    from backend.models import FarmTask
    from backend.models.models import TaskType, TaskStatus
    try:
        calendar = crop_calendar_service.generate_calendar(
            crop.crop_name, crop.sowing_date,
            field_name=crop.field.name if crop.field else "Field"
        )
        for task_data in calendar.get("generated_tasks", []):
            task = FarmTask(
                farm_id=farm_id,
                crop_id=crop.id,
                title=task_data["title"],
                description=task_data.get("description"),
                task_type=TaskType(task_data.get("task_type", "general")),
                due_date=date.fromisoformat(task_data["due_date"]) if task_data.get("due_date") else None,
                priority=task_data.get("priority", 2),
                auto_generated=True,
                status=TaskStatus.pending,
            )
            db.add(task)
        db.commit()
        logger.info(f"Auto-generated {len(calendar.get('generated_tasks', []))} tasks for crop {crop.id}")
    except Exception as e:
        logger.error(f"Failed to auto-generate tasks for crop {crop.id}: {e}")
