"""
Helicopter Flight Forecast Module
Evaluates conditions for safe helicopter flights
Full daily forecast: wind, temp, clouds, cloud base, sun/moon
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger('helicopter')

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

# Cloud cover to oktas symbol mapping (8 symbols)
CLOUD_SYMBOLS = [
    (0, "☀️"),       # 0 oktas - clear
    (12.5, "🌤"),    # 1 okta - mostly clear
    (25, "⛅"),      # 2-3 oktas - partly cloudy
    (37.5, "⛅"),
    (50, "🌥"),      # 4 oktas - half cloudy
    (62.5, "🌥"),    # 5 oktas
    (75, "☁️"),      # 6-7 oktas - mostly cloudy
    (87.5, "☁️"),
    (100, "☁️"),     # 8 oktas - overcast
]


def cloud_symbol(cover_pct: float) -> str:
    """Convert cloud cover % to weather symbol"""
    for threshold, symbol in reversed(CLOUD_SYMBOLS):
        if cover_pct >= threshold:
            return symbol
    return "☀️"


def estimate_cloud_base_ft(temp_c: float, dewpoint_c: float) -> int:
    """Estimate cloud base altitude in feet using spread method"""
    spread = temp_c - dewpoint_c
    cloud_base_ft = max(0, int((spread / 2.5) * 1000))
    return cloud_base_ft


def moon_illumination(dt: date) -> float:
    """Calculate approximate moon illumination percentage"""
    known_new = date(2000, 1, 6)
    days_since = (dt - known_new).days
    cycle = 29.53058867
    phase = (days_since % cycle) / cycle
    # Cosine curve: 0% at new moon (phase=0), 100% at full moon (phase=0.5)
    illumination = (1 - math.cos(2 * math.pi * phase)) / 2
    return round(illumination * 100, 0)


def moon_phase_name(dt: date) -> str:
    """Get moon phase name in Hebrew"""
    known_new = date(2000, 1, 6)
    days_since = (dt - known_new).days
    cycle = 29.53058867
    phase = (days_since % cycle) / cycle
    if phase < 0.03 or phase > 0.97:
        return "ירח חדש 🌑"
    elif phase < 0.22:
        return "סהר הולך וגדל 🌒"
    elif phase < 0.28:
        return "רבע ראשון 🌓"
    elif phase < 0.47:
        return "גיבנוני הולך וגדל 🌔"
    elif phase < 0.53:
        return "ירח מלא 🌕"
    elif phase < 0.72:
        return "גיבנוני הולך וקטן 🌖"
    elif phase < 0.78:
        return "רבע אחרון 🌗"
    else:
        return "סהר הולך וקטן 🌘"


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

    async def close(self):
        await self.client.aclose()

    def _get_location(self, location_id: str) -> Optional[Dict]:
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
            "hourly": (
                "temperature_2m,relative_humidity_2m,dewpoint_2m,"
                "precipitation,cloud_cover,visibility,"
                "wind_speed_10m,wind_direction_10m,wind_gusts_10m"
            ),
            "daily": (
                "temperature_2m_max,temperature_2m_min,"
                "sunrise,sunset,"
                "precipitation_sum,wind_speed_10m_max,wind_gusts_10m_max,"
                "wind_direction_10m_dominant"
            ),
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
                wind_dir = hourly.get("wind_direction_10m", [])[i] or 0
                gusts = hourly.get("wind_gusts_10m", [])[i] or 0
                visibility = (hourly.get("visibility", [])[i] or 50000) / 1000
                cloud = hourly.get("cloud_cover", [])[i] or 0
                precip = hourly.get("precipitation", [])[i] or 0
                temp = hourly.get("temperature_2m", [])[i] or 20
                dewpoint = hourly.get("dewpoint_2m", [])[i] or 15
                humidity = hourly.get("relative_humidity_2m", [])[i] or 50

                cloud_base = estimate_cloud_base_ft(temp, dewpoint)

                # Evaluate conditions
                warnings = []
                score = 100

                if wind > self.MAX_WIND_KNOTS:
                    warnings.append(f"רוח חזקה: {wind:.0f}kts")
                    score -= 40
                elif wind > 20:
                    score -= (wind - 20) * 2

                if gusts > self.MAX_GUSTS_KNOTS:
                    warnings.append(f"משבים חזקים: {gusts:.0f}kts")
                    score -= 30
                elif gusts > 30:
                    score -= (gusts - 30) * 2

                if visibility < self.MIN_VISIBILITY_KM:
                    warnings.append(f"ראות נמוכה: {visibility:.1f}km")
                    score -= 50
                elif visibility < 5:
                    score -= (5 - visibility) * 5

                if precip > self.MAX_PRECIPITATION_MM:
                    warnings.append(f"משקעים: {precip:.1f}mm")
                    score -= 30

                if cloud > 80:
                    score -= 10

                if cloud_base < 1500:
                    warnings.append(f"בסיס עננים נמוך: {cloud_base}ft")
                    score -= 20

                score = max(0, min(100, score))
                is_flyable = score >= 50 and not warnings

                conditions.append({
                    "time": time_str,
                    "wind_speed_knots": round(wind, 1),
                    "wind_direction_deg": round(wind_dir),
                    "wind_gusts_knots": round(gusts, 1),
                    "visibility_km": round(visibility, 1),
                    "cloud_cover_percent": cloud,
                    "cloud_symbol": cloud_symbol(cloud),
                    "cloud_base_ft": cloud_base,
                    "precipitation_mm": round(precip, 2),
                    "temperature_c": round(temp, 1),
                    "humidity_percent": round(humidity),
                    "is_flyable": is_flyable,
                    "score": round(score, 1),
                    "warnings": warnings
                })

            # Build daily summaries
            daily_raw = data.get("daily", {})
            daily_times = daily_raw.get("time", [])
            daily_summaries = []
            for i, day_str in enumerate(daily_times):
                day_date = date.fromisoformat(day_str)
                sunrise = daily_raw.get("sunrise", [])[i] or ""
                sunset = daily_raw.get("sunset", [])[i] or ""
                moon_ill = moon_illumination(day_date)
                moon_ph = moon_phase_name(day_date)

                # Get hours for this day (safe division)
                day_hours = [c for c in conditions if c["time"].startswith(day_str)]
                day_hours_count = len(day_hours) if len(day_hours) > 0 else 1
                avg_cloud = sum(h["cloud_cover_percent"] for h in day_hours) / day_hours_count
                avg_cloud_base = sum(h["cloud_base_ft"] for h in day_hours) / day_hours_count
                flyable_hours = sum(1 for h in day_hours if h["is_flyable"])

                daily_summaries.append({
                    "date": day_str,
                    "temp_max": daily_raw.get("temperature_2m_max", [])[i],
                    "temp_min": daily_raw.get("temperature_2m_min", [])[i],
                    "wind_max_knots": daily_raw.get("wind_speed_10m_max", [])[i],
                    "gusts_max_knots": daily_raw.get("wind_gusts_10m_max", [])[i],
                    "wind_direction_dominant": daily_raw.get("wind_direction_10m_dominant", [])[i],
                    "precipitation_sum": daily_raw.get("precipitation_sum", [])[i],
                    "cloud_cover_avg": round(avg_cloud),
                    "cloud_symbol": cloud_symbol(avg_cloud),
                    "cloud_base_avg_ft": round(avg_cloud_base),
                    "sunrise": sunrise,
                    "sunset": sunset,
                    "moon_illumination": moon_ill,
                    "moon_phase": moon_ph,
                    "flyable_hours": flyable_hours,
                    "total_hours": len(day_hours)
                })

            return {
                "location": loc,
                "forecast": conditions,
                "daily": daily_summaries,
                "fetched_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching helicopter forecast: {e}")
            return None

    async def get_rankings(self) -> Dict:
        """Get all locations ranked by current flight conditions"""
        import asyncio

        # Fetch ALL locations concurrently to avoid 30s Render timeout
        tasks = [self.get_forecast(loc["id"], days=3) for loc in HELICOPTER_LOCATIONS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        rankings = []
        for forecast in results:
            if isinstance(forecast, dict) and forecast.get("forecast"):
                current = forecast["forecast"][0]
                daily = forecast.get("daily", [{}])
                today = daily[0] if daily else {}

                rankings.append({
                    "location": forecast["location"],
                    "score": current["score"],
                    "is_flyable": current["is_flyable"],
                    "wind_speed_knots": current["wind_speed_knots"],
                    "wind_direction_deg": current["wind_direction_deg"],
                    "wind_gusts_knots": current["wind_gusts_knots"],
                    "visibility_km": current["visibility_km"],
                    "temperature_c": current["temperature_c"],
                    "cloud_cover_percent": current["cloud_cover_percent"],
                    "cloud_symbol": current["cloud_symbol"],
                    "cloud_base_ft": current["cloud_base_ft"],
                    "sunrise": today.get("sunrise", ""),
                    "sunset": today.get("sunset", ""),
                    "moon_illumination": today.get("moon_illumination", 0),
                    "moon_phase": today.get("moon_phase", ""),
                    "warnings": current["warnings"],
                    "daily": daily
                })

        rankings.sort(key=lambda x: x["score"], reverse=True)

        return {
            "rankings": rankings,
            "fetched_at": datetime.now().isoformat()
        }
