"""
SmartFarm - Crop Calendar Service (Phase 6)
Generates crop stage timelines and farm tasks from sowing date.
"""
import json
import logging
import os
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "crops", "crops.json"
)

STAGE_ICONS = {
    "land_preparation": "🌱",
    "sowing":           "🌾",
    "germination":      "🌿",
    "vegetative":       "🍃",
    "flowering":        "🌸",
    "maturity":         "🌻",
    "harvest":          "🚜",
}

STAGE_TASKS = {
    "land_preparation": [
        "Plough and prepare the field",
        "Add basal fertilizer (NPK as recommended)",
        "Level the field for uniform irrigation",
        "Check and repair irrigation infrastructure",
    ],
    "sowing": [
        "Treat seeds with recommended fungicide",
        "Sow seeds at the recommended depth and spacing",
        "Apply pre-emergence herbicide if needed",
        "Record the sowing date",
    ],
    "germination": [
        "Monitor germination rate (expect 85%+)",
        "Apply light irrigation if soil is dry",
        "Watch for early pest damage",
        "Ensure adequate soil moisture",
    ],
    "vegetative": [
        "Apply top-dress nitrogen fertilizer",
        "Monitor for pests and diseases",
        "Irrigate as per schedule",
        "Remove weeds",
        "Inspect crop health weekly",
    ],
    "flowering": [
        "Do NOT apply pesticides during flowering",
        "Ensure adequate irrigation — this is the critical stage",
        "Monitor for fruit/grain set",
        "Watch for pollinators",
        "Avoid any stress during this stage",
    ],
    "maturity": [
        "Reduce irrigation frequency",
        "Monitor grain/fruit development",
        "Prepare harvesting equipment",
        "Check moisture content",
    ],
    "harvest": [
        "Harvest at optimal moisture content",
        "Dry produce to safe storage moisture",
        "Store in clean, dry storage",
        "Check mandi prices before selling",
        "Record yield for future planning",
    ],
}


class CropCalendarService:
    """
    Generates crop calendar from sowing date + crop growth stages.
    """

    def __init__(self):
        self._catalog: Optional[List[Dict]] = None

    def _load_catalog(self) -> List[Dict]:
        if self._catalog is None:
            try:
                with open(DATA_PATH, "r") as f:
                    self._catalog = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load crop catalog: {e}")
                self._catalog = []
        return self._catalog

    def _get_crop_info(self, crop_name: str) -> Optional[Dict]:
        catalog = self._load_catalog()
        for c in catalog:
            if c["crop_name"].lower() == crop_name.lower():
                return c
        return None

    def generate_calendar(
        self,
        crop_name: str,
        sowing_date: date,
        field_name: str = "Field",
        area_acres: float = 1.0,
    ) -> Dict[str, Any]:
        """
        Generate full crop calendar from sowing date.

        Returns:
            Dict with stages list, timeline, and generated tasks.
        """
        crop_info = self._get_crop_info(crop_name)
        if not crop_info:
            logger.warning(f"Crop '{crop_name}' not in catalog — using generic stages")
            stages = self._generic_stages()
        else:
            stages = crop_info.get("growth_stages", self._generic_stages())

        today = date.today()
        current_date = sowing_date
        calendar_stages = []
        all_tasks = []
        current_stage_name = None

        for stage_info in stages:
            stage_name = stage_info["stage"]
            duration = stage_info["duration_days"]
            stage_end = current_date + timedelta(days=duration)

            is_current = current_date <= today < stage_end
            is_past = today >= stage_end
            is_future = today < current_date

            if is_current:
                current_stage_name = stage_name
                days_in_stage = (today - current_date).days
                days_remaining = (stage_end - today).days
            else:
                days_in_stage = None
                days_remaining = None

            calendar_stages.append({
                "stage": stage_name,
                "icon": STAGE_ICONS.get(stage_name, "📅"),
                "start_date": current_date.isoformat(),
                "end_date": stage_end.isoformat(),
                "duration_days": duration,
                "is_current": is_current,
                "is_past": is_past,
                "is_future": is_future,
                "days_in_stage": days_in_stage,
                "days_remaining": days_remaining,
            })

            # Generate tasks for this stage
            if is_current or (is_future and (current_date - today).days <= 7):
                tasks = self._generate_stage_tasks(
                    stage_name, crop_name, field_name, area_acres,
                    current_date, stage_end
                )
                all_tasks.extend(tasks)

            current_date = stage_end

        expected_harvest = current_date

        return {
            "crop_name": crop_name,
            "field_name": field_name,
            "sowing_date": sowing_date.isoformat(),
            "expected_harvest_date": expected_harvest.isoformat(),
            "current_stage": current_stage_name,
            "stages": calendar_stages,
            "generated_tasks": all_tasks,
            "total_duration_days": (expected_harvest - sowing_date).days,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_current_stage(self, crop_name: str, sowing_date: date) -> Optional[str]:
        """Returns the name of the current growth stage."""
        calendar = self.generate_calendar(crop_name, sowing_date)
        return calendar.get("current_stage")

    def get_upcoming_stage(self, crop_name: str, sowing_date: date) -> Optional[Dict]:
        """Returns the next upcoming stage details."""
        calendar = self.generate_calendar(crop_name, sowing_date)
        for stage in calendar["stages"]:
            if stage["is_future"]:
                return stage
        return None

    def _generate_stage_tasks(
        self, stage_name: str, crop_name: str, field_name: str,
        area_acres: float, stage_start: date, stage_end: date
    ) -> List[Dict]:
        """Generate FarmTask dicts for a given stage."""
        task_templates = STAGE_TASKS.get(stage_name, ["Monitor the crop"])
        tasks = []
        for i, template in enumerate(task_templates):
            due = stage_start + timedelta(days=i * 2)
            due = min(due, stage_end - timedelta(days=1))
            tasks.append({
                "title": f"{crop_name}: {template}",
                "description": f"Task for {crop_name} in {field_name} during {stage_name} stage.",
                "task_type": self._task_type(template),
                "due_date": due.isoformat(),
                "priority": 1 if stage_name == "flowering" else 2,
                "stage": stage_name,
            })
        return tasks

    def _task_type(self, title: str) -> str:
        t = title.lower()
        if "irrigat" in t:
            return "irrigation"
        elif "fertil" in t or "npk" in t:
            return "fertilization"
        elif "pest" in t or "disease" in t or "spray" in t:
            return "pest_control"
        elif "harvest" in t or "yield" in t:
            return "harvesting"
        elif "plough" in t or "prepare" in t or "level" in t:
            return "land_prep"
        elif "sow" in t or "seed" in t:
            return "sowing"
        else:
            return "inspection"

    def _generic_stages(self) -> List[Dict]:
        return [
            {"stage": "land_preparation", "duration_days": 7},
            {"stage": "sowing",           "duration_days": 3},
            {"stage": "germination",      "duration_days": 10},
            {"stage": "vegetative",       "duration_days": 40},
            {"stage": "flowering",        "duration_days": 20},
            {"stage": "maturity",         "duration_days": 20},
            {"stage": "harvest",          "duration_days": 5},
        ]


# Module-level singleton
crop_calendar_service = CropCalendarService()
