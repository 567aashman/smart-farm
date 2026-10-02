"""
SmartFarm - Crop Recommendation Engine (Phase 5)
Matches crop suitability to location, season, soil, and weather.
Every recommendation includes a detailed explanation.
"""
import json
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Season detection by month (India-centric)
KHARIF_MONTHS = [6, 7, 8, 9, 10]       # June–October (monsoon)
RABI_MONTHS = [11, 12, 1, 2, 3]        # November–March (winter)
ZAID_MONTHS = [3, 4, 5]                # March–May (summer)

SOIL_COMPATIBILITY = {
    "wheat":     ["loamy", "clay_loam", "sandy_loam"],
    "rice":      ["clay", "clay_loam"],
    "maize":     ["loamy", "sandy_loam", "clay_loam"],
    "mustard":   ["loamy", "sandy_loam"],
    "potato":    ["sandy_loam", "loamy"],
    "tomato":    ["loamy", "sandy_loam", "clay_loam"],
    "cotton":    ["clay", "clay_loam"],
    "sugarcane": ["loamy", "clay_loam"],
    "chickpea":  ["sandy_loam", "loamy"],
    "soybean":   ["loamy", "clay_loam"],
}

DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "crops", "crops.json"
)


class CropRecommendationEngine:
    """
    Recommends crops based on season, temperature, rainfall, and soil.
    Returns suitability scores and human-readable reasons.
    """

    def __init__(self):
        self._catalog: Optional[List[Dict]] = None

    def _load_catalog(self) -> List[Dict]:
        if self._catalog is None:
            try:
                with open(DATA_PATH, "r") as f:
                    self._catalog = json.load(f)
            except FileNotFoundError:
                logger.error(f"Crop catalog not found at {DATA_PATH}")
                self._catalog = []
            except Exception as e:
                logger.error(f"Failed to load crop catalog: {e}")
                self._catalog = []
        return self._catalog

    def get_current_season(self, month: Optional[int] = None) -> str:
        m = month or datetime.now().month
        if m in KHARIF_MONTHS:
            return "kharif"
        elif m in RABI_MONTHS:
            return "rabi"
        else:
            return "zaid"

    def recommend(
        self,
        location: str,
        soil_type: str,
        temperature_c: float,
        rainfall_mm: float,          # Annual or recent seasonal rainfall
        month: Optional[int] = None,
        water_availability: str = "medium",  # low / medium / high
    ) -> Dict[str, Any]:
        """
        Generate crop recommendations.

        Returns dict with recommendations list sorted by suitability score.
        """
        catalog = self._load_catalog()
        current_month = month or datetime.now().month
        season = self.get_current_season(current_month)

        recommendations = []

        for crop in catalog:
            score, reasons, flags = self._score_crop(
                crop, season, soil_type, temperature_c, rainfall_mm, water_availability, current_month
            )

            suitability = self._score_to_label(score)

            recommendations.append({
                "crop_name": crop["crop_name"],
                "local_name": crop.get("local_name"),
                "season": crop["season"],
                "suitability": suitability,
                "suitability_score": round(score, 1),
                "reasons": reasons,
                "soil_match": flags["soil_match"],
                "temp_match": flags["temp_match"],
                "rainfall_match": flags["rainfall_match"],
                "sowing_window": self._sowing_window_text(crop),
                "growth_duration_days": crop["growth_duration_days"],
            })

        # Sort: highest score first
        recommendations.sort(key=lambda x: x["suitability_score"], reverse=True)

        return {
            "location": location,
            "season": season,
            "current_month": current_month,
            "recommendations": recommendations,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def _score_crop(
        self, crop: Dict, season: str, soil_type: str, temp_c: float,
        rainfall_mm: float, water_availability: str, current_month: int
    ):
        """Score a crop 0–100 based on match quality."""
        score = 0.0
        reasons = []
        flags = {"soil_match": False, "temp_match": False, "rainfall_match": False}

        # ── Season Match (30 points) ──
        crop_season = crop.get("season", "")
        if crop_season == season:
            score += 30
            reasons.append(f"Ideal for {season} season (June–October)" if season == "kharif"
                           else f"Ideal for {season} season (Nov–March)" if season == "rabi"
                           else f"Suitable for {season} season")
        elif crop_season == "perennial":
            score += 15
            reasons.append("Perennial crop, can be sown across seasons")
        else:
            score -= 10
            reasons.append(f"Off-season crop — primarily a {crop_season} crop. Sowing now is risky.")

        # ── Temperature Match (25 points) ──
        t_min = crop.get("temperature_min_c", 0)
        t_max = crop.get("temperature_max_c", 50)
        if t_min <= temp_c <= t_max:
            score += 25
            flags["temp_match"] = True
            reasons.append(f"Temperature {temp_c}°C is within optimal range ({t_min}–{t_max}°C)")
        elif temp_c < t_min:
            diff = t_min - temp_c
            score += max(0, 25 - diff * 3)
            reasons.append(f"Temperature {temp_c}°C is slightly below optimal minimum ({t_min}°C)")
        else:
            diff = temp_c - t_max
            score += max(0, 25 - diff * 3)
            reasons.append(f"Temperature {temp_c}°C is above optimal maximum ({t_max}°C)")

        # ── Rainfall / Water Match (25 points) ──
        req = crop.get("rainfall_requirement_mm", 500)
        # Scale annual requirement to seasonal rainfall estimate
        seasonal_equiv = rainfall_mm
        ratio = seasonal_equiv / max(req, 1)
        if 0.7 <= ratio <= 1.5:
            score += 25
            flags["rainfall_match"] = True
            reasons.append(f"Rainfall requirements match ({req}mm needed, {rainfall_mm:.0f}mm available)")
        elif ratio < 0.7:
            pts = max(0, 25 * ratio / 0.7)
            score += pts
            reasons.append(f"Lower rainfall available ({rainfall_mm:.0f}mm) than ideal ({req}mm). Irrigation needed.")
        else:
            score += 15
            reasons.append(f"High rainfall may require drainage management (req: {req}mm)")

        # Water availability override
        water_req_day = crop.get("water_requirement_mm_per_day", 5)
        if water_availability == "low" and water_req_day > 6:
            score -= 15
            reasons.append(f"Water availability is low but {crop['crop_name']} requires {water_req_day}mm/day")
        elif water_availability == "high" and water_req_day > 5:
            score += 5
            reasons.append("Sufficient water availability for this crop")

        # ── Soil Match (20 points) ──
        compatible_soils = SOIL_COMPATIBILITY.get(crop["crop_name"].lower(), [])
        if soil_type.lower() in compatible_soils:
            score += 20
            flags["soil_match"] = True
            reasons.append(f"{soil_type.replace('_', ' ').title()} soil is ideal for {crop['crop_name']}")
        else:
            score += 5
            reasons.append(f"Soil type '{soil_type}' is not the most ideal for {crop['crop_name']}")

        # ── Sowing Window (bonus) ──
        sw_start = crop.get("sowing_window_start")
        sw_end = crop.get("sowing_window_end")
        if sw_start and sw_end:
            in_window = self._in_sowing_window(current_month, sw_start, sw_end)
            if in_window:
                score += 10
                reasons.append("Currently in the optimal sowing window")
            else:
                score -= 5
                reasons.append(f"Optimal sowing window is {sw_start} to {sw_end}")

        return min(100, max(0, score)), reasons, flags

    def _in_sowing_window(self, month: int, start: str, end: str) -> bool:
        try:
            start_m = int(start.split("-")[0])
            end_m = int(end.split("-")[0])
            if start_m <= end_m:
                return start_m <= month <= end_m
            else:  # wraps around year (e.g. Nov–Feb)
                return month >= start_m or month <= end_m
        except Exception:
            return False

    def _score_to_label(self, score: float) -> str:
        if score >= 75:
            return "highly_suitable"
        elif score >= 55:
            return "suitable"
        elif score >= 30:
            return "moderate"
        else:
            return "not_suitable"

    def _sowing_window_text(self, crop: Dict) -> Optional[str]:
        s = crop.get("sowing_window_start")
        e = crop.get("sowing_window_end")
        if s and e:
            MONTHS = {
                "01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr",
                "05": "May", "06": "Jun", "07": "Jul", "08": "Aug",
                "09": "Sep", "10": "Oct", "11": "Nov", "12": "Dec",
            }
            sm = MONTHS.get(s.split("-")[0], s)
            em = MONTHS.get(e.split("-")[0], e)
            return f"{sm} – {em}"
        return None


# Module-level singleton
crop_recommendation_engine = CropRecommendationEngine()
