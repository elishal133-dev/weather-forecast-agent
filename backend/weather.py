"""
Weather API Integration using Open-Meteo
Fetches wind and marine (wave) data for kite spots
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import httpx


@dataclass
class WindData:
    """Wind conditions at a specific time"""
    timestamp: datetime
    wind_speed_knots: float      # Wind speed in knots
    wind_gusts_knots: float      # Wind gusts in knots
    wind_direction: int          # Wind direction in degrees (0-360)
    wind_direction_cardinal: str  # N, NE, E, SE, S, SW, W, NW


@dataclass
class WaveData:
    """Wave conditions at a specific time"""
    timestamp: datetime
    wave_height_m: float         # Significant wave height in meters
    wave_period_s: float         # Wave period in seconds
    wave_direction: int          # Wave direction in degrees


@dataclass
class SpotForecast:
    """Complete forecast for a kite spot"""
    spot_id: str
    spot_name: str
    latitude: float
    longitude: float
    wind_data: List[WindData]
    wave_data: Optional[List[WaveData]]  # May be None for inland spots (Kinneret)
    fetched_at: datetime


def degrees_to_cardinal(degrees: int) -> str:
    """Convert wind direction degrees to cardinal direction"""
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = round(degrees / 45) % 8
    return directions[index]


def kmh_to_knots(kmh: float) -> float:
    """Convert km/h to knots"""
    return kmh * 0.539957


def ms_to_knots(ms: float) -> float:
    """Convert m/s to knots"""
    return ms * 1.94384


class WeatherService:
    """Service for fetching weather data from Open-Meteo API"""

    WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
    MARINE_API_URL = "https://marine-api.open-meteo.com/v1/marine"

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        await self.client.aclose()

    async def fetch_wind_data(
        self,
        latitude: float,
        longitude: float,
        days: int = 3
    ) -> List[WindData]:
        """Fetch wind forecast data for a location"""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "wind_speed_10m,wind_gusts_10m,wind_direction_10m",
            "wind_speed_unit": "kn",  # Request in knots directly
            "timezone": "Asia/Jerusalem",
            "forecast_days": days
        }

        try:
            response = await self.client.get(self.WEATHER_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            wind_speeds = hourly.get("wind_speed_10m", [])
            wind_gusts = hourly.get("wind_gusts_10m", [])
            wind_directions = hourly.get("wind_direction_10m", [])

            wind_data = []
            for i, time_str in enumerate(times):
                timestamp = datetime.fromisoformat(time_str)
                direction = int(wind_directions[i]) if wind_directions[i] is not None else 0

                wind_data.append(WindData(
                    timestamp=timestamp,
                    wind_speed_knots=wind_speeds[i] or 0,
                    wind_gusts_knots=wind_gusts[i] or 0,
                    wind_direction=direction,
                    wind_direction_cardinal=degrees_to_cardinal(direction)
                ))

            return wind_data

        except Exception as e:
            print(f"Error fetching wind data: {e}")
            return []

    async def fetch_wave_data(
        self,
        latitude: float,
        longitude: float,
        days: int = 3
    ) -> Optional[List[WaveData]]:
        """Fetch marine/wave forecast data for a location"""
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "wave_height,wave_period,wave_direction",
            "timezone": "Asia/Jerusalem",
            "forecast_days": days
        }

        try:
            response = await self.client.get(self.MARINE_API_URL, params=params)
            response.raise_for_status()
            data = response.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])
            wave_heights = hourly.get("wave_height", [])
            wave_periods = hourly.get("wave_period", [])
            wave_directions = hourly.get("wave_direction", [])

            wave_data = []
            for i, time_str in enumerate(times):
                timestamp = datetime.fromisoformat(time_str)

                wave_data.append(WaveData(
                    timestamp=timestamp,
                    wave_height_m=wave_heights[i] or 0,
                    wave_period_s=wave_periods[i] or 0,
                    wave_direction=int(wave_directions[i]) if wave_directions[i] is not None else 0
                ))

            return wave_data

        except Exception as e:
            # Marine data may not be available for inland locations (Kinneret)
            print(f"Note: Wave data not available: {e}")
            return None

    async def fetch_spot_forecast(
        self,
        spot_id: str,
        spot_name: str,
        latitude: float,
        longitude: float,
        days: int = 3,
        include_waves: bool = True
    ) -> SpotForecast:
        """Fetch complete forecast for a single spot"""

        # Fetch wind and wave data concurrently
        if include_waves:
            wind_task = self.fetch_wind_data(latitude, longitude, days)
            wave_task = self.fetch_wave_data(latitude, longitude, days)
            wind_data, wave_data = await asyncio.gather(wind_task, wave_task)
        else:
            wind_data = await self.fetch_wind_data(latitude, longitude, days)
            wave_data = None

        return SpotForecast(
            spot_id=spot_id,
            spot_name=spot_name,
            latitude=latitude,
            longitude=longitude,
            wind_data=wind_data,
            wave_data=wave_data,
            fetched_at=datetime.now()
        )

    async def fetch_all_spots_forecast(
        self,
        spots: List[Dict[str, Any]],
        days: int = 3
    ) -> List[SpotForecast]:
        """Fetch forecasts for multiple spots concurrently"""

        tasks = []
        for spot in spots:
            # Kinneret doesn't have marine data
            include_waves = spot["id"] != "kinneret_diamond"

            task = self.fetch_spot_forecast(
                spot_id=spot["id"],
                spot_name=spot["name"],
                latitude=spot["lat"],
                longitude=spot["lon"],
                days=days,
                include_waves=include_waves
            )
            tasks.append(task)

        # Fetch all spots concurrently with some delay to avoid rate limiting
        forecasts = []
        batch_size = 5  # Process 5 spots at a time

        for i in range(0, len(tasks), batch_size):
            batch = tasks[i:i + batch_size]
            batch_results = await asyncio.gather(*batch, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, SpotForecast):
                    forecasts.append(result)
                else:
                    print(f"Error in batch: {result}")

            # Small delay between batches
            if i + batch_size < len(tasks):
                await asyncio.sleep(0.5)

        return forecasts


# Current conditions helper
def get_current_conditions(forecast: SpotForecast) -> Dict[str, Any]:
    """Extract current/nearest hour conditions from forecast"""
    now = datetime.now()

    # Find nearest wind data point
    current_wind = None
    if forecast.wind_data:
        for wind in forecast.wind_data:
            if wind.timestamp >= now:
                current_wind = wind
                break
        if not current_wind and forecast.wind_data:
            current_wind = forecast.wind_data[-1]

    # Find nearest wave data point
    current_wave = None
    if forecast.wave_data:
        for wave in forecast.wave_data:
            if wave.timestamp >= now:
                current_wave = wave
                break
        if not current_wave and forecast.wave_data:
            current_wave = forecast.wave_data[-1]

    return {
        "spot_id": forecast.spot_id,
        "spot_name": forecast.spot_name,
        "wind": {
            "speed_knots": current_wind.wind_speed_knots if current_wind else 0,
            "gusts_knots": current_wind.wind_gusts_knots if current_wind else 0,
            "direction": current_wind.wind_direction if current_wind else 0,
            "direction_cardinal": current_wind.wind_direction_cardinal if current_wind else "N"
        } if current_wind else None,
        "wave": {
            "height_m": current_wave.wave_height_m if current_wave else 0,
            "period_s": current_wave.wave_period_s if current_wave else 0,
            "direction": current_wave.wave_direction if current_wave else 0
        } if current_wave else None,
        "fetched_at": forecast.fetched_at.isoformat()
    }
