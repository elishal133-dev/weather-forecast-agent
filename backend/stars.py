"""
Stargazing Forecast Module
Evaluates conditions for night sky observation
Factors: Moon rise/phase, cloud cover, light pollution
Uses PyEphem for accurate astronomical calculations
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional, Tuple
import httpx

# PyEphem for accurate astronomical calculations
try:
    import ephem
    HAS_EPHEM = True
except ImportError:
    HAS_EPHEM = False

logger = logging.getLogger('stars')

# Best stargazing locations in Israel (low light pollution)
STARGAZING_LOCATIONS = [
    {"id": "mitzpe_ramon", "name": "Mitzpe Ramon", "name_he": "מצפה רמון", "lat": 30.6103, "lon": 34.8011, "light_pollution": "very_low"},
    {"id": "ramon_crater", "name": "Ramon Crater", "name_he": "מכתש רמון", "lat": 30.5833, "lon": 34.8833, "light_pollution": "very_low"},
    {"id": "negev_highlands", "name": "Negev Highlands", "name_he": "רמת הנגב", "lat": 30.8500, "lon": 34.7500, "light_pollution": "very_low"},
    {"id": "arad", "name": "Arad", "name_he": "ערד", "lat": 31.2589, "lon": 35.2129, "light_pollution": "low"},
    {"id": "dead_sea", "name": "Dead Sea", "name_he": "ים המלח", "lat": 31.5000, "lon": 35.5000, "light_pollution": "low"},
    {"id": "golan_heights", "name": "Golan Heights", "name_he": "רמת הגולן", "lat": 33.0000, "lon": 35.7500, "light_pollution": "low"},
    {"id": "galilee", "name": "Upper Galilee", "name_he": "גליל עליון", "lat": 33.0500, "lon": 35.5000, "light_pollution": "medium"},
    {"id": "timna", "name": "Timna Park", "name_he": "פארק תמנע", "lat": 29.7872, "lon": 34.9892, "light_pollution": "very_low"},
]

# Light pollution scores (lower = better for stargazing)
LIGHT_POLLUTION_SCORE = {
    "very_low": 100,
    "low": 80,
    "medium": 60,
    "high": 30
}


class StarsService:
    """Service for stargazing forecasts"""

    WEATHER_API = "https://api.open-meteo.com/v1/forecast"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    def _get_location(self, location_id: str) -> Optional[Dict]:
        """Get location by ID or name"""
        for loc in STARGAZING_LOCATIONS:
            if loc["id"] == location_id.lower().replace(" ", "_") or \
               loc["name"].lower() == location_id.lower():
                return loc
        return None

    def _calculate_moon_phase(self, target_date: date) -> Dict:
        """
        Calculate moon phase and illumination
        Returns phase name and illumination percentage
        """
        # Known new moon: Jan 6, 2000
        known_new_moon = date(2000, 1, 6)
        days_since = (target_date - known_new_moon).days
        lunar_cycle = 29.53059  # days

        phase_day = days_since % lunar_cycle
        phase_fraction = phase_day / lunar_cycle
        illumination = (1 - math.cos(2 * math.pi * phase_fraction)) / 2 * 100

        # Phase names (using fraction: 0=new, 0.5=full)
        if phase_fraction < 0.03 or phase_fraction > 0.97:
            phase = "New Moon"
        elif phase_fraction < 0.22:
            phase = "Waxing Crescent"
        elif phase_fraction < 0.28:
            phase = "First Quarter"
        elif phase_fraction < 0.47:
            phase = "Waxing Gibbous"
        elif phase_fraction < 0.53:
            phase = "Full Moon"
        elif phase_fraction < 0.72:
            phase = "Waning Gibbous"
        elif phase_fraction < 0.78:
            phase = "Last Quarter"
        else:
            phase = "Waning Crescent"

        return {
            "phase": phase,
            "illumination": round(illumination, 1),
            "is_good_for_stars": illumination < 40  # Less than 40% is good
        }

    def _calculate_moon_times(self, target_date: date, lat: float, lon: float) -> Tuple[Optional[str], Optional[str]]:
        """
        Calculate accurate moonrise and moonset times using PyEphem.
        Returns (moonrise, moonset) as ISO time strings or None if unavailable.
        """
        if not HAS_EPHEM:
            # Fallback to simplified estimation
            return self._estimate_moon_times_simple(target_date)

        try:
            # Create observer for the location
            observer = ephem.Observer()
            observer.lat = str(lat)
            observer.lon = str(lon)
            observer.elevation = 0
            observer.pressure = 0  # Disable atmospheric refraction for consistency

            # Set date to start of day (midnight local time)
            # Convert to UTC (Israel is UTC+2 or UTC+3)
            observer.date = ephem.Date(datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0))

            moon = ephem.Moon()

            # Calculate moonrise
            moonrise_str = None
            try:
                moonrise = observer.next_rising(moon, use_center=True)
                moonrise_dt = ephem.Date(moonrise).datetime()
                # Add 2 hours for Israel timezone (approximate)
                moonrise_local = moonrise_dt + timedelta(hours=2)
                if moonrise_local.date() == target_date:
                    moonrise_str = moonrise_local.strftime("%H:%M")
            except (ephem.NeverUpError, ephem.AlwaysUpError):
                pass

            # Calculate moonset
            moonset_str = None
            try:
                # Reset observer date
                observer.date = ephem.Date(datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0))
                moonset = observer.next_setting(moon, use_center=True)
                moonset_dt = ephem.Date(moonset).datetime()
                # Add 2 hours for Israel timezone (approximate)
                moonset_local = moonset_dt + timedelta(hours=2)
                if moonset_local.date() == target_date:
                    moonset_str = moonset_local.strftime("%H:%M")
            except (ephem.NeverUpError, ephem.AlwaysUpError):
                pass

            return (moonrise_str, moonset_str)

        except Exception as e:
            logger.warning(f"PyEphem moon calculation error: {e}")
            return self._estimate_moon_times_simple(target_date)

    def _estimate_moon_times_simple(self, target_date: date) -> Tuple[Optional[str], Optional[str]]:
        """Fallback simplified moon times estimation"""
        phase_day = (target_date - date(2000, 1, 6)).days % 29.53

        # Rough moonrise estimation based on phase
        # New moon rises at sunrise (~6am), full moon at sunset (~18pm)
        rise_hour = 6 + (phase_day / 29.53) * 12
        # Moonset is roughly 12 hours after moonrise
        set_hour = (rise_hour + 12) % 24

        rise_h = int(rise_hour) % 24
        rise_m = int((rise_hour % 1) * 60)
        set_h = int(set_hour) % 24
        set_m = int((set_hour % 1) * 60)

        return (f"{rise_h:02d}:{rise_m:02d}", f"{set_h:02d}:{set_m:02d}")

    def _get_moon_night_status(self, moonrise: Optional[str], moonset: Optional[str], sunset: Optional[str]) -> Dict:
        """
        Determine moon visibility status during night hours (after sunset).
        Returns status info to help users understand when moon is visible.
        """
        # Parse sunset time (format: 2024-01-15T17:30)
        sunset_hour = 17  # default
        if sunset:
            try:
                sunset_hour = int(sunset.split('T')[1][:2])
            except:
                pass

        # Convert times to hours for comparison
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

        # Night hours: sunset to 04:00 next day
        night_start = sunset_hour
        night_end = 4  # 04:00

        # Determine visibility status
        if rise_h is None and set_h is None:
            return {"status": "unknown", "status_he": "לא ידוע", "icon": "❓"}

        if rise_h is not None and set_h is not None:
            if rise_h < set_h:
                # Normal case: moon rises then sets same day
                if rise_h >= night_start:
                    # Moon rises after sunset - visible from moonrise
                    return {"status": "rises_at_night", "status_he": f"עולה ב-{moonrise}", "icon": "🌙↑"}
                elif set_h <= night_start:
                    # Moon sets before sunset - not visible at night
                    return {"status": "not_visible", "status_he": "לא נראה בלילה", "icon": "🌑"}
                elif set_h > night_start:
                    # Moon is up at sunset, sets during night
                    return {"status": "sets_at_night", "status_he": f"שוקע ב-{moonset}", "icon": "🌙↓"}
            else:
                # Moon sets before it rises (crosses midnight)
                if set_h <= night_end and rise_h >= night_start:
                    # Moon visible early night, sets, then rises again late night
                    return {"status": "partial", "status_he": f"שוקע {moonset}, עולה {moonrise}", "icon": "🌗"}
                elif rise_h >= night_start:
                    return {"status": "rises_at_night", "status_he": f"עולה ב-{moonrise}", "icon": "🌙↑"}
                else:
                    return {"status": "sets_at_night", "status_he": f"שוקע ב-{moonset}", "icon": "🌙↓"}

        if rise_h is not None:
            if rise_h >= night_start or rise_h <= night_end:
                return {"status": "rises_at_night", "status_he": f"עולה ב-{moonrise}", "icon": "🌙↑"}
            else:
                return {"status": "visible_all_night", "status_he": "נראה כל הלילה", "icon": "🌕"}

        if set_h is not None:
            if set_h >= night_start or set_h <= night_end:
                return {"status": "sets_at_night", "status_he": f"שוקע ב-{moonset}", "icon": "🌙↓"}
            else:
                return {"status": "not_visible", "status_he": "לא נראה בלילה", "icon": "🌑"}

        return {"status": "unknown", "status_he": "לא ידוע", "icon": "❓"}

    async def get_forecast(self, location: str, days: int = 7) -> Optional[Dict]:
        """Get stargazing forecast for a location"""
        loc = self._get_location(location)
        if not loc:
            return None

        params = {
            "latitude": loc["lat"],
            "longitude": loc["lon"],
            "hourly": "cloud_cover,visibility",
            "daily": "sunrise,sunset",
            "timezone": "Asia/Jerusalem",
            "forecast_days": days
        }

        try:
            response = await self.client.get(self.WEATHER_API, params=params)
            response.raise_for_status()
            data = response.json()

            daily = data.get("daily", {})
            hourly = data.get("hourly", {})

            forecasts = []
            today = date.today()

            for i in range(days):
                target_date = today + timedelta(days=i)
                date_str = target_date.isoformat()

                # Get sunset/sunrise
                sunrise = daily.get("sunrise", [])[i] if i < len(daily.get("sunrise", [])) else None
                sunset = daily.get("sunset", [])[i] if i < len(daily.get("sunset", [])) else None

                # Get night hours cloud cover (20:00 - 04:00)
                night_clouds = []
                for j, time_str in enumerate(hourly.get("time", [])):
                    hour = int(time_str[11:13])
                    hour_date = time_str[:10]
                    if hour_date == date_str and (hour >= 20 or hour <= 4):
                        cloud = hourly.get("cloud_cover", [])[j] or 0
                        night_clouds.append(cloud)

                avg_cloud = sum(night_clouds) / len(night_clouds) if len(night_clouds) > 0 else 50

                # Moon data
                moon = self._calculate_moon_phase(target_date)
                moonrise, moonset = self._calculate_moon_times(target_date, loc["lat"], loc["lon"])
                moon_status = self._get_moon_night_status(moonrise, moonset, sunset)

                # Calculate stargazing score
                # Factors: clouds (40%), moon (40%), light pollution (20%)
                cloud_score = max(0, 100 - avg_cloud)
                moon_score = max(0, 100 - moon["illumination"])
                light_score = LIGHT_POLLUTION_SCORE.get(loc.get("light_pollution", "medium"), 50)

                total_score = (cloud_score * 0.4) + (moon_score * 0.4) + (light_score * 0.2)

                # Rating
                if total_score >= 80:
                    rating = "Excellent"
                elif total_score >= 60:
                    rating = "Good"
                elif total_score >= 40:
                    rating = "Fair"
                else:
                    rating = "Poor"

                forecasts.append({
                    "date": date_str,
                    "sunset": sunset,
                    "sunrise": sunrise,
                    "moonrise": moonrise,
                    "moonset": moonset,
                    "moon_status": moon_status["status"],
                    "moon_status_he": moon_status["status_he"],
                    "moon_status_icon": moon_status["icon"],
                    "moon_phase": moon["phase"],
                    "moon_illumination": moon["illumination"],
                    "cloud_cover_night": round(avg_cloud, 1),
                    "score": round(total_score, 1),
                    "rating": rating,
                    "is_good_night": total_score >= 60
                })

            return {
                "location": loc,
                "forecast": forecasts,
                "fetched_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error fetching stars forecast: {e}")
            return None

    async def get_best_tonight(self) -> Dict:
        """Get best location for stargazing tonight"""
        rankings = await self.get_rankings()
        if rankings["rankings"]:
            best = rankings["rankings"][0]
            return {
                "best_location": best["location"],
                "score": best["score"],
                "rating": best["rating"],
                "moon_phase": best["moon_phase"],
                "cloud_cover": best["cloud_cover"],
                "recommendation": self._get_recommendation(best)
            }
        return {"message": "No data available"}

    def _get_recommendation(self, data: Dict) -> str:
        """Generate recommendation text"""
        score = data["score"]
        if score >= 80:
            return "Perfect night for stargazing! Head out after sunset."
        elif score >= 60:
            return "Good conditions. Bring binoculars or telescope."
        elif score >= 40:
            return "Fair conditions. Visible stars but not ideal."
        else:
            return "Poor conditions tonight. Consider another night."

    async def get_rankings(self) -> Dict:
        """Get all locations ranked by stargazing conditions tonight"""
        import asyncio

        # Fetch ALL locations concurrently to avoid 30s Render timeout
        tasks = [self.get_forecast(loc["id"], days=1) for loc in STARGAZING_LOCATIONS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        rankings = []
        for forecast in results:
            if isinstance(forecast, dict) and forecast.get("forecast"):
                tonight = forecast["forecast"][0]
                rankings.append({
                    "location": forecast["location"],
                    "score": tonight["score"],
                    "rating": tonight["rating"],
                    "moon_phase": tonight["moon_phase"],
                    "moon_illumination": tonight["moon_illumination"],
                    "moonrise": tonight.get("moonrise"),
                    "moonset": tonight.get("moonset"),
                    "moon_status": tonight.get("moon_status"),
                    "moon_status_he": tonight.get("moon_status_he"),
                    "moon_status_icon": tonight.get("moon_status_icon"),
                    "cloud_cover": tonight["cloud_cover_night"],
                    "is_good_night": tonight["is_good_night"]
                })

        # Sort by score
        rankings.sort(key=lambda x: x["score"], reverse=True)

        return {
            "rankings": rankings,
            "fetched_at": datetime.now().isoformat()
        }
