"""
SmartFarm AI - FarmAI Tools (Phase 10)
Tools that the Groq AI agent can call to fetch real farm/weather data.
The AI must never invent weather, farm, or irrigation data.
All values come from the actual services and database.
"""
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from backend.models import Crop, Farm, Field, SoilProfile, FarmTask, IrrigationRecord
from backend.agriculture.irrigation_engine import irrigation_engine
from backend.agriculture.crop_recommendation import crop_recommendation_engine
from backend.agriculture.crop_calendar import crop_calendar_service
from backend.agriculture.risk_engine import risk_engine
from backend.agriculture.action_plan import action_plan_engine

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# TOOL DEFINITIONS (Groq function-calling format)
# ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_farm_profile",
            "description": "Get the farmer's farm profile including location, area, soil, and irrigation method.",
            "parameters": {
                "type": "object",
                "properties": {
                    "farm_id": {"type": "integer", "description": "The farm ID"}
                },
                "required": ["farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_active_crops",
            "description": "Get all currently active crops on the farm with their stages and sowing dates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "farm_id": {"type": "integer", "description": "The farm ID"}
                },
                "required": ["farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crop_stage",
            "description": "Get the current growth stage of a specific crop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop_id": {"type": "integer", "description": "The crop ID"},
                    "farm_id": {"type": "integer", "description": "The farm ID"}
                },
                "required": ["crop_id", "farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_weather",
            "description": "Get current weather conditions for the farm location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "farm_id": {"type": "integer", "description": "The farm ID"}
                },
                "required": ["farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather_forecast",
            "description": "Get 5-day weather forecast for the farm location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "farm_id": {"type": "integer", "description": "The farm ID"},
                    "days": {"type": "integer", "description": "Number of forecast days (1-5)", "default": 5}
                },
                "required": ["farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_irrigation",
            "description": "Calculate whether irrigation is needed for the farm, when, and how much water.",
            "parameters": {
                "type": "object",
                "properties": {
                    "farm_id": {"type": "integer", "description": "The farm ID"},
                    "crop_id": {"type": "integer", "description": "Optional specific crop ID"}
                },
                "required": ["farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crop_recommendations",
            "description": "Get crop recommendations for the farm based on season, soil, and weather.",
            "parameters": {
                "type": "object",
                "properties": {
                    "farm_id": {"type": "integer", "description": "The farm ID"}
                },
                "required": ["farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_crop_calendar",
            "description": "Get the crop growth calendar showing all stages and upcoming tasks for a crop.",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop_id": {"type": "integer", "description": "The crop ID"},
                    "farm_id": {"type": "integer", "description": "The farm ID"}
                },
                "required": ["crop_id", "farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_risk_analysis",
            "description": "Get weather and crop risk analysis for the farm.",
            "parameters": {
                "type": "object",
                "properties": {
                    "farm_id": {"type": "integer", "description": "The farm ID"}
                },
                "required": ["farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_action_plan",
            "description": "Get the 7-day farm action plan combining weather, irrigation, and crop tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "farm_id": {"type": "integer", "description": "The farm ID"}
                },
                "required": ["farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_mandi_prices",
            "description": "Get current mandi (market) prices for crops. Note: price data may not always be available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop_name": {"type": "string", "description": "Name of the crop"},
                    "location": {"type": "string", "description": "Market location or city"}
                },
                "required": ["crop_name", "location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_fertilizer_plan",
            "description": "Calculate NPK (Nitrogen, Phosphorus, Potassium) fertilizer requirements for a farm based on its soil profile and active crops.",
            "parameters": {
                "type": "object",
                "properties": {
                    "farm_id": {"type": "integer", "description": "The farm ID"}
                },
                "required": ["farm_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_crop_disease",
            "description": "Diagnose potential crop diseases based on observed symptoms and current weather conditions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "crop_name": {"type": "string", "description": "Name of the affected crop"},
                    "symptoms": {"type": "string", "description": "Detailed description of the observed symptoms (e.g., yellowing leaves, brown spots)"},
                    "farm_id": {"type": "integer", "description": "Optional farm ID to include local weather context"}
                },
                "required": ["crop_name", "symptoms"]
            }
        }
    },
]


# ─────────────────────────────────────────────
# TOOL EXECUTOR
# ─────────────────────────────────────────────

class FarmToolExecutor:
    """
    Executes tool calls from the Groq AI.
    Fetches real data from the database and services.
    """

    def __init__(self, db: Session, weather_service=None, market_service=None):
        self.db = db
        self.weather_service = weather_service
        self.market_service = market_service

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> str:
        """Execute a tool and return JSON string result."""
        import json

        logger.info(f"FarmAI tool call: {tool_name}({args})")

        try:
            if tool_name == "get_farm_profile":
                result = self._get_farm_profile(args["farm_id"])
            elif tool_name == "get_active_crops":
                result = self._get_active_crops(args["farm_id"])
            elif tool_name == "get_crop_stage":
                result = self._get_crop_stage(args["crop_id"], args["farm_id"])
            elif tool_name == "get_current_weather":
                result = await self._get_current_weather(args["farm_id"])
            elif tool_name == "get_weather_forecast":
                result = await self._get_weather_forecast(args["farm_id"], args.get("days", 5))
            elif tool_name == "calculate_irrigation":
                result = await self._calculate_irrigation(args["farm_id"], args.get("crop_id"))
            elif tool_name == "get_crop_recommendations":
                result = await self._get_crop_recommendations(args["farm_id"])
            elif tool_name == "get_crop_calendar":
                result = self._get_crop_calendar(args["crop_id"], args["farm_id"])
            elif tool_name == "get_risk_analysis":
                result = await self._get_risk_analysis(args["farm_id"])
            elif tool_name == "get_action_plan":
                result = await self._get_action_plan(args["farm_id"])
            elif tool_name == "get_mandi_prices":
                result = await self._get_mandi_prices(args["crop_name"], args["location"])
            elif tool_name == "get_fertilizer_plan":
                result = self._get_fertilizer_plan(args["farm_id"])
            elif tool_name == "diagnose_crop_disease":
                result = await self._diagnose_crop_disease(args["crop_name"], args["symptoms"], args.get("farm_id"))
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            logger.error(f"Tool {tool_name} error: {e}", exc_info=True)
            result = {"error": f"Tool execution failed: {str(e)}"}

        return json.dumps(result, default=str)

    # ── Farm Profile ──

    def _get_farm_profile(self, farm_id: int) -> Dict:
        farm = self.db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            return {"error": f"Farm {farm_id} not found"}
        soil = farm.soil_profile
        return {
            "farm_id": farm.id,
            "name": farm.name,
            "location": farm.location,
            "state": farm.state,
            "total_area_acres": farm.total_area_acres,
            "irrigation_method": farm.irrigation_method.value if farm.irrigation_method else None,
            "water_source": farm.water_source.value if farm.water_source else None,
            "soil": {
                "type": soil.soil_type.value if soil else "unknown",
                "ph": soil.ph_level if soil else None,
                "water_holding": soil.water_holding_capacity if soil else None,
            } if soil else None,
        }

    # ── Active Crops ──

    def _get_active_crops(self, farm_id: int) -> Dict:
        farm = self.db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            return {"error": f"Farm {farm_id} not found"}

        crops = []
        for field in farm.fields:
            for crop in field.crops:
                if crop.status.value == "active":
                    crops.append({
                        "crop_id": crop.id,
                        "crop_name": crop.crop_name,
                        "variety": crop.variety,
                        "field_name": field.name,
                        "area_acres": crop.area_acres,
                        "sowing_date": crop.sowing_date.isoformat() if crop.sowing_date else None,
                        "current_stage": crop.current_stage.value if crop.current_stage else None,
                        "expected_harvest_date": crop.expected_harvest_date.isoformat() if crop.expected_harvest_date else None,
                    })

        return {"farm_id": farm_id, "active_crops": crops, "count": len(crops)}

    # ── Crop Stage ──

    def _get_crop_stage(self, crop_id: int, farm_id: int) -> Dict:
        crop = self.db.query(Crop).filter(Crop.id == crop_id).first()
        if not crop:
            return {"error": f"Crop {crop_id} not found"}

        calendar = {}
        if crop.sowing_date:
            calendar = crop_calendar_service.generate_calendar(
                crop.crop_name, crop.sowing_date,
                field_name=crop.field.name if crop.field else "Field"
            )

        return {
            "crop_id": crop.id,
            "crop_name": crop.crop_name,
            "current_stage": crop.current_stage.value if crop.current_stage else None,
            "sowing_date": crop.sowing_date.isoformat() if crop.sowing_date else None,
            "expected_harvest": crop.expected_harvest_date.isoformat() if crop.expected_harvest_date else None,
            "stages_summary": [
                {
                    "stage": s["stage"],
                    "start_date": s["start_date"],
                    "end_date": s["end_date"],
                    "is_current": s["is_current"],
                    "days_remaining": s.get("days_remaining"),
                }
                for s in calendar.get("stages", [])
            ],
        }

    # ── Weather ──

    async def _get_current_weather(self, farm_id: int) -> Dict:
        farm = self.db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            return {"error": f"Farm {farm_id} not found"}
        if not self.weather_service:
            return {"error": "Weather service not available"}
        try:
            return await self.weather_service.get_current_weather(farm.location)
        except Exception as e:
            return {"error": f"Weather temporarily unavailable: {str(e)}"}

    async def _get_weather_forecast(self, farm_id: int, days: int = 5) -> Dict:
        farm = self.db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            return {"error": f"Farm {farm_id} not found"}
        if not self.weather_service:
            return {"error": "Weather service not available"}
        try:
            return await self.weather_service.get_forecast(farm.location, days)
        except Exception as e:
            return {"error": f"Forecast temporarily unavailable: {str(e)}"}

    # ── Irrigation ──

    async def _calculate_irrigation(self, farm_id: int, crop_id: Optional[int] = None) -> Dict:
        farm = self.db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            return {"error": f"Farm {farm_id} not found"}

        soil = farm.soil_profile
        soil_type = soil.soil_type.value if soil else "loamy"

        # Get first active crop if crop_id not specified
        crop = None
        if crop_id:
            crop = self.db.query(Crop).filter(Crop.id == crop_id).first()
        else:
            for field in farm.fields:
                for c in field.crops:
                    if c.status.value == "active":
                        crop = c
                        break
                if crop:
                    break

        if not crop:
            return {"error": "No active crop found on farm"}

        # Get catalog data for water requirement
        water_req = 5.0  # default mm/day
        if crop.catalog:
            water_req = crop.catalog.water_requirement_mm_per_day

        # Last irrigation
        last_irr = (
            self.db.query(IrrigationRecord)
            .filter(IrrigationRecord.farm_id == farm_id, IrrigationRecord.completed == True)
            .order_by(IrrigationRecord.actual_date.desc())
            .first()
        )
        last_irr_date = last_irr.actual_date if last_irr else None

        # Get weather
        current_weather = {}
        forecast_days = []
        if self.weather_service:
            try:
                current_weather = await self.weather_service.get_current_weather(farm.location)
                forecast = await self.weather_service.get_forecast(farm.location, 3)
                forecast_days = forecast.get("days", [])
            except Exception:
                pass

        return irrigation_engine.calculate(
            crop_name=crop.crop_name,
            crop_stage=crop.current_stage.value if crop.current_stage else "vegetative",
            area_acres=crop.area_acres,
            soil_type=soil_type,
            irrigation_method=farm.irrigation_method.value if farm.irrigation_method else "flood",
            water_requirement_mm_per_day=water_req,
            forecast_days=forecast_days,
            current_weather=current_weather,
            last_irrigation_date=last_irr_date,
        )

    # ── Crop Recommendations ──

    async def _get_crop_recommendations(self, farm_id: int) -> Dict:
        farm = self.db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            return {"error": f"Farm {farm_id} not found"}

        soil = farm.soil_profile
        soil_type = soil.soil_type.value if soil else "loamy"

        current_weather = {}
        if self.weather_service:
            try:
                current_weather = await self.weather_service.get_current_weather(farm.location)
            except Exception:
                pass

        temp = current_weather.get("temperature_c", 25)
        rain = current_weather.get("rainfall_mm", 0)

        return crop_recommendation_engine.recommend(
            location=farm.location,
            soil_type=soil_type,
            temperature_c=temp,
            rainfall_mm=rain * 30,  # rough monthly estimate from current
            water_availability="medium",
        )

    # ── Crop Calendar ──

    def _get_crop_calendar(self, crop_id: int, farm_id: int) -> Dict:
        crop = self.db.query(Crop).filter(Crop.id == crop_id).first()
        if not crop:
            return {"error": f"Crop {crop_id} not found"}
        if not crop.sowing_date:
            return {"error": "Sowing date not set for this crop"}

        return crop_calendar_service.generate_calendar(
            crop.crop_name, crop.sowing_date,
            field_name=crop.field.name if crop.field else "Field",
            area_acres=crop.area_acres
        )

    # ── Risk Analysis ──

    async def _get_risk_analysis(self, farm_id: int) -> Dict:
        farm = self.db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            return {"error": f"Farm {farm_id} not found"}

        current_weather = {}
        forecast_days = []
        if self.weather_service:
            try:
                current_weather = await self.weather_service.get_current_weather(farm.location)
                forecast = await self.weather_service.get_forecast(farm.location, 5)
                forecast_days = forecast.get("days", [])
            except Exception as e:
                current_weather = {}

        active_crops = []
        for field in farm.fields:
            for c in field.crops:
                if c.status.value == "active":
                    active_crops.append({
                        "crop_name": c.crop_name,
                        "current_stage": c.current_stage.value if c.current_stage else "vegetative",
                        "area_acres": c.area_acres,
                    })

        return risk_engine.analyse(
            farm_id=farm_id,
            location=farm.location,
            current_weather=current_weather,
            forecast_days=forecast_days,
            active_crops=active_crops,
        )

    # ── Action Plan ──

    async def _get_action_plan(self, farm_id: int) -> Dict:
        farm = self.db.query(Farm).filter(Farm.id == farm_id).first()
        if not farm:
            return {"error": f"Farm {farm_id} not found"}

        # Gather all inputs
        active_crops_data = []
        for field in farm.fields:
            for c in field.crops:
                if c.status.value == "active":
                    active_crops_data.append({
                        "crop_name": c.crop_name,
                        "current_stage": c.current_stage.value if c.current_stage else "vegetative",
                        "area_acres": c.area_acres,
                    })

        current_weather = {}
        forecast_days = []
        if self.weather_service:
            try:
                current_weather = await self.weather_service.get_current_weather(farm.location)
                forecast = await self.weather_service.get_forecast(farm.location, 7)
                forecast_days = forecast.get("days", [])
            except Exception:
                pass

        irr_rec = await self._calculate_irrigation(farm_id)
        risk = risk_engine.analyse(
            farm_id=farm_id, location=farm.location,
            current_weather=current_weather, forecast_days=forecast_days,
            active_crops=active_crops_data
        )

        pending_tasks = (
            self.db.query(FarmTask)
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
            active_crops=active_crops_data,
            irrigation_recommendation=irr_rec,
            weather_forecast=forecast_days,
            current_weather=current_weather,
            risk_analysis=risk,
            pending_tasks=tasks_data,
        )

    # ── Mandi Prices ──

    async def _get_mandi_prices(self, crop_name: str, location: str) -> Dict:
        if self.market_service:
            try:
                return await self.market_service.get_prices(crop_name, location)
            except Exception as e:
                return {
                    "available": False,
                    "error": f"Market data temporarily unavailable: {str(e)}",
                    "note": "Please check data.gov.in or agmarknet.gov.in for current prices."
                }
        return {
            "available": False,
            "note": "Market data service not configured. Check agmarknet.gov.in for live prices.",
            "crop_name": crop_name,
            "location": location,
        }
