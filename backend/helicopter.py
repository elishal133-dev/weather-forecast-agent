"""
Helicopter Flight Forecast Module
Evaluates conditions for safe helicopter flights
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import httpx

# Helicopter-friendly locations in Israel
HELICOPTER_LOCATIONS = [
    {"id": "tel_aviv", "name": "Tel Aviv", "name_he": "תל אביב", "lat": 32.0853, "lon": 34.7818},
    {"id": "jerusalem", "name": "Jerusalem", "name_he": "ירושלים", "lat": 31.7683, "lon": 35.2137},
    {"id": "haifa", "name": "Haifa", "name_he": "חיפה", "lat": 32.7940, "lon": 34.9896},
    {"id": "eilat", "name": "Eilat", "name_he": "אילת", "lat": 29.5577, "lon": 34.9519},
    {"id": "beer_sheva", "name": "Beer Sheva", "name_he": "באר שבע", "lat": 31.2518, "lon": 34.7913},
    {"id": "tiberias", "name": "Tiberias", "name_he": "טבריה", "lat": 32.7922, "lon": 35.5312},
    {"id": "netanya", "name": "Netanya", "name_he": "נתניה", "lat": 32.3215, "lon": 34.8532},
]


@dataclass
class FlightConditions:
    """Flight conditions for a specific hour"""
    time: datetime
    wind_speed_knots: float
    wind_gusts_knots: float
    visibility_km: float
    cloud_cover_percent: int
    precipitation_mm: float
    temperature_c: float
    is_flyable: bool
    score: float  # 0-100
    warnings: List[str]


class HelicopterService:
    """Service for helicopter flight forecasts"""

    WEATHER_API = "https://api.open-meteo.com/v1/forecast"

    # Flight limits
    MAX_WIND_KNOTS = 30
    MAX_GUSTS_KNOTS = 40
    MIN_VISIBILITY_KM = 3
    MAX_PRECIPITATION_MM = 0.5

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.cache: Dict[str, Any] = {}

    async def close(self):
        await self.client.aclose()

    def _get_location(self, location_id: str) -> Optional[Dict]:
        """Get location by ID or name"""
        for loc in HELICOPTER_LOCATIONS:
            if loc["id"] == location_id.lower().replace(" ", "_") or \
               loc["name"].lower() == location_id.lower():
                return loc
        return None

    async def get_forecast(self, location: str, days: int = 3) -> Optional[Dict]:
        """Get helicopter flight forecast for a location"""
        loc = self._get_location(location)
        if not loc:
            return None

        params = {
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "hourly": "temperature_2m,precipitation,cloud_cover,visibility,wind_speed_10m,wind_gusts_10m",
            "wind_speed_unit": "kn",
            "timezone": "Asia/Jerusalem",
            "forecast_days": days
        }

        try:
            response = await self.client.get(self.WEATHER_API, params=params)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])

            conditions = []
            for i, time_str in enumerate(times):
                wind = hourly.get("wind_speed_10m", [])[i] or 0
                gusts = hourly.get("wind_gusts_10m", [])[i] or 0
                visibility = (hourly.get("visibility", [])[i] or 50000) / 1000  # m to km
                cloud = hourly.get("cloud_cover", [])[i] or 0
                precip = hourly.get("precipitation", [])[i] or 0
                temp = hourly.get("temperature_2m", [])[i] or 20

                # Evaluate conditions
                warnings = []
                score = 100

                if wind > self.MAX_WIND_KNOTS:
                    warnings.append(f"High wind: {wind:.0f}kts")
                    score -= 40
                elif wind > 20:
                    score -= (wind - 20) * 2

                if gusts > self.MAX_GUSTS_KNOTS:
                    warnings.append(f"Strong gusts: {gusts:.0f}kts")
                    score -= 30
                elif gusts > 30:
                    score -= (gusts - 30) * 2

                if visibility < self.MIN_VISIBILITY_KM:
                    warnings.append(f"Low visibility: {visibility:.1f}km")
                    score -= 50
                elif visibility < 5:
                    score -= (5 - visibility) * 5

                if precip > self.MAX_PRECIPITATION_MM:
                    warnings.append(f"Precipitation: {precip:.1f}mm")
                    score -= 30

                if cloud > 80:
                    score -= 10

                score = max(0, min(100, score))
                is_flyable = score >= 50 and not warnings

                conditions.append({
                    "time": time_str,
                    "wind_speed_knots": round(wind, 1),
                    "wind_gusts_knots": round(gusts, 1),
                    "visibility_km": round(visibility, 1),
                    "cloud_cover_percent": cloud,
                    "precipitation_mm": round(precip, 2),
                    "temperature_c": round(temp, 1),
                    "is_flyable": is_flyable,
                    "score": round(score, 1),
                    "warnings": warnings
                })

            return {
                "location": loc,
                "forecast": conditions,
                "fetched_at": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"Error fetching helicopter forecast: {e}")
            return None

    async def get_rankings(self) -> Dict:
        """Get all locations ranked by current flight conditions"""
        rankings = []

        for loc in HELICOPTER_LOCATIONS:
            forecast = await self.get_forecast(loc["id"], days=1)
            if forecast and forecast["forecast"]:
                # Get current hour conditions
                current = forecast["forecast"][0]
                rankings.append({
                    "location": loc,
                    "score": current["score"],
                    "is_flyable": current["is_flyable"],
                    "wind_speed_knots": current["wind_speed_knots"],
                    "visibility_km": current["visibility_km"],
                    "warnings": current["warnings"]
                })

        # Sort by score
        rankings.sort(key=lambda x: x["score"], reverse=True)

        return {
            "rankings": rankings,
            "fetched_at": datetime.now().isoformat()
        }
