"""
Multi-Source Weather Aggregator
Combines data from multiple weather APIs for better accuracy:
- Open-Meteo (free, no API key)
- OpenWeatherMap (free tier, needs API key)
- WeatherAPI (free tier, needs API key)
"""

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import httpx

logger = logging.getLogger('multi_weather')


@dataclass
class WeatherData:
    """Unified weather data structure"""
    source: str
    timestamp: datetime
    wind_speed_knots: float
    wind_gusts_knots: Optional[float]
    wind_direction_deg: int
    temperature_c: float
    humidity_percent: int
    cloud_cover_percent: int
    visibility_km: float
    precipitation_mm: float
    pressure_hpa: Optional[float] = None
    dewpoint_c: Optional[float] = None


class OpenMeteoSource:
    """Open-Meteo API - Free, no API key needed"""

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.name = "open_meteo"

    async def fetch_current(self, lat: float, lon: float) -> Optional[WeatherData]:
        """Fetch current weather from Open-Meteo"""
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "current": "temperature_2m,relative_humidity_2m,precipitation,cloud_cover,wind_speed_10m,wind_direction_10m,wind_gusts_10m,pressure_msl",
                "wind_speed_unit": "kn",
                "timezone": "auto"
            }

            resp = await self.client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            current = data.get("current", {})

            return WeatherData(
                source=self.name,
                timestamp=datetime.now(),
                wind_speed_knots=current.get("wind_speed_10m", 0) or 0,
                wind_gusts_knots=current.get("wind_gusts_10m"),
                wind_direction_deg=int(current.get("wind_direction_10m", 0) or 0),
                temperature_c=current.get("temperature_2m", 20) or 20,
                humidity_percent=int(current.get("relative_humidity_2m", 50) or 50),
                cloud_cover_percent=int(current.get("cloud_cover", 0) or 0),
                visibility_km=50.0,  # Open-Meteo doesn't provide visibility in current
                precipitation_mm=current.get("precipitation", 0) or 0,
                pressure_hpa=current.get("pressure_msl")
            )
        except Exception as e:
            logger.warning(f"Open-Meteo fetch failed: {e}")
            return None

    async def fetch_hourly(self, lat: float, lon: float, hours: int = 24) -> List[Dict]:
        """Fetch hourly forecast from Open-Meteo"""
        try:
            params = {
                "latitude": lat,
                "longitude": lon,
                "hourly": "temperature_2m,relative_humidity_2m,dewpoint_2m,precipitation,cloud_cover,visibility,wind_speed_10m,wind_direction_10m,wind_gusts_10m",
                "wind_speed_unit": "kn",
                "timezone": "auto",
                "forecast_hours": hours
            }

            resp = await self.client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            data = resp.json()

            hourly = data.get("hourly", {})
            times = hourly.get("time", [])

            result = []
            for i, time_str in enumerate(times[:hours]):
                result.append({
                    "source": self.name,
                    "time": time_str,
                    "wind_speed_knots": hourly.get("wind_speed_10m", [])[i] or 0,
                    "wind_gusts_knots": hourly.get("wind_gusts_10m", [])[i] or 0,
                    "wind_direction_deg": hourly.get("wind_direction_10m", [])[i] or 0,
                    "temperature_c": hourly.get("temperature_2m", [])[i] or 20,
                    "humidity_percent": hourly.get("relative_humidity_2m", [])[i] or 50,
                    "cloud_cover_percent": hourly.get("cloud_cover", [])[i] or 0,
                    "visibility_km": (hourly.get("visibility", [])[i] or 50000) / 1000,
                    "precipitation_mm": hourly.get("precipitation", [])[i] or 0,
                    "dewpoint_c": hourly.get("dewpoint_2m", [])[i]
                })

            return result
        except Exception as e:
            logger.warning(f"Open-Meteo hourly fetch failed: {e}")
            return []


class OpenWeatherMapSource:
    """OpenWeatherMap API - Free tier (1000 calls/day)"""

    BASE_URL = "https://api.openweathermap.org/data/2.5"

    def __init__(self, client: httpx.AsyncClient, api_key: Optional[str] = None):
        self.client = client
        self.api_key = api_key or os.environ.get("OPENWEATHERMAP_API_KEY")
        self.name = "openweathermap"
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.info("OpenWeatherMap: No API key found, source disabled")

    def _ms_to_knots(self, ms: float) -> float:
        """Convert m/s to knots"""
        return ms * 1.94384

    async def fetch_current(self, lat: float, lon: float) -> Optional[WeatherData]:
        """Fetch current weather from OpenWeatherMap"""
        if not self.enabled:
            return None

        try:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric"
            }

            resp = await self.client.get(f"{self.BASE_URL}/weather", params=params)
            resp.raise_for_status()
            data = resp.json()

            wind = data.get("wind", {})
            main = data.get("main", {})
            clouds = data.get("clouds", {})
            rain = data.get("rain", {})

            return WeatherData(
                source=self.name,
                timestamp=datetime.now(),
                wind_speed_knots=self._ms_to_knots(wind.get("speed", 0)),
                wind_gusts_knots=self._ms_to_knots(wind.get("gust", 0)) if wind.get("gust") else None,
                wind_direction_deg=int(wind.get("deg", 0)),
                temperature_c=main.get("temp", 20),
                humidity_percent=int(main.get("humidity", 50)),
                cloud_cover_percent=int(clouds.get("all", 0)),
                visibility_km=(data.get("visibility", 10000) or 10000) / 1000,
                precipitation_mm=rain.get("1h", 0),
                pressure_hpa=main.get("pressure"),
                dewpoint_c=self._calc_dewpoint(main.get("temp", 20), main.get("humidity", 50))
            )
        except Exception as e:
            logger.warning(f"OpenWeatherMap fetch failed: {e}")
            return None

    async def fetch_hourly(self, lat: float, lon: float, hours: int = 24) -> List[Dict]:
        """Fetch hourly forecast from OpenWeatherMap (5 day / 3 hour forecast)"""
        if not self.enabled:
            return []

        try:
            params = {
                "lat": lat,
                "lon": lon,
                "appid": self.api_key,
                "units": "metric",
                "cnt": min(hours // 3 + 1, 40)  # 3-hour intervals, max 5 days
            }

            resp = await self.client.get(f"{self.BASE_URL}/forecast", params=params)
            resp.raise_for_status()
            data = resp.json()

            result = []
            for item in data.get("list", []):
                wind = item.get("wind", {})
                main = item.get("main", {})
                clouds = item.get("clouds", {})
                rain = item.get("rain", {})

                result.append({
                    "source": self.name,
                    "time": item.get("dt_txt"),
                    "wind_speed_knots": self._ms_to_knots(wind.get("speed", 0)),
                    "wind_gusts_knots": self._ms_to_knots(wind.get("gust", 0)) if wind.get("gust") else 0,
                    "wind_direction_deg": wind.get("deg", 0),
                    "temperature_c": main.get("temp", 20),
                    "humidity_percent": main.get("humidity", 50),
                    "cloud_cover_percent": clouds.get("all", 0),
                    "visibility_km": (item.get("visibility", 10000) or 10000) / 1000,
                    "precipitation_mm": rain.get("3h", 0) / 3,  # Convert 3h to hourly
                    "dewpoint_c": self._calc_dewpoint(main.get("temp", 20), main.get("humidity", 50))
                })

            return result
        except Exception as e:
            logger.warning(f"OpenWeatherMap hourly fetch failed: {e}")
            return []

    def _calc_dewpoint(self, temp: float, humidity: float) -> float:
        """Calculate dewpoint from temperature and humidity"""
        import math
        a, b = 17.27, 237.7
        alpha = ((a * temp) / (b + temp)) + math.log(humidity / 100.0)
        return (b * alpha) / (a - alpha)


class WeatherAPISource:
    """WeatherAPI.com - Free tier (1M calls/month)"""

    BASE_URL = "https://api.weatherapi.com/v1"

    def __init__(self, client: httpx.AsyncClient, api_key: Optional[str] = None):
        self.client = client
        self.api_key = api_key or os.environ.get("WEATHERAPI_KEY")
        self.name = "weatherapi"
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.info("WeatherAPI: No API key found, source disabled")

    def _kph_to_knots(self, kph: float) -> float:
        """Convert km/h to knots"""
        return kph * 0.539957

    async def fetch_current(self, lat: float, lon: float) -> Optional[WeatherData]:
        """Fetch current weather from WeatherAPI"""
        if not self.enabled:
            return None

        try:
            params = {
                "key": self.api_key,
                "q": f"{lat},{lon}",
                "aqi": "no"
            }

            resp = await self.client.get(f"{self.BASE_URL}/current.json", params=params)
            resp.raise_for_status()
            data = resp.json()

            current = data.get("current", {})

            return WeatherData(
                source=self.name,
                timestamp=datetime.now(),
                wind_speed_knots=self._kph_to_knots(current.get("wind_kph", 0)),
                wind_gusts_knots=self._kph_to_knots(current.get("gust_kph", 0)),
                wind_direction_deg=int(current.get("wind_degree", 0)),
                temperature_c=current.get("temp_c", 20),
                humidity_percent=int(current.get("humidity", 50)),
                cloud_cover_percent=int(current.get("cloud", 0)),
                visibility_km=current.get("vis_km", 10),
                precipitation_mm=current.get("precip_mm", 0),
                pressure_hpa=current.get("pressure_mb"),
                dewpoint_c=current.get("dewpoint_c")
            )
        except Exception as e:
            logger.warning(f"WeatherAPI fetch failed: {e}")
            return None

    async def fetch_hourly(self, lat: float, lon: float, hours: int = 24) -> List[Dict]:
        """Fetch hourly forecast from WeatherAPI"""
        if not self.enabled:
            return []

        try:
            days = (hours // 24) + 1
            params = {
                "key": self.api_key,
                "q": f"{lat},{lon}",
                "days": min(days, 3),  # Free tier: max 3 days
                "aqi": "no"
            }

            resp = await self.client.get(f"{self.BASE_URL}/forecast.json", params=params)
            resp.raise_for_status()
            data = resp.json()

            result = []
            for day in data.get("forecast", {}).get("forecastday", []):
                for hour in day.get("hour", []):
                    result.append({
                        "source": self.name,
                        "time": hour.get("time"),
                        "wind_speed_knots": self._kph_to_knots(hour.get("wind_kph", 0)),
                        "wind_gusts_knots": self._kph_to_knots(hour.get("gust_kph", 0)),
                        "wind_direction_deg": hour.get("wind_degree", 0),
                        "temperature_c": hour.get("temp_c", 20),
                        "humidity_percent": hour.get("humidity", 50),
                        "cloud_cover_percent": hour.get("cloud", 0),
                        "visibility_km": hour.get("vis_km", 10),
                        "precipitation_mm": hour.get("precip_mm", 0),
                        "dewpoint_c": hour.get("dewpoint_c")
                    })

            return result[:hours]
        except Exception as e:
            logger.warning(f"WeatherAPI hourly fetch failed: {e}")
            return []


class WindySource:
    """Windy API - Point Forecast API (free tier available)"""

    BASE_URL = "https://api.windy.com/api/point-forecast/v2"

    def __init__(self, client: httpx.AsyncClient, api_key: Optional[str] = None):
        self.client = client
        self.api_key = api_key or os.environ.get("WINDY_API_KEY")
        self.name = "windy"
        self.enabled = bool(self.api_key)

        if not self.enabled:
            logger.info("Windy: No API key found, source disabled")

    def _ms_to_knots(self, ms: float) -> float:
        """Convert m/s to knots"""
        return ms * 1.94384

    async def fetch_current(self, lat: float, lon: float) -> Optional[WeatherData]:
        """Fetch current weather from Windy"""
        if not self.enabled:
            return None

        try:
            payload = {
                "lat": lat,
                "lon": lon,
                "model": "gfs",  # Global Forecast System
                "parameters": ["wind", "windGust", "temp", "rh", "pressure", "cloudcover", "visibility", "precip"],
                "levels": ["surface"],
                "key": self.api_key
            }

            resp = await self.client.post(self.BASE_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            # Get first timestamp data (current)
            ts = data.get("ts", [])
            if not ts:
                return None

            # Extract values at first time index
            wind_u = data.get("wind_u-surface", [0])[0]
            wind_v = data.get("wind_v-surface", [0])[0]
            import math
            wind_speed = math.sqrt(wind_u**2 + wind_v**2)
            wind_dir = (math.degrees(math.atan2(-wind_u, -wind_v)) + 360) % 360

            return WeatherData(
                source=self.name,
                timestamp=datetime.now(),
                wind_speed_knots=self._ms_to_knots(wind_speed),
                wind_gusts_knots=self._ms_to_knots(data.get("gust-surface", [0])[0] or wind_speed),
                wind_direction_deg=int(wind_dir),
                temperature_c=data.get("temp-surface", [293])[0] - 273.15,  # Kelvin to Celsius
                humidity_percent=int(data.get("rh-surface", [50])[0] or 50),
                cloud_cover_percent=int(data.get("cloudcover-surface", [0])[0] or 0),
                visibility_km=(data.get("visibility-surface", [10000])[0] or 10000) / 1000,
                precipitation_mm=data.get("precip-surface", [0])[0] or 0,
                pressure_hpa=data.get("pressure-surface", [None])[0]
            )
        except Exception as e:
            logger.warning(f"Windy fetch failed: {e}")
            return None

    async def fetch_hourly(self, lat: float, lon: float, hours: int = 24) -> List[Dict]:
        """Fetch hourly forecast from Windy"""
        if not self.enabled:
            return []

        try:
            payload = {
                "lat": lat,
                "lon": lon,
                "model": "gfs",
                "parameters": ["wind", "windGust", "temp", "rh", "dewpoint", "cloudcover", "visibility", "precip"],
                "levels": ["surface"],
                "key": self.api_key
            }

            resp = await self.client.post(self.BASE_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            ts = data.get("ts", [])
            result = []

            import math
            for i, timestamp in enumerate(ts[:hours]):
                wind_u = data.get("wind_u-surface", [])[i] if i < len(data.get("wind_u-surface", [])) else 0
                wind_v = data.get("wind_v-surface", [])[i] if i < len(data.get("wind_v-surface", [])) else 0
                wind_speed = math.sqrt(wind_u**2 + wind_v**2)
                wind_dir = (math.degrees(math.atan2(-wind_u, -wind_v)) + 360) % 360

                gust = data.get("gust-surface", [])[i] if i < len(data.get("gust-surface", [])) else wind_speed
                temp_k = data.get("temp-surface", [])[i] if i < len(data.get("temp-surface", [])) else 293
                rh = data.get("rh-surface", [])[i] if i < len(data.get("rh-surface", [])) else 50
                cloud = data.get("cloudcover-surface", [])[i] if i < len(data.get("cloudcover-surface", [])) else 0
                vis = data.get("visibility-surface", [])[i] if i < len(data.get("visibility-surface", [])) else 10000
                precip = data.get("precip-surface", [])[i] if i < len(data.get("precip-surface", [])) else 0
                dewpoint_k = data.get("dewpoint-surface", [])[i] if i < len(data.get("dewpoint-surface", [])) else None

                result.append({
                    "source": self.name,
                    "time": datetime.fromtimestamp(timestamp / 1000).isoformat(),
                    "wind_speed_knots": self._ms_to_knots(wind_speed),
                    "wind_gusts_knots": self._ms_to_knots(gust or wind_speed),
                    "wind_direction_deg": int(wind_dir),
                    "temperature_c": temp_k - 273.15,
                    "humidity_percent": int(rh or 50),
                    "cloud_cover_percent": int(cloud or 0),
                    "visibility_km": (vis or 10000) / 1000,
                    "precipitation_mm": precip or 0,
                    "dewpoint_c": (dewpoint_k - 273.15) if dewpoint_k else None
                })

            return result
        except Exception as e:
            logger.warning(f"Windy hourly fetch failed: {e}")
            return []


class MultiSourceWeather:
    """
    Aggregates weather data from multiple sources for better accuracy.
    Uses weighted averaging based on source reliability.
    """

    # Source weights (higher = more trusted)
    SOURCE_WEIGHTS = {
        "open_meteo": 1.0,      # Good baseline, always available
        "openweathermap": 1.2,  # Generally reliable
        "weatherapi": 1.1,      # Good coverage
        "windy": 1.3            # High quality forecast data
    }

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)
        self.sources = [
            OpenMeteoSource(self.client),
            OpenWeatherMapSource(self.client),
            WeatherAPISource(self.client),
            WindySource(self.client)
        ]

        enabled = [s.name for s in self.sources if getattr(s, 'enabled', True)]
        logger.info(f"MultiSourceWeather initialized with sources: {enabled}")

    async def close(self):
        await self.client.aclose()

    async def fetch_current(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch and combine current weather from all sources"""
        tasks = [source.fetch_current(lat, lon) for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = [r for r in results if isinstance(r, WeatherData)]

        if not valid_results:
            logger.error(f"All weather sources failed for {lat}, {lon}")
            return {}

        combined = self._combine_current(valid_results)
        combined["sources_used"] = [r.source for r in valid_results]
        combined["source_count"] = len(valid_results)

        return combined

    async def fetch_hourly(self, lat: float, lon: float, hours: int = 24) -> List[Dict]:
        """Fetch and combine hourly forecast from all sources"""
        tasks = [source.fetch_hourly(lat, lon, hours) for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Collect valid results
        all_hourly = []
        for result in results:
            if isinstance(result, list) and result:
                all_hourly.extend(result)

        if not all_hourly:
            logger.warning(f"No hourly data from any source for {lat}, {lon}")
            return []

        # Group by time and combine
        return self._combine_hourly(all_hourly, hours)

    def _combine_current(self, results: List[WeatherData]) -> Dict[str, Any]:
        """Combine current weather data using weighted averaging"""
        total_weight = 0
        combined = {
            "wind_speed_knots": 0,
            "wind_gusts_knots": 0,
            "wind_direction_deg": 0,
            "temperature_c": 0,
            "humidity_percent": 0,
            "cloud_cover_percent": 0,
            "visibility_km": 0,
            "precipitation_mm": 0
        }

        # Wind direction needs special handling (circular average)
        wind_x, wind_y = 0, 0

        for data in results:
            weight = self.SOURCE_WEIGHTS.get(data.source, 1.0)
            total_weight += weight

            combined["wind_speed_knots"] += data.wind_speed_knots * weight
            combined["wind_gusts_knots"] += (data.wind_gusts_knots or data.wind_speed_knots) * weight
            combined["temperature_c"] += data.temperature_c * weight
            combined["humidity_percent"] += data.humidity_percent * weight
            combined["cloud_cover_percent"] += data.cloud_cover_percent * weight
            combined["visibility_km"] += data.visibility_km * weight
            combined["precipitation_mm"] += data.precipitation_mm * weight

            # Circular average for wind direction
            import math
            rad = math.radians(data.wind_direction_deg)
            wind_x += math.cos(rad) * weight
            wind_y += math.sin(rad) * weight

        if total_weight > 0:
            for key in combined:
                combined[key] = round(combined[key] / total_weight, 1)

            # Calculate average wind direction
            import math
            combined["wind_direction_deg"] = int(math.degrees(math.atan2(wind_y, wind_x))) % 360

            # Integer fields
            combined["humidity_percent"] = int(combined["humidity_percent"])
            combined["cloud_cover_percent"] = int(combined["cloud_cover_percent"])

        combined["timestamp"] = datetime.now().isoformat()

        return combined

    def _combine_hourly(self, all_data: List[Dict], hours: int) -> List[Dict]:
        """Combine hourly data from multiple sources"""
        from collections import defaultdict

        # Group by approximate time (within same hour)
        time_groups = defaultdict(list)
        for item in all_data:
            time_str = item.get("time", "")
            # Normalize time to hour
            if "T" in time_str:
                hour_key = time_str[:13]  # "2024-01-01T12"
            else:
                hour_key = time_str[:13] if len(time_str) >= 13 else time_str
            time_groups[hour_key].append(item)

        # Sort by time and combine each group
        sorted_times = sorted(time_groups.keys())
        result = []

        for time_key in sorted_times[:hours]:
            group = time_groups[time_key]
            if not group:
                continue

            combined = self._average_group(group)
            combined["time"] = time_key + ":00" if len(time_key) == 13 else group[0]["time"]
            combined["sources"] = list(set(item["source"] for item in group))
            result.append(combined)

        return result

    def _average_group(self, group: List[Dict]) -> Dict:
        """Average a group of hourly data points"""
        import math

        fields = ["wind_speed_knots", "wind_gusts_knots", "temperature_c",
                  "humidity_percent", "cloud_cover_percent", "visibility_km", "precipitation_mm"]

        combined = {}
        wind_x, wind_y = 0, 0
        total_weight = 0

        for item in group:
            weight = self.SOURCE_WEIGHTS.get(item.get("source", ""), 1.0)
            total_weight += weight

            for field in fields:
                val = item.get(field, 0) or 0
                combined[field] = combined.get(field, 0) + val * weight

            # Wind direction circular average
            deg = item.get("wind_direction_deg", 0) or 0
            rad = math.radians(deg)
            wind_x += math.cos(rad) * weight
            wind_y += math.sin(rad) * weight

        if total_weight > 0:
            for field in fields:
                combined[field] = round(combined[field] / total_weight, 1)

            combined["wind_direction_deg"] = int(math.degrees(math.atan2(wind_y, wind_x))) % 360
            combined["humidity_percent"] = int(combined["humidity_percent"])
            combined["cloud_cover_percent"] = int(combined["cloud_cover_percent"])

        # Include dewpoint if available
        dewpoints = [item.get("dewpoint_c") for item in group if item.get("dewpoint_c") is not None]
        if dewpoints:
            combined["dewpoint_c"] = round(sum(dewpoints) / len(dewpoints), 1)

        return combined


# Global instance
multi_weather = MultiSourceWeather()
