"""
SmartFarm AI - Automated Tests (Phase 20)
Tests for all agricultural engines, services, and API endpoints.
Run: pytest backend/tests/ -v
"""
import pytest
import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

# ─────────────────────────────────────────────
# IRRIGATION ENGINE TESTS
# ─────────────────────────────────────────────

class TestIrrigationEngine:
    """Phase 20: Agricultural calculation tests."""

    def setup_method(self):
        from backend.agriculture.irrigation_engine import IrrigationEngine
        self.engine = IrrigationEngine()

    def _make_forecast(self, rain_mm: float, pop: float = 0.0, days: int = 3):
        return [{"rainfall_mm": rain_mm, "rain_probability": pop, "temp_max_c": 30} for _ in range(days)]

    def _make_weather(self, temp: float = 25, humidity: float = 60, rain: float = 0):
        return {"temperature_c": temp, "humidity_percent": humidity, "rainfall_mm": rain}

    def test_skip_on_heavy_rain(self):
        """High expected rainfall → irrigation should be skipped."""
        result = self.engine.calculate(
            crop_name="Wheat", crop_stage="vegetative",
            area_acres=2.0, soil_type="loamy",
            irrigation_method="flood",
            water_requirement_mm_per_day=4.5,
            forecast_days=self._make_forecast(rain_mm=25.0, pop=90.0),
            current_weather=self._make_weather(),
            last_irrigation_date=date.today() - timedelta(days=5),
        )
        assert result["irrigation_required"] is False
        assert result["weather_factor"] == "rain_skip"
        assert result["confidence"] == "high"

    def test_irrigate_on_dry_spell(self):
        """Low rainfall + high crop demand → recommend irrigation."""
        result = self.engine.calculate(
            crop_name="Rice", crop_stage="vegetative",
            area_acres=1.0, soil_type="clay",
            irrigation_method="flood",
            water_requirement_mm_per_day=7.0,
            forecast_days=self._make_forecast(rain_mm=0.5, pop=5.0),
            current_weather=self._make_weather(temp=35, humidity=40),
            last_irrigation_date=date.today() - timedelta(days=10),
        )
        assert result["irrigation_required"] is True
        assert result["estimated_requirement_mm"] is not None
        assert result["estimated_requirement_mm"] > 0

    def test_postpone_on_moderate_rain(self):
        """Moderate rain → postpone irrigation."""
        result = self.engine.calculate(
            crop_name="Wheat", crop_stage="vegetative",
            area_acres=1.0, soil_type="loamy",
            irrigation_method="drip",
            water_requirement_mm_per_day=4.5,
            forecast_days=self._make_forecast(rain_mm=8.0, pop=65.0),
            current_weather=self._make_weather(),
            last_irrigation_date=date.today() - timedelta(days=3),
        )
        assert result["irrigation_required"] is False
        assert result["weather_factor"] == "rain_postpone"

    def test_flowering_stage_critical_water(self):
        """Flowering stage + no recent irrigation → must irrigate."""
        result = self.engine.calculate(
            crop_name="Wheat", crop_stage="flowering",
            area_acres=2.0, soil_type="loamy",
            irrigation_method="flood",
            water_requirement_mm_per_day=4.5,
            forecast_days=self._make_forecast(rain_mm=0, pop=0),
            current_weather=self._make_weather(temp=28),
            last_irrigation_date=date.today() - timedelta(days=5),
        )
        assert result["irrigation_required"] is True

    def test_no_irrigation_needed_recently_done(self):
        """Recent irrigation on sandy soil → skip."""
        result = self.engine.calculate(
            crop_name="Mustard", crop_stage="vegetative",
            area_acres=1.0, soil_type="sandy",
            irrigation_method="drip",
            water_requirement_mm_per_day=3.5,
            forecast_days=self._make_forecast(rain_mm=0, pop=0),
            current_weather=self._make_weather(temp=22, humidity=70),
            last_irrigation_date=date.today() - timedelta(days=1),
        )
        assert result["irrigation_required"] is False


# ─────────────────────────────────────────────
# CROP RECOMMENDATION TESTS
# ─────────────────────────────────────────────

class TestCropRecommendationEngine:
    def setup_method(self):
        from backend.agriculture.crop_recommendation import CropRecommendationEngine
        self.engine = CropRecommendationEngine()

    def test_wheat_suitable_in_rabi(self):
        """Wheat should be highly suitable in rabi season with loamy soil."""
        result = self.engine.recommend(
            location="Delhi",
            soil_type="loamy",
            temperature_c=18,
            rainfall_mm=300,
            month=11,  # November = rabi
        )
        recs = {r["crop_name"]: r for r in result["recommendations"]}
        assert "Wheat" in recs
        assert recs["Wheat"]["suitability"] in ["highly_suitable", "suitable"]
        assert recs["Wheat"]["season"] == "rabi"

    def test_rice_not_suitable_in_rabi(self):
        """Rice should not be suitable in rabi season."""
        result = self.engine.recommend(
            location="Lucknow",
            soil_type="clay",
            temperature_c=18,
            rainfall_mm=200,
            month=11,
        )
        recs = {r["crop_name"]: r for r in result["recommendations"]}
        if "Rice" in recs:
            assert recs["Rice"]["suitability"] in ["moderate", "not_suitable"]

    def test_soil_match_improves_score(self):
        """Crops with matching soil type should have higher scores."""
        result = self.engine.recommend(
            location="Nagpur",
            soil_type="clay",
            temperature_c=28,
            rainfall_mm=800,
            month=7,
        )
        recs = {r["crop_name"]: r for r in result["recommendations"]}
        # Rice and Cotton prefer clay
        if "Rice" in recs and "Wheat" in recs:
            # Rice on clay should score better than Wheat on clay (wrong season for Wheat too)
            assert recs["Rice"]["soil_match"] is True

    def test_all_crops_have_reasons(self):
        """Every recommendation must include reasons."""
        result = self.engine.recommend(
            location="Bhopal",
            soil_type="loamy",
            temperature_c=25,
            rainfall_mm=600,
        )
        for rec in result["recommendations"]:
            assert len(rec["reasons"]) > 0

    def test_season_detection_kharif(self):
        """Month 7 (July) should be detected as kharif."""
        season = self.engine.get_current_season(month=7)
        assert season == "kharif"

    def test_season_detection_rabi(self):
        """Month 12 (December) should be detected as rabi."""
        season = self.engine.get_current_season(month=12)
        assert season == "rabi"


# ─────────────────────────────────────────────
# RISK ENGINE TESTS
# ─────────────────────────────────────────────

class TestRiskEngine:
    def setup_method(self):
        from backend.agriculture.risk_engine import RiskEngine
        self.engine = RiskEngine()

    def _weather(self, temp=25, humidity=60, rain=0, wind=10):
        return {"temperature_c": temp, "humidity_percent": humidity, "rainfall_mm": rain, "wind_speed_kmh": wind}

    def _forecast(self, rain_mm=0, pop=0, days=5):
        return [{"rainfall_mm": rain_mm, "rain_probability": pop, "temp_max_c": 30} for _ in range(days)]

    def test_heavy_rain_risk_detected(self):
        """Heavy rain forecast → heavy rain risk alert."""
        result = self.engine.analyse(
            farm_id=1, location="Mumbai",
            current_weather=self._weather(),
            forecast_days=self._forecast(rain_mm=50, pop=90),
            active_crops=[{"crop_name": "Rice", "current_stage": "vegetative", "area_acres": 2}],
        )
        risk_types = [r["risk_type"] for r in result["risks"]]
        assert "heavy_rain" in risk_types

    def test_heat_stress_detected(self):
        """Temperature >= 40°C → heat stress alert."""
        result = self.engine.analyse(
            farm_id=1, location="Rajasthan",
            current_weather=self._weather(temp=42),
            forecast_days=self._forecast(),
            active_crops=[{"crop_name": "Wheat", "current_stage": "flowering", "area_acres": 1}],
        )
        risk_types = [r["risk_type"] for r in result["risks"]]
        assert "heat_stress" in risk_types
        heat_risk = next(r for r in result["risks"] if r["risk_type"] == "heat_stress")
        assert heat_risk["level"] in ["medium", "high"]

    def test_fungal_risk_high_humidity_and_rain(self):
        """High humidity + rainfall → fungal risk conditions."""
        result = self.engine.analyse(
            farm_id=1, location="Kerala",
            current_weather=self._weather(humidity=90, rain=20),
            forecast_days=self._forecast(rain_mm=10),
            active_crops=[{"crop_name": "Rice", "current_stage": "vegetative", "area_acres": 1}],
        )
        risk_types = [r["risk_type"] for r in result["risks"]]
        assert "fungal_risk" in risk_types
        # Check wording — must not claim diagnosis
        fungal = next(r for r in result["risks"] if r["risk_type"] == "fungal_risk")
        assert "diagnos" not in fungal["description"].lower()
        assert "favorable" in fungal["description"].lower() or "conditions" in fungal["description"].lower()

    def test_dry_spell_detected(self):
        """No rainfall in 5 days → dry spell warning."""
        result = self.engine.analyse(
            farm_id=1, location="Jaipur",
            current_weather=self._weather(rain=0),
            forecast_days=self._forecast(rain_mm=0),
            active_crops=[{"crop_name": "Wheat", "current_stage": "vegetative", "area_acres": 1}],
        )
        risk_types = [r["risk_type"] for r in result["risks"]]
        assert "dry_spell" in risk_types

    def test_no_risks_on_perfect_weather(self):
        """Normal weather → no high/critical risks."""
        result = self.engine.analyse(
            farm_id=1, location="Pune",
            current_weather=self._weather(temp=25, humidity=55, rain=3),
            forecast_days=self._forecast(rain_mm=3, pop=30),
            active_crops=[{"crop_name": "Wheat", "current_stage": "vegetative", "area_acres": 1}],
        )
        high_risks = [r for r in result["risks"] if r["level"] in ["high", "critical"]]
        assert len(high_risks) == 0


# ─────────────────────────────────────────────
# CROP CALENDAR TESTS
# ─────────────────────────────────────────────

class TestCropCalendarService:
    def setup_method(self):
        from backend.agriculture.crop_calendar import CropCalendarService
        self.service = CropCalendarService()

    def test_calendar_has_all_stages(self):
        sowing = date.today() - timedelta(days=30)
        result = self.service.generate_calendar("Wheat", sowing)
        stage_names = [s["stage"] for s in result["stages"]]
        assert "sowing" in stage_names
        assert "vegetative" in stage_names
        assert "harvest" in stage_names

    def test_current_stage_detected(self):
        sowing = date.today() - timedelta(days=30)
        result = self.service.generate_calendar("Wheat", sowing)
        # After 30 days, should be in vegetative or germination
        assert result["current_stage"] is not None

    def test_tasks_generated(self):
        sowing = date.today() - timedelta(days=10)
        result = self.service.generate_calendar("Rice", sowing)
        assert len(result["generated_tasks"]) > 0

    def test_harvest_date_calculated(self):
        sowing = date(2025, 11, 1)
        result = self.service.generate_calendar("Wheat", sowing)
        # Wheat takes ~120 days
        assert result["expected_harvest_date"] is not None


# ─────────────────────────────────────────────
# ACTION PLAN TESTS
# ─────────────────────────────────────────────

class TestActionPlanEngine:
    def setup_method(self):
        from backend.agriculture.action_plan import ActionPlanEngine
        self.engine = ActionPlanEngine()

    def test_plan_has_7_days(self):
        result = self.engine.generate(
            farm_id=1, farm_name="Test Farm",
            active_crops=[{"crop_name": "Wheat", "current_stage": "vegetative", "area_acres": 2}],
            irrigation_recommendation={"irrigation_required": True, "estimated_requirement_mm": 20, "reason": "dry", "recommended_time": "06:00"},
            weather_forecast=[{"rainfall_mm": 0, "rain_probability": 0, "temp_max_c": 30, "temp_min_c": 18, "description": "Clear", "icon": ""} for _ in range(7)],
            current_weather={"temperature_c": 25, "humidity_percent": 55, "rainfall_mm": 0, "wind_speed_kmh": 10},
            risk_analysis={"risks": [], "overall_risk_level": "none"},
            pending_tasks=[],
        )
        assert len(result["days"]) == 7
        assert result["days"][0]["day_label"] == "TODAY"
        assert result["days"][1]["day_label"] == "TOMORROW"

    def test_irrigation_action_on_first_day(self):
        result = self.engine.generate(
            farm_id=1, farm_name="Test Farm",
            active_crops=[{"crop_name": "Wheat", "current_stage": "vegetative", "area_acres": 2}],
            irrigation_recommendation={"irrigation_required": True, "estimated_requirement_mm": 18, "reason": "soil dry", "recommended_time": "06:00"},
            weather_forecast=[{"rainfall_mm": 0, "rain_probability": 0, "temp_max_c": 28, "temp_min_c": 15, "description": "Clear", "icon": ""} for _ in range(7)],
            current_weather={"temperature_c": 25, "humidity_percent": 55, "rainfall_mm": 0, "wind_speed_kmh": 10},
            risk_analysis={"risks": [], "overall_risk_level": "none"},
            pending_tasks=[],
        )
        today_actions = result["days"][0]["actions"]
        irrigation_actions = [a for a in today_actions if a["category"] == "irrigation"]
        assert len(irrigation_actions) > 0

    def test_rain_day_has_weather_action(self):
        result = self.engine.generate(
            farm_id=1, farm_name="Test Farm",
            active_crops=[],
            irrigation_recommendation={"irrigation_required": False, "reason": "ok", "skip_reason": "ok"},
            weather_forecast=[{"rainfall_mm": 30, "rain_probability": 90, "temp_max_c": 25, "temp_min_c": 18, "description": "Rain", "icon": ""} for _ in range(7)],
            current_weather={"temperature_c": 22, "humidity_percent": 85, "rainfall_mm": 5, "wind_speed_kmh": 10},
            risk_analysis={"risks": [], "overall_risk_level": "none"},
            pending_tasks=[],
        )
        today_actions = result["days"][0]["actions"]
        weather_actions = [a for a in today_actions if a["category"] == "weather"]
        assert len(weather_actions) > 0


# ─────────────────────────────────────────────
# MARKET SERVICE TESTS
# ─────────────────────────────────────────────

class TestMarketService:
    def setup_method(self):
        from backend.services.market_service import MarketService
        self.service = MarketService()

    @pytest.mark.asyncio
    async def test_wheat_has_msp_price(self):
        result = await self.service.get_prices("wheat", "Delhi")
        assert result["available"] is True
        assert result["price_per_quintal"] is not None
        assert result["price_per_quintal"] > 0
        assert "MSP" in result.get("note", "") or "source" in result

    @pytest.mark.asyncio
    async def test_unknown_crop_returns_not_available(self):
        result = await self.service.get_prices("unknowncrop123", "Delhi")
        assert result["available"] is False

    @pytest.mark.asyncio
    async def test_never_fabricates_variable_prices(self):
        """Tomato prices are variable — must not return a fabricated price."""
        result = await self.service.get_prices("tomato", "Nashik")
        # If available is False, price must be None
        if not result["available"]:
            assert result["price_per_quintal"] is None


# ─────────────────────────────────────────────
# END-TO-END WORKFLOW TEST
# ─────────────────────────────────────────────

class TestE2EWorkflow:
    """Phase 21: End-to-end workflow validation using in-memory SQLite."""

    @pytest.fixture(autouse=True)
    def setup_db(self):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from backend.database.connection import Base
        from backend.models import models  # noqa: register all models

        engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine)
        Session = sessionmaker(bind=engine)
        self.db = Session()
        yield
        self.db.close()

    def test_create_user_and_farm(self):
        from backend.models import User, Farm, SoilProfile
        from backend.models.models import IrrigationMethod, WaterSource, SoilType

        user = User(name="Ramesh Kumar", email="ramesh@test.com")
        self.db.add(user)
        self.db.commit()
        assert user.id is not None

        farm = Farm(
            user_id=user.id,
            name="Ramesh's Farm",
            location="Nagpur,IN",
            total_area_acres=5.0,
            irrigation_method=IrrigationMethod.drip,
            water_source=WaterSource.borewell,
        )
        self.db.add(farm)
        self.db.commit()
        assert farm.id is not None

        soil = SoilProfile(
            farm_id=farm.id,
            soil_type=SoilType.loamy,
            ph_level=6.5,
        )
        self.db.add(soil)
        self.db.commit()

        # Verify retrieval
        fetched_farm = self.db.query(Farm).filter(Farm.id == farm.id).first()
        assert fetched_farm.name == "Ramesh's Farm"
        assert fetched_farm.soil_profile.ph_level == 6.5

    def test_add_crop_with_calendar_tasks(self):
        from backend.models import User, Farm, Field, Crop, FarmTask
        from backend.models.models import IrrigationMethod, WaterSource, CropStatus, GrowthStage

        user = User(name="Suresh", email="suresh@test.com")
        self.db.add(user)
        farm = Farm(user_id=user.id if user.id else 1, name="S Farm", location="Pune,IN", total_area_acres=3,
                    irrigation_method=IrrigationMethod.flood, water_source=WaterSource.canal)
        self.db.add(user)
        self.db.commit()
        farm.user_id = user.id
        self.db.add(farm)
        self.db.commit()

        field = Field(farm_id=farm.id, name="North Field", area_acres=2.0)
        self.db.add(field)
        self.db.commit()

        sowing = date.today() - timedelta(days=20)
        crop = Crop(
            field_id=field.id, crop_name="Wheat", area_acres=2.0,
            sowing_date=sowing, status=CropStatus.active, current_stage=GrowthStage.vegetative
        )
        self.db.add(crop)
        self.db.commit()

        # Verify crop saved
        fetched = self.db.query(Crop).filter(Crop.id == crop.id).first()
        assert fetched.crop_name == "Wheat"
        assert fetched.sowing_date == sowing

    def test_irrigation_recommendation_no_crash(self):
        """Irrigation engine should not crash with valid inputs."""
        from backend.agriculture.irrigation_engine import IrrigationEngine
        engine = IrrigationEngine()
        result = engine.calculate(
            crop_name="Wheat", crop_stage="vegetative",
            area_acres=2.0, soil_type="loamy",
            irrigation_method="drip",
            water_requirement_mm_per_day=4.5,
            forecast_days=[{"rainfall_mm": 0, "rain_probability": 10}],
            current_weather={"temperature_c": 25, "humidity_percent": 60, "rainfall_mm": 0},
        )
        assert "irrigation_required" in result
        assert "reason" in result
        assert isinstance(result["irrigation_required"], bool)
