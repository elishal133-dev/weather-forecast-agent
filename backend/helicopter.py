"""
Helicopter Flight Forecast Module
Evaluates conditions for safe helicopter flights
Full daily forecast: wind, temp, clouds, cloud base, sun/moon
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import httpx

# PyEphem for accurate astronomical calculations
try:
    import ephem
    HAS_EPHEM = True
except ImportError:
    HAS_EPHEM = False

logger = logging.getLogger('helicopter')


def calculate_civil_twilight_end(sunset_str: str, latitude: float) -> str:
    """
    Calculate civil twilight end time (sun 6° below horizon).
    For Israel latitudes (~29-33°), civil twilight is approximately 25-30 minutes after sunset.
    """
    if not sunset_str:
        return ""
    try:
        sunset_dt = datetime.fromisoformat(sunset_str)
        # Civil twilight duration varies with latitude and time of year
        # For Israel (lat ~30-33°), it's approximately 25-28 minutes
        # Use a simple approximation based on latitude
        twilight_minutes = int(24 + (latitude - 29) * 0.5)  # ~24-26 min for Israel
        civil_twilight_end = sunset_dt + timedelta(minutes=twilight_minutes)
        return civil_twilight_end.isoformat()
    except Exception:
        return ""

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

def cloud_oktas(cover_pct: float) -> int:
    """Convert cloud cover percentage to oktas (0-8 scale)"""
    if cover_pct is None:
        return 0
    # Convert percentage to oktas (0-8)
    return min(8, max(0, round(cover_pct / 12.5)))


def cloud_oktas_str(cover_pct: float) -> str:
    """Convert cloud cover percentage to oktas string format (e.g., '6/8')"""
    oktas = cloud_oktas(cover_pct)
    return f"{oktas}/8"


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


def calculate_moon_times(target_date: date, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
    """
    Calculate accurate moonrise and moonset times using PyEphem.
    Returns (moonrise, moonset) as time strings or None if unavailable.
    """
    if not HAS_EPHEM:
        return _estimate_moon_times_simple(target_date)

    try:
        observer = ephem.Observer()
        observer.lat = str(lat)
        observer.lon = str(lon)
        observer.elevation = 0
        observer.pressure = 0

        observer.date = ephem.Date(datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0))
        moon = ephem.Moon()

        moonrise_str = None
        try:
            moonrise = observer.next_rising(moon, use_center=True)
            moonrise_dt = ephem.Date(moonrise).datetime()
            moonrise_local = moonrise_dt + timedelta(hours=2)  # Israel timezone
            if moonrise_local.date() == target_date:
                moonrise_str = moonrise_local.strftime("%H:%M")
        except (ephem.NeverUpError, ephem.AlwaysUpError):
            pass

        moonset_str = None
        try:
            observer.date = ephem.Date(datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0))
            moonset = observer.next_setting(moon, use_center=True)
            moonset_dt = ephem.Date(moonset).datetime()
            moonset_local = moonset_dt + timedelta(hours=2)
            if moonset_local.date() == target_date:
                moonset_str = moonset_local.strftime("%H:%M")
        except (ephem.NeverUpError, ephem.AlwaysUpError):
            pass

        return (moonrise_str, moonset_str)

    except Exception as e:
        logger.warning(f"PyEphem moon calculation error: {e}")
        return _estimate_moon_times_simple(target_date)


def _estimate_moon_times_simple(target_date: date) -> Tuple[Optional[str], Optional[str]]:
    """Fallback simplified moon times estimation"""
    phase_day = (target_date - date(2000, 1, 6)).days % 29.53
    rise_hour = 6 + (phase_day / 29.53) * 12
    set_hour = (rise_hour + 12) % 24

    rise_h = int(rise_hour) % 24
    rise_m = int((rise_hour % 1) * 60)
    set_h = int(set_hour) % 24
    set_m = int((set_hour % 1) * 60)

    return (f"{rise_h:02d}:{rise_m:02d}", f"{set_h:02d}:{set_m:02d}")


def get_moon_visibility_status(moonrise: Optional[str], moonset: Optional[str], sunset: Optional[str]) -> Dict:
    """
    Determine moon visibility status during night hours.
    Returns status info with Hebrew text and icon.
    """
    sunset_hour = 17
    if sunset:
        try:
            sunset_hour = int(sunset.split('T')[1][:2])
        except:
            pass

    def time_to_hours(t: Optional[str]) -> Optional[float]:
        if not t:
            return None
        try:
            parts = t.split(':')
            return int(parts[0]) + int(parts[1]) / 60
        except:
            return None

    rise_h = time_to_hours(moonrise)
    set_h = time_to_hours(moonset)
    night_start = sunset_hour

    if rise_h is None and set_h is None:
        return {"status": "unknown", "status_he": "לא ידוע", "icon": "❓"}

    if rise_h is not None and set_h is not None:
        if rise_h < set_h:
            if rise_h >= night_start:
                return {"status": "rises_at_night", "status_he": f"עולה ב-{moonrise}", "icon": "🌙↑"}
            elif set_h <= night_start:
                return {"status": "not_visible", "status_he": "לא נראה בלילה", "icon": "🌑"}
            elif set_h > night_start:
                return {"status": "sets_at_night", "status_he": f"שוקע ב-{moonset}", "icon": "🌙↓"}
        else:
            if rise_h >= night_start:
                return {"status": "rises_at_night", "status_he": f"עולה ב-{moonrise}", "icon": "🌙↑"}
            else:
                return {"status": "sets_at_night", "status_he": f"שוקע ב-{moonset}", "icon": "🌙↓"}

    if rise_h is not None:
        if rise_h >= night_start or rise_h <= 4:
            return {"status": "rises_at_night", "status_he": f"עולה ב-{moonrise}", "icon": "🌙↑"}
        else:
            return {"status": "visible_all_night", "status_he": "נראה כל הלילה", "icon": "🌕"}

    if set_h is not None:
        if set_h >= night_start or set_h <= 4:
            return {"status": "sets_at_night", "status_he": f"שוקע ב-{moonset}", "icon": "🌙↓"}
        else:
            return {"status": "not_visible", "status_he": "לא נראה בלילה", "icon": "🌑"}

    return {"status": "unknown", "status_he": "לא ידוע", "icon": "❓"}


class HelicopterService:
    """Service for helicopter flight forecasts using multi-source weather data"""

    WEATHER_API = "https://api.open-meteo.com/v1/forecast"

    # Flight limits
    MAX_WIND_KNOTS = 30
    MAX_GUSTS_KNOTS = 40
    MIN_VISIBILITY_KM = 3
    MAX_PRECIPITATION_MM = 0.5

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        # Import multi-source weather
        try:
            from multi_source_weather import MultiSourceWeather
            self.multi_weather = MultiSourceWeather()
            self.use_multi_source = True
            logger.info("HelicopterService: Multi-source weather enabled")
        except ImportError:
            self.multi_weather = None
            self.use_multi_source = False
            logger.info("HelicopterService: Using single source (Open-Meteo)")

    async def close(self):
        await self.client.aclose()
        if self.multi_weather:
            await self.multi_weather.close()

    def _get_location(self, location_id: str) -> Optional[Dict]:
        for loc in HELICOPTER_LOCATIONS:
            if loc["id"] == location_id.lower().replace(" ", "_") or \
               loc["name"].lower() == location_id.lower():
                return loc
        return None

    async def get_forecast(self, location: str, days: int = 3) -> Optional[Dict]:
        """Get helicopter flight forecast for a location using multi-source data"""
        loc = self._get_location(location)
        if not loc:
            return None

        # Fetch multi-source hourly data if available
        multi_hourly = []
        sources_used = ["open_meteo"]
        if self.use_multi_source and self.multi_weather:
            try:
                multi_hourly = await self.multi_weather.fetch_hourly(loc["lat"], loc["lon"], hours=days * 24)
                if multi_hourly:
                    sources_used = list(set(
                        src for item in multi_hourly
                        for src in (item.get("sources", [item.get("source", "unknown")]))
                    ))
                    logger.info(f"Multi-source data for {loc['name']}: {len(multi_hourly)} hours from {sources_used}")
            except Exception as e:
                logger.warning(f"Multi-source fetch failed for {loc['name']}: {e}")

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
                # Get base data from Open-Meteo
                wind = hourly.get("wind_speed_10m", [])[i] or 0
                wind_dir = hourly.get("wind_direction_10m", [])[i] or 0
                gusts = hourly.get("wind_gusts_10m", [])[i] or 0
                visibility = (hourly.get("visibility", [])[i] or 50000) / 1000
                cloud = hourly.get("cloud_cover", [])[i] or 0
                precip = hourly.get("precipitation", [])[i] or 0
                temp = hourly.get("temperature_2m", [])[i] or 20
                dewpoint = hourly.get("dewpoint_2m", [])[i] or 15
                humidity = hourly.get("relative_humidity_2m", [])[i] or 50

                # Override with multi-source averaged data if available
                if multi_hourly and i < len(multi_hourly):
                    mh = multi_hourly[i]
                    wind = mh.get("wind_speed_knots", wind)
                    gusts = mh.get("wind_gusts_knots", gusts)
                    wind_dir = mh.get("wind_direction_deg", wind_dir)
                    temp = mh.get("temperature_c", temp)
                    humidity = mh.get("humidity_percent", humidity)
                    cloud = mh.get("cloud_cover_percent", cloud)
                    visibility = mh.get("visibility_km", visibility)
                    precip = mh.get("precipitation_mm", precip)
                    if mh.get("dewpoint_c") is not None:
                        dewpoint = mh.get("dewpoint_c")

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
                    "cloud_oktas": cloud_oktas_str(cloud),
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

                # Calculate moon rise/set times
                moonrise, moonset = calculate_moon_times(day_date, loc["lat"], loc["lon"])
                moon_status = get_moon_visibility_status(moonrise, moonset, sunset)

                # Get hours for this day (safe division)
                day_hours = [c for c in conditions if c["time"].startswith(day_str)]
                day_hours_count = len(day_hours) if len(day_hours) > 0 else 1
                avg_cloud = sum(h["cloud_cover_percent"] for h in day_hours) / day_hours_count
                avg_cloud_base = sum(h["cloud_base_ft"] for h in day_hours) / day_hours_count
                flyable_hours = sum(1 for h in day_hours if h["is_flyable"])

                # Calculate civil twilight end (6° below horizon)
                civil_twilight = calculate_civil_twilight_end(sunset, loc["lat"])

                daily_summaries.append({
                    "date": day_str,
                    "temp_max": daily_raw.get("temperature_2m_max", [])[i],
                    "temp_min": daily_raw.get("temperature_2m_min", [])[i],
                    "wind_max_knots": daily_raw.get("wind_speed_10m_max", [])[i],
                    "gusts_max_knots": daily_raw.get("wind_gusts_10m_max", [])[i],
                    "wind_direction_dominant": daily_raw.get("wind_direction_10m_dominant", [])[i],
                    "precipitation_sum": daily_raw.get("precipitation_sum", [])[i],
                    "cloud_cover_avg": round(avg_cloud),
                    "cloud_oktas": cloud_oktas_str(avg_cloud),
                    "cloud_base_avg_ft": round(avg_cloud_base),
                    "sunrise": sunrise,
                    "sunset": sunset,
                    "civil_twilight_end": civil_twilight,
                    "moonrise": moonrise,
                    "moonset": moonset,
                    "moon_status": moon_status["status"],
                    "moon_status_he": moon_status["status_he"],
                    "moon_status_icon": moon_status["icon"],
                    "moon_illumination": moon_ill,
                    "moon_phase": moon_ph,
                    "flyable_hours": flyable_hours,
                    "total_hours": len(day_hours)
                })

            return {
                "location": loc,
                "forecast": conditions,
                "daily": daily_summaries,
                "sources": sources_used,
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
                    "cloud_oktas": current["cloud_oktas"],
                    "cloud_base_ft": current["cloud_base_ft"],
                    "sunrise": today.get("sunrise", ""),
                    "sunset": today.get("sunset", ""),
                    "civil_twilight_end": today.get("civil_twilight_end", ""),
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
