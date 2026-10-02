"""
SmartFarm - Weather Service (Phase 3)
Abstraction layer over OpenWeatherMap API.
All weather data comes from the API — never fabricated.
"""
import logging
import httpx
from datetime import datetime, timezone
from typing import Optional
from backend.config import settings

logger = logging.getLogger(__name__)

# Wind direction mapping
WIND_DEGREES = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"
]

def _deg_to_compass(deg: float) -> str:
    idx = round(deg / 22.5) % 16
    return WIND_DEGREES[idx]

def _unix_to_ist(ts: int) -> str:
    """Convert UNIX timestamp to IST time string HH:MM."""
    from datetime import timezone, timedelta
    IST = timezone(timedelta(hours=5, minutes=30))
    return datetime.fromtimestamp(ts, tz=IST).strftime("%H:%M")

def _icon_url(icon_code: str) -> str:
    return f"https://openweathermap.org/img/wn/{icon_code}@2x.png"


class WeatherService:
    """
    Service to fetch weather data from OpenWeatherMap.
    All public methods raise WeatherServiceError on failure.
    Never return fabricated data.
    """

    BASE = settings.weather_api_base
    API_KEY = settings.weather_api_key
    TIMEOUT = 10  # seconds

    def _check_api_key(self):
        if not self.API_KEY:
            raise WeatherServiceError("WEATHER_API_KEY is not configured.")

    async def get_current_weather(self, location: str) -> dict:
        """Returns current weather for a location name (e.g., 'Nagpur,IN')."""
        self._check_api_key()
        url = f"{self.BASE}/weather"
        params = {
            "q": location,
            "appid": self.API_KEY,
            "units": "metric"
        }
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise WeatherServiceError(f"Location '{location}' not found.")
                raise WeatherServiceError(f"Weather API error: {e.response.status_code}")
            except httpx.RequestError as e:
                raise WeatherServiceError(f"Weather API connection failed: {e}")

        rain_1h = data.get("rain", {}).get("1h", 0.0)
        wind_deg = data.get("wind", {}).get("deg", 0)

        return {
            "location": f"{data['name']}, {data['sys']['country']}",
            "temperature_c": round(data["main"]["temp"], 1),
            "feels_like_c": round(data["main"]["feels_like"], 1),
            "humidity_percent": data["main"]["humidity"],
            "rainfall_mm": round(rain_1h, 2),
            "wind_speed_kmh": round(data.get("wind", {}).get("speed", 0) * 3.6, 1),
            "wind_direction": _deg_to_compass(wind_deg),
            "cloud_cover_percent": data.get("clouds", {}).get("all", 0),
            "description": data["weather"][0]["description"].title(),
            "icon": _icon_url(data["weather"][0]["icon"]),
            "icon_code": data["weather"][0]["icon"],
            "sunrise": _unix_to_ist(data["sys"]["sunrise"]),
            "sunset": _unix_to_ist(data["sys"]["sunset"]),
            "rain_probability": 0.0,  # Current weather has no pop; use forecast for pop
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_forecast(self, location: str, days: int = 7) -> dict:
        """
        Returns N-day daily forecast. OWM free tier provides 5 days / 3-hour intervals.
        We aggregate into daily summaries.
        """
        self._check_api_key()
        url = f"{self.BASE}/forecast"
        params = {
            "q": location,
            "appid": self.API_KEY,
            "units": "metric",
            "cnt": min(days * 8, 40)  # 8 x 3h = 1 day, max 40 = 5 days
        }
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise WeatherServiceError(f"Location '{location}' not found.")
                raise WeatherServiceError(f"Forecast API error: {e.response.status_code}")
            except httpx.RequestError as e:
                raise WeatherServiceError(f"Forecast API connection failed: {e}")

        return self._aggregate_forecast(data, days)

    def _aggregate_forecast(self, data: dict, days: int) -> dict:
        """Aggregate 3-hourly OWM forecast into daily summaries."""
        from collections import defaultdict
        import json

        daily = defaultdict(lambda: {
            "temps": [], "humidities": [], "rain": 0.0, "pops": [],
            "descriptions": [], "icons": []
        })

        for item in data.get("list", []):
            dt = datetime.fromtimestamp(item["dt"])
            day_key = dt.strftime("%Y-%m-%d")
            d = daily[day_key]
            d["temps"].append(item["main"]["temp"])
            d["humidities"].append(item["main"]["humidity"])
            d["rain"] += item.get("rain", {}).get("3h", 0.0)
            d["pops"].append(item.get("pop", 0.0))
            d["descriptions"].append(item["weather"][0]["description"].title())
            d["icons"].append(item["weather"][0]["icon"])

        result_days = []
        DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

        for i, (day_key, d) in enumerate(sorted(daily.items())[:days]):
            dt = datetime.strptime(day_key, "%Y-%m-%d")
            result_days.append({
                "date": day_key,
                "day_of_week": DAY_NAMES[dt.weekday()],
                "temp_max_c": round(max(d["temps"]), 1),
                "temp_min_c": round(min(d["temps"]), 1),
                "humidity_percent": round(sum(d["humidities"]) / len(d["humidities"]), 1),
                "rainfall_mm": round(d["rain"], 2),
                "rain_probability": round(max(d["pops"]) * 100, 1),
                "description": max(set(d["descriptions"]), key=d["descriptions"].count),
                "icon": _icon_url(max(set(d["icons"]), key=d["icons"].count)),
            })

        city_name = data.get("city", {}).get("name", "")
        country = data.get("city", {}).get("country", "")
        return {
            "location": f"{city_name}, {country}",
            "days": result_days
        }

    async def get_rainfall_forecast(self, location: str, days: int = 5) -> list:
        """Returns list of daily expected rainfall amounts."""
        forecast = await self.get_forecast(location, days)
        return [
            {"date": d["date"], "rainfall_mm": d["rainfall_mm"], "probability": d["rain_probability"]}
            for d in forecast["days"]
        ]

    async def get_current_by_coords(self, lat: float, lon: float) -> dict:
        """Fetch current weather using coordinates."""
        self._check_api_key()
        url = f"{self.BASE}/weather"
        params = {"lat": lat, "lon": lon, "appid": self.API_KEY, "units": "metric"}
        async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
            try:
                resp = await client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                raise WeatherServiceError(f"Weather API error: {e}")
        return await self.get_current_weather(f"{data['name']},{data['sys']['country']}")


class WeatherServiceError(Exception):
    """Raised when the weather service cannot retrieve data."""
    pass


# Module-level singleton
weather_service = WeatherService()
