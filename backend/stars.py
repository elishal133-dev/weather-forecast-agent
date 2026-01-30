"""
Stargazing Forecast Module
Evaluates conditions for night sky observation
Factors: Moon rise/phase, cloud cover, light pollution
"""

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Optional
import httpx
import math

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
        illumination = (1 - math.cos(2 * math.pi * phase_day / lunar_cycle)) / 2 * 100

        # Phase names
        if phase_day < 1.85:
            phase = "New Moon"
        elif phase_day < 7.38:
            phase = "Waxing Crescent"
        elif phase_day < 9.23:
            phase = "First Quarter"
        elif phase_day < 14.77:
            phase = "Waxing Gibbous"
        elif phase_day < 16.61:
            phase = "Full Moon"
        elif phase_day < 22.15:
            phase = "Waning Gibbous"
        elif phase_day < 23.99:
            phase = "Last Quarter"
        else:
            phase = "Waning Crescent"

        return {
            "phase": phase,
            "illumination": round(illumination, 1),
            "is_good_for_stars": illumination < 40  # Less than 40% is good
        }

    def _estimate_moonrise(self, target_date: date, lat: float) -> Optional[str]:
        """Estimate moonrise time (simplified calculation)"""
        # This is a simplified estimation
        # In production, use PyEphem or Skyfield for accuracy
        moon = self._calculate_moon_phase(target_date)
        phase_day = (target_date - date(2000, 1, 6)).days % 29.53

        # Rough moonrise estimation based on phase
        # New moon rises at sunrise, full moon at sunset
        base_hour = 6 + (phase_day / 29.53) * 12

        hour = int(base_hour) % 24
        minute = int((base_hour % 1) * 60)

        return f"{hour:02d}:{minute:02d}"

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

                avg_cloud = sum(night_clouds) / len(night_clouds) if night_clouds else 50

                # Moon data
                moon = self._calculate_moon_phase(target_date)
                moonrise = self._estimate_moonrise(target_date, loc["lat"])

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
            print(f"Error fetching stars forecast: {e}")
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
                    "cloud_cover": tonight["cloud_cover_night"],
                    "is_good_night": tonight["is_good_night"]
                })

        # Sort by score
        rankings.sort(key=lambda x: x["score"], reverse=True)

        return {
            "rankings": rankings,
            "fetched_at": datetime.now().isoformat()
        }
