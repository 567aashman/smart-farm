"""
SmartFarm AI - Risk Engine (Phase 7)
Detects weather and crop/environment risks.

IMPORTANT: We do NOT diagnose diseases from weather alone.
We identify "conditions favorable for" risk, not confirmed disease.
"""
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class RiskEngine:
    """
    Analyses current weather + forecast + crop stage to identify risks.
    Returns risk alerts with level and recommended action.
    """

    def analyse(
        self,
        farm_id: int,
        location: str,
        current_weather: Dict[str, Any],
        forecast_days: List[Dict[str, Any]],
        active_crops: List[Dict[str, Any]],  # list of {name, stage, area_acres}
    ) -> Dict[str, Any]:
        """
        Run risk analysis. Returns risk analysis response dict.
        """
        risks = []
        crop_names = [c.get("crop_name", "crop") for c in active_crops]
        crop_stages = {c.get("crop_name", "crop"): c.get("current_stage", "vegetative") for c in active_crops}

        temp = current_weather.get("temperature_c", 25)
        humidity = current_weather.get("humidity_percent", 50)
        rain_mm = current_weather.get("rainfall_mm", 0)
        wind_kmh = current_weather.get("wind_speed_kmh", 0)

        next_day_rain = forecast_days[0].get("rainfall_mm", 0) if forecast_days else 0
        next_day_pop = forecast_days[0].get("rain_probability", 0) if forecast_days else 0
        total_3day_rain = sum(d.get("rainfall_mm", 0) for d in forecast_days[:3])

        # ── Risk 1: Heavy Rain / Flood Risk ──
        if next_day_rain >= 40 or total_3day_rain >= 80:
            risks.append({
                "risk_type": "heavy_rain",
                "title": "Heavy Rainfall Alert",
                "description": f"Heavy rain expected: {next_day_rain:.0f}mm tomorrow, {total_3day_rain:.0f}mm over 3 days.",
                "level": "high" if next_day_rain >= 60 else "medium",
                "recommended_action": "Skip irrigation. Ensure field drainage. Protect harvested produce.",
                "affected_crops": crop_names,
            })

        # ── Risk 2: Heat Stress ──
        if temp >= 40:
            risks.append({
                "risk_type": "heat_stress",
                "title": "Extreme Heat Stress",
                "description": f"Temperature is {temp}°C — above crop tolerance for most varieties.",
                "level": "high" if temp >= 44 else "medium",
                "recommended_action": "Increase irrigation frequency. Apply mulch. Avoid daytime spraying.",
                "affected_crops": [c for c in crop_names if crop_stages.get(c) in ["flowering", "maturity"]],
            })
        elif temp >= 35:
            risks.append({
                "risk_type": "heat_stress",
                "title": "Heat Stress Warning",
                "description": f"Temperature {temp}°C is above optimal for many crops.",
                "level": "low",
                "recommended_action": "Monitor crops closely. Irrigate during cooler hours (early morning).",
                "affected_crops": crop_names,
            })

        # ── Risk 3: High Wind ──
        if wind_kmh >= 50:
            risks.append({
                "risk_type": "high_wind",
                "title": "High Wind Warning",
                "description": f"Wind speed is {wind_kmh:.0f} km/h — risk of crop lodging.",
                "level": "high" if wind_kmh >= 70 else "medium",
                "recommended_action": "Avoid spraying. Stake tall crops. Check for lodging in wheat/maize.",
                "affected_crops": crop_names,
            })

        # ── Risk 4: Dry Spell ──
        total_5day_rain = sum(d.get("rainfall_mm", 0) for d in forecast_days[:5])
        if total_5day_rain < 5 and rain_mm < 2:
            risks.append({
                "risk_type": "dry_spell",
                "title": "Dry Spell Warning",
                "description": f"Less than 5mm rainfall expected in 5 days. Current rainfall: {rain_mm}mm.",
                "level": "medium",
                "recommended_action": "Ensure irrigation is scheduled. Monitor soil moisture. Prioritize flowering-stage crops.",
                "affected_crops": crop_names,
            })

        # ── Risk 5: High Humidity + Rain → Fungal Risk ──
        if humidity >= 80 and rain_mm > 5:
            affected = [c for c in crop_names if crop_stages.get(c) in ["vegetative", "flowering"]]
            if affected:
                risks.append({
                    "risk_type": "fungal_risk",
                    "title": "Conditions Favorable for Fungal Disease",
                    "description": (
                        f"High humidity ({humidity}%) combined with rainfall ({rain_mm}mm) creates favorable "
                        "conditions for fungal diseases such as blight, rust, and powdery mildew."
                    ),
                    "level": "medium",
                    "recommended_action": (
                        "Inspect crops for early signs of fungal infection. "
                        "Consider preventive fungicide application if symptoms appear. "
                        "Do NOT diagnose from weather alone — inspect plants."
                    ),
                    "affected_crops": affected,
                })

        # ── Risk 6: Low Temperature / Frost Risk ──
        if temp <= 5:
            risks.append({
                "risk_type": "frost_risk",
                "title": "Frost/Cold Stress Risk",
                "description": f"Temperature is {temp}°C — risk of frost damage to crops.",
                "level": "critical" if temp <= 2 else "high",
                "recommended_action": "Apply light irrigation before night (ice blanket effect). Cover nursery seedlings.",
                "affected_crops": crop_names,
            })

        # ── Risk 7: Excess Moisture / Waterlogging ──
        if rain_mm >= 25 and next_day_rain >= 15:
            risks.append({
                "risk_type": "waterlogging",
                "title": "Waterlogging Risk",
                "description": f"Recent heavy rain ({rain_mm}mm) and more forecast ({next_day_rain}mm). Risk of waterlogging.",
                "level": "medium",
                "recommended_action": "Open drainage channels. Skip irrigation completely. Inspect roots for rot signs.",
                "affected_crops": crop_names,
            })

        # ── Risk 8: Monsoon tracking ──
        monsoon_status = self._detect_monsoon_status(current_weather, forecast_days)
        if monsoon_status:
            risks.append(monsoon_status)

        # ── Overall risk level ──
        if any(r["level"] == "critical" for r in risks):
            overall = "critical"
        elif any(r["level"] == "high" for r in risks):
            overall = "high"
        elif any(r["level"] == "medium" for r in risks):
            overall = "medium"
        elif risks:
            overall = "low"
        else:
            overall = "none"

        return {
            "farm_id": farm_id,
            "location": location,
            "risks": risks,
            "overall_risk_level": overall,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _detect_monsoon_status(
        self, current: Dict, forecast: List[Dict]
    ) -> Optional[Dict]:
        """
        Simple monsoon detection for Indian subcontinent.
        Based on month + rainfall patterns.
        """
        month = datetime.now().month
        total_rain = sum(d.get("rainfall_mm", 0) for d in forecast[:5])
        current_rain = current.get("rainfall_mm", 0)

        # Monsoon season: June–September
        if month in [6, 7, 8, 9]:
            if total_rain >= 100:
                return {
                    "risk_type": "monsoon_active",
                    "title": "Active Monsoon Detected",
                    "description": f"Active monsoon conditions. {total_rain:.0f}mm rainfall expected in 5 days.",
                    "level": "medium",
                    "recommended_action": "Reduce irrigation. Monitor drainage. Choose waterlogging-tolerant varieties.",
                    "affected_crops": [],
                }
            elif total_rain >= 30:
                return {
                    "risk_type": "monsoon_moderate",
                    "title": "Monsoon Activity",
                    "description": f"Moderate monsoon rainfall expected ({total_rain:.0f}mm in 5 days).",
                    "level": "low",
                    "recommended_action": "Adjust irrigation schedule. Use rainfall efficiently.",
                    "affected_crops": [],
                }
        elif month in [10, 11]:
            if total_rain > 20:
                return {
                    "risk_type": "monsoon_retreating",
                    "title": "Retreating Monsoon",
                    "description": f"Retreating monsoon activity with {total_rain:.0f}mm expected. Heavy localized rain possible.",
                    "level": "low",
                    "recommended_action": "Be prepared for sudden heavy rain. Check drainage channels.",
                    "affected_crops": [],
                }
        return None


# Module-level singleton
risk_engine = RiskEngine()
