"""
SmartFarm - Action Plan Engine (Phase 8)
Combines weather + irrigation + crop calendar + risk into a 7-day action plan.
"""
import logging
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

PRIORITY_ICONS = {1: "🔴", 2: "🟡", 3: "🟢"}
CATEGORY_ICONS = {
    "irrigation": "💧",
    "weather":    "🌤️",
    "crop":       "🌱",
    "risk":       "⚠️",
    "general":    "📋",
    "harvest":    "🚜",
    "market":     "💰",
}


class ActionPlanEngine:
    """
    Generates the 7-day farm action plan by combining all engines.
    """

    def generate(
        self,
        farm_id: int,
        farm_name: str,
        active_crops: List[Dict],       # [{crop_name, current_stage, area_acres, sowing_date}]
        irrigation_recommendation: Dict,
        weather_forecast: List[Dict],   # 7-day forecast
        current_weather: Dict,
        risk_analysis: Dict,
        pending_tasks: List[Dict],      # upcoming FarmTasks
    ) -> Dict[str, Any]:
        """Generate a 7-day action plan."""

        today = date.today()
        days = []

        for i in range(7):
            target_date = today + timedelta(days=i)
            day_forecast = weather_forecast[i] if i < len(weather_forecast) else {}

            label = "TODAY" if i == 0 else "TOMORROW" if i == 1 else f"Day {i + 1}"
            actions = []

            # ── Weather actions ──
            rain_mm = day_forecast.get("rainfall_mm", 0)
            rain_prob = day_forecast.get("rain_probability", 0)
            temp_max = day_forecast.get("temp_max_c", 25)
            description = day_forecast.get("description", "")

            if rain_mm >= 20 or rain_prob >= 80:
                actions.append({
                    "icon": "🌧️",
                    "title": f"Heavy Rain Expected ({rain_mm:.0f}mm)",
                    "description": f"Heavy rainfall expected ({rain_prob:.0f}% probability). Skip irrigation and ensure drainage.",
                    "priority": 1,
                    "category": "weather",
                })
            elif rain_mm >= 5:
                actions.append({
                    "icon": "🌦️",
                    "title": f"Light Rain Expected ({rain_mm:.0f}mm)",
                    "description": f"Light rain may reduce irrigation need. Monitor field moisture.",
                    "priority": 2,
                    "category": "weather",
                })

            if temp_max >= 38:
                actions.append({
                    "icon": "🌡️",
                    "title": f"Heat Alert ({temp_max}°C)",
                    "description": "High temperature expected. Irrigate during morning hours only.",
                    "priority": 1,
                    "category": "weather",
                })

            # ── Irrigation actions ──
            if i == 0:
                if irrigation_recommendation.get("irrigation_required"):
                    req_mm = irrigation_recommendation.get("estimated_requirement_mm", 0)
                    rec_time = irrigation_recommendation.get("recommended_time", "06:00")
                    actions.append({
                        "icon": "💧",
                        "title": f"Irrigate Fields ({req_mm:.0f}mm recommended)",
                        "description": f"Best time: {rec_time}. {irrigation_recommendation.get('reason', '')}",
                        "priority": 1,
                        "category": "irrigation",
                    })
                else:
                    skip = irrigation_recommendation.get("skip_reason", "No irrigation required today.")
                    actions.append({
                        "icon": "✅",
                        "title": "No Irrigation Required",
                        "description": skip,
                        "priority": 3,
                        "category": "irrigation",
                    })

            # ── Crop-specific actions ──
            for crop in active_crops:
                stage = crop.get("current_stage", "vegetative")
                name = crop.get("crop_name", "Crop")

                if i == 0:
                    if stage == "flowering":
                        actions.append({
                            "icon": "🌸",
                            "title": f"Monitor {name} — Flowering Stage",
                            "description": "Critical stage. Check for pollination, avoid pesticide application.",
                            "priority": 1,
                            "category": "crop",
                        })
                    elif stage == "germination":
                        actions.append({
                            "icon": "🌿",
                            "title": f"Check {name} Germination",
                            "description": "Count seedlings. Ensure soil stays moist but not waterlogged.",
                            "priority": 2,
                            "category": "crop",
                        })
                    else:
                        actions.append({
                            "icon": "🔍",
                            "title": f"Inspect {name} ({stage.replace('_', ' ').title()})",
                            "description": f"Check plant health, pest signs, and growth progress.",
                            "priority": 3,
                            "category": "crop",
                        })

            # ── Risk actions ──
            if i == 0:
                for risk in risk_analysis.get("risks", []):
                    if risk["level"] in ["high", "critical"]:
                        actions.append({
                            "icon": "⚠️",
                            "title": f"RISK: {risk['title']}",
                            "description": risk["recommended_action"],
                            "priority": 1,
                            "category": "risk",
                        })

            # ── Pending tasks for this day ──
            for task in pending_tasks:
                due = task.get("due_date")
                if due == target_date.isoformat():
                    actions.append({
                        "icon": "📋",
                        "title": task["title"],
                        "description": task.get("description", ""),
                        "priority": task.get("priority", 2),
                        "category": "general",
                    })

            # Sort actions by priority
            actions.sort(key=lambda a: a["priority"])

            # Weather summary for the day
            weather_summary = self._weather_summary(day_forecast)

            days.append({
                "date": target_date.isoformat(),
                "day_label": label,
                "weather_summary": weather_summary,
                "actions": actions,
                "irrigation_needed": (
                    irrigation_recommendation.get("irrigation_required") and i == 0
                ) or (
                    rain_mm < 3 and i > 0 and (i % 3 == 0)
                ),
            })

        return {
            "farm_id": farm_id,
            "farm_name": farm_name,
            "days": days,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _weather_summary(self, forecast: Dict) -> str:
        if not forecast:
            return "Weather data unavailable"
        desc = forecast.get("description", "")
        tmax = forecast.get("temp_max_c", "?")
        tmin = forecast.get("temp_min_c", "?")
        rain = forecast.get("rainfall_mm", 0)
        pop = forecast.get("rain_probability", 0)
        return f"{desc} | {tmin}–{tmax}°C | Rain: {rain:.0f}mm ({pop:.0f}%)"


# Module-level singleton
action_plan_engine = ActionPlanEngine()
