"""
SmartFarm - Irrigation Engine (Phase 4)
Rule-based agricultural irrigation recommendations.

The LLM does NOT calculate irrigation values.
This engine uses transparent agricultural rules.

Key rules:
1. Skip if heavy rain expected (>15mm in next 24h)
2. Postpone if moderate rain expected (5-15mm)
3. Recommend if crop water demand > available moisture
4. Adjust for crop stage, soil type, and weather
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# SOIL WATER HOLDING CAPACITY (mm per 10cm depth)
# ─────────────────────────────────────────────
SOIL_WHC = {
    "sandy":     0.5,   # drains very fast
    "sandy_loam": 1.2,
    "loamy":     1.8,
    "clay_loam": 2.2,
    "clay":      2.5,   # holds most water
    "silty":     2.0,
    "peaty":     2.8,
    "chalky":    1.0,
}

# ─────────────────────────────────────────────
# CROP STAGE WATER DEMAND MULTIPLIERS (Kc values)
# ─────────────────────────────────────────────
STAGE_KC = {
    "land_preparation": 0.4,
    "sowing":           0.5,
    "germination":      0.7,
    "vegetative":       1.0,
    "flowering":        1.2,  # peak demand
    "maturity":         0.8,
    "harvest":          0.4,
}

# ─────────────────────────────────────────────
# IRRIGATION METHOD EFFICIENCY
# ─────────────────────────────────────────────
METHOD_EFFICIENCY = {
    "drip":      0.90,
    "sprinkler": 0.75,
    "furrow":    0.60,
    "flood":     0.50,
    "rainfed":   1.00,  # no irrigation
}

# Rainfall thresholds (mm)
RAIN_SKIP_THRESHOLD = 15.0      # skip irrigation: heavy rain
RAIN_POSTPONE_THRESHOLD = 5.0   # postpone: moderate rain
RAIN_COUNT_DAYS = 1             # look ahead days for rainfall decision


class IrrigationEngine:
    """
    Computes irrigation recommendations from agricultural rules.
    Inputs: crop data, weather data, soil profile.
    Output: IrrigationRecommendation dict.
    """

    def calculate(
        self,
        crop_name: str,
        crop_stage: str,
        area_acres: float,
        soil_type: str,
        irrigation_method: str,
        water_requirement_mm_per_day: float,
        forecast_days: List[Dict[str, Any]],
        current_weather: Dict[str, Any],
        last_irrigation_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point. Returns recommendation dict.

        Args:
            crop_name: e.g. "Wheat"
            crop_stage: e.g. "vegetative"
            area_acres: field area
            soil_type: e.g. "loamy"
            irrigation_method: e.g. "drip"
            water_requirement_mm_per_day: base from crop catalog
            forecast_days: list of forecast dicts with rainfall_mm, rain_probability
            current_weather: current weather dict
            last_irrigation_date: date of last irrigation

        Returns:
            dict matching IrrigationRecommendation schema
        """
        logger.info(f"Calculating irrigation for {crop_name} ({crop_stage}), soil={soil_type}")

        # ─── Step 1: Get next-day rainfall forecast ───
        next_day_rain = 0.0
        next_day_pop = 0.0
        if forecast_days:
            next_day_rain = forecast_days[0].get("rainfall_mm", 0.0)
            next_day_pop = forecast_days[0].get("rain_probability", 0.0)

        current_rain = current_weather.get("rainfall_mm", 0.0)
        temp = current_weather.get("temperature_c", 25.0)
        humidity = current_weather.get("humidity_percent", 50.0)

        # ─── Step 2: Calculate actual crop water demand ───
        kc = STAGE_KC.get(crop_stage, 1.0)
        eto = self._calc_eto(temp, humidity)            # Reference ET (Penman-simplified)
        etc = round(eto * kc, 2)                        # Crop ET = ETo × Kc (mm/day)
        # Blend with catalog value, giving 60% weight to calculated ET
        effective_demand = round(0.6 * etc + 0.4 * water_requirement_mm_per_day, 2)

        # ─── Step 3: Days since last irrigation ───
        days_since_irrigated = None
        if last_irrigation_date:
            days_since_irrigated = (date.today() - last_irrigation_date).days

        # ─── Step 4: Soil depletion estimate ───
        whc = SOIL_WHC.get(soil_type, 1.8)
        # Effective root zone depth assumed 30cm = 3 × 10cm
        soil_storage_mm = whc * 30
        # Rough depletion estimate (days × demand - recent rain)
        recent_rain = current_rain + next_day_rain * 0.5
        depletion_mm = 0.0
        if days_since_irrigated is not None:
            depletion_mm = max(0, days_since_irrigated * effective_demand - recent_rain)
        else:
            depletion_mm = soil_storage_mm * 0.5  # assume 50% depleted if unknown

        # ─── Step 5: Irrigation decision rules ───
        reasons = []
        irrigation_required = False
        recommended_date = (date.today() + timedelta(days=1)).isoformat()
        recommended_time = "06:00"
        confidence = "medium"
        skip_reason = None
        weather_factor = None

        # Rule A: Heavy rain expected → skip
        if next_day_rain >= RAIN_SKIP_THRESHOLD or (next_day_pop >= 80 and next_day_rain >= 8):
            irrigation_required = False
            skip_reason = f"Heavy rainfall expected tomorrow ({next_day_rain:.0f}mm, {next_day_pop:.0f}% probability)"
            reasons.append(skip_reason)
            weather_factor = "rain_skip"
            confidence = "high"

        # Rule B: Moderate rain → postpone by 1 day
        elif next_day_rain >= RAIN_POSTPONE_THRESHOLD or next_day_pop >= 60:
            irrigation_required = False
            skip_reason = f"Moderate rain expected ({next_day_rain:.0f}mm). Consider irrigating in 2 days."
            recommended_date = (date.today() + timedelta(days=2)).isoformat()
            reasons.append(f"Rainfall of {next_day_rain:.0f}mm expected tomorrow.")
            reasons.append("Irrigation postponed to avoid waterlogging.")
            weather_factor = "rain_postpone"
            confidence = "medium"

        # Rule C: Soil significantly depleted → irrigate
        elif depletion_mm >= (soil_storage_mm * 0.5):
            irrigation_required = True
            reasons.append(f"Estimated soil moisture depletion: {depletion_mm:.0f}mm")
            reasons.append(f"Crop ({crop_name}) in {crop_stage} stage requires ~{effective_demand:.1f}mm/day")
            if days_since_irrigated is not None:
                reasons.append(f"Last irrigation was {days_since_irrigated} days ago")
            confidence = "high" if depletion_mm >= soil_storage_mm * 0.7 else "medium"

        # Rule D: High temperature + low humidity → irrigate
        elif temp >= 35 and humidity < 40:
            irrigation_required = True
            reasons.append(f"High temperature ({temp}°C) and low humidity ({humidity}%) increasing water demand")
            reasons.append(f"Crop ET estimated at {etc:.1f}mm/day")
            confidence = "medium"
            weather_factor = "heat_stress"

        # Rule E: Crop at peak demand stage (flowering)
        elif crop_stage == "flowering" and days_since_irrigated and days_since_irrigated >= 3:
            irrigation_required = True
            reasons.append(f"Wheat is in flowering stage — highest water demand period (Kc={kc})")
            reasons.append(f"It has been {days_since_irrigated} days since last irrigation")
            confidence = "high"

        # Rule F: Normal conditions, check standard interval
        else:
            # Standard irrigation interval by soil type
            soil_interval = {"sandy": 3, "sandy_loam": 5, "loamy": 7, "clay_loam": 8, "clay": 10}
            interval = soil_interval.get(soil_type, 7)
            if days_since_irrigated is not None and days_since_irrigated >= interval:
                irrigation_required = True
                reasons.append(f"Standard irrigation interval reached ({days_since_irrigated} of {interval} days for {soil_type} soil)")
                confidence = "medium"
            else:
                irrigation_required = False
                remaining = (interval - (days_since_irrigated or 0)) if days_since_irrigated else interval
                skip_reason = f"No irrigation needed. Next expected in ~{remaining} day(s)."
                reasons.append(skip_reason)
                confidence = "medium"

        # ─── Step 6: Calculate how much water is needed ───
        requirement_mm = None
        duration_hours = None
        if irrigation_required:
            # Net irrigation = depletion adjusted for method efficiency
            efficiency = METHOD_EFFICIENCY.get(irrigation_method, 0.60)
            gross_req = round(max(depletion_mm, effective_demand * 2), 1)
            requirement_mm = round(gross_req / efficiency, 1)
            # Duration estimate: 1mm/hour for flood, 2mm/hour for drip
            flow_mm_per_hour = {"drip": 2.0, "sprinkler": 1.5, "furrow": 1.2, "flood": 1.0}.get(irrigation_method, 1.0)
            duration_hours = round(requirement_mm / flow_mm_per_hour, 1)

        return {
            "irrigation_required": irrigation_required,
            "recommended_date": recommended_date if irrigation_required else None,
            "recommended_time": recommended_time,
            "estimated_requirement_mm": requirement_mm,
            "duration_hours": duration_hours,
            "reason": " ".join(reasons) if reasons else "Irrigation assessment complete.",
            "confidence": confidence,
            "skip_reason": skip_reason,
            "weather_factor": weather_factor,
            # Extra context for FarmAI tool
            "_debug": {
                "eto_mm_day": eto,
                "etc_mm_day": etc,
                "kc": kc,
                "effective_demand_mm": effective_demand,
                "next_day_rain_mm": next_day_rain,
                "depletion_mm": depletion_mm,
                "soil_storage_mm": soil_storage_mm,
            }
        }

    def _calc_eto(self, temp_c: float, humidity: float) -> float:
        """
        Simplified Hargreaves ETo approximation.
        Full Penman-Monteith requires radiation data not in free weather APIs.
        ETo (mm/day) ≈ 0.0023 × (T_mean + 17.8) × (T_max - T_min)^0.5 × Ra
        We use a simplified version with temp and humidity adjustment.
        """
        # Vapour pressure deficit adjustment
        vpd_factor = 1 + max(0, (temp_c - 25) * 0.05)
        humidity_factor = max(0.6, (100 - humidity) / 100)
        eto = round(temp_c * 0.15 * vpd_factor * (1 + humidity_factor * 0.3), 2)
        return max(1.0, min(eto, 12.0))  # clamp to realistic range


# Module-level singleton
irrigation_engine = IrrigationEngine()
