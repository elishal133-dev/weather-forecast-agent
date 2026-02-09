"""
Multi-Source Weather Aggregator with Data Validation
Combines data from multiple weather APIs for better accuracy:
- Open-Meteo (free, no API key)
- OpenWeatherMap (free tier, needs API key)
- WeatherAPI (free tier, needs API key)
- Windy (free tier, needs API key)

Includes cross-source validation and anomaly detection.
"""

import asyncio
import logging
import os
import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import httpx

logger = logging.getLogger('multi_weather')


# =============================================================================
# Data Validation Configuration
# =============================================================================

@dataclass
class ValidationConfig:
    """Configuration for data validation thresholds"""
    # Maximum acceptable deviation from median (as multiplier of std dev)
    outlier_threshold: float = 2.0

    # Minimum sources needed for high confidence
    min_sources_high_confidence: int = 3

    # Field-specific reasonable ranges
    field_ranges: Dict[str, Tuple[float, float]] = field(default_factory=lambda: {
        "wind_speed_knots": (0, 100),
        "wind_gusts_knots": (0, 120),
        "temperature_c": (-30, 55),
        "humidity_percent": (0, 100),
        "cloud_cover_percent": (0, 100),
        "visibility_km": (0, 100),
        "precipitation_mm": (0, 100),
        "wind_direction_deg": (0, 360)
    })

    # Maximum acceptable difference between sources for each field
    max_source_diff: Dict[str, float] = field(default_factory=lambda: {
        "wind_speed_knots": 10,      # 10 knots difference acceptable
        "wind_gusts_knots": 15,      # 15 knots for gusts
        "temperature_c": 3,          # 3°C difference
        "humidity_percent": 20,      # 20% humidity difference
        "cloud_cover_percent": 30,   # 30% cloud cover difference
        "visibility_km": 5,          # 5km visibility difference
        "precipitation_mm": 2,       # 2mm precipitation
        "wind_direction_deg": 45     # 45° direction difference
    })


@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    confidence: float  # 0-1
    anomalies: List[str]
    corrections: Dict[str, Any]
    source_agreement: Dict[str, float]  # Field -> agreement score


class DataValidator:
    """
    Cross-source data validation and anomaly detection.
    Compares data from multiple sources to ensure accuracy.
    """

    def __init__(self, config: ValidationConfig = None):
        self.config = config or ValidationConfig()
        self.anomaly_log: List[Dict] = []

    def validate_current(self, results: List['WeatherData']) -> ValidationResult:
        """Validate current weather data from multiple sources"""
        if len(results) < 2:
            return ValidationResult(
                is_valid=True,
                confidence=0.5 if results else 0,
                anomalies=[],
                corrections={},
                source_agreement={}
            )

        anomalies = []
        corrections = {}
        agreement_scores = {}

        # Validate each field
        fields = ["wind_speed_knots", "wind_gusts_knots", "temperature_c",
                  "humidity_percent", "cloud_cover_percent", "visibility_km",
                  "precipitation_mm"]

        for field_name in fields:
            values = [(getattr(r, field_name) or 0, r.source) for r in results
                     if getattr(r, field_name, None) is not None]

            if len(values) < 2:
                continue

            nums = [v[0] for v in values]
            sources = [v[1] for v in values]

            # Check range validity
            min_val, max_val = self.config.field_ranges.get(field_name, (-float('inf'), float('inf')))
            out_of_range = [(n, s) for n, s in values if n < min_val or n > max_val]
            if out_of_range:
                for val, src in out_of_range:
                    anomalies.append(f"{field_name}: {src} reported {val} (out of range {min_val}-{max_val})")

            # Check source agreement
            max_diff = self.config.max_source_diff.get(field_name, float('inf'))
            spread = max(nums) - min(nums)

            if spread > max_diff:
                # Sources disagree significantly
                median = statistics.median(nums)
                anomalies.append(f"{field_name}: sources disagree (spread={spread:.1f}, max allowed={max_diff})")

                # Find outlier sources
                for val, src in values:
                    if abs(val - median) > max_diff:
                        anomalies.append(f"  -> {src} outlier: {val:.1f} (median={median:.1f})")

                # Suggest correction to median
                corrections[field_name] = median

            # Calculate agreement score (0-1)
            if spread <= max_diff:
                agreement_scores[field_name] = 1.0
            else:
                agreement_scores[field_name] = max(0, 1 - (spread / (max_diff * 3)))

        # Wind direction needs special circular handling
        self._validate_wind_direction(results, anomalies, corrections, agreement_scores)

        # Calculate overall confidence
        if not agreement_scores:
            confidence = 0.5
        else:
            confidence = sum(agreement_scores.values()) / len(agreement_scores)

            # Boost confidence if more sources agree
            if len(results) >= self.config.min_sources_high_confidence:
                confidence = min(1.0, confidence * 1.1)

        # Log anomalies
        if anomalies:
            self._log_anomaly({
                "timestamp": datetime.now().isoformat(),
                "type": "current_weather",
                "anomalies": anomalies,
                "sources": [r.source for r in results]
            })

        return ValidationResult(
            is_valid=len(anomalies) == 0,
            confidence=round(confidence, 2),
            anomalies=anomalies,
            corrections=corrections,
            source_agreement=agreement_scores
        )

    def validate_hourly(self, all_data: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """Validate hourly forecast data and return corrected data with anomaly list"""
        from collections import defaultdict

        anomalies = []

        # Group by time
        time_groups = defaultdict(list)
        for item in all_data:
            time_str = item.get("time", "")[:13]  # Group by hour
            time_groups[time_str].append(item)

        corrected_data = []

        for time_key, group in time_groups.items():
            if len(group) < 2:
                corrected_data.extend(group)
                continue

            # Check each field for outliers
            fields = ["wind_speed_knots", "wind_gusts_knots", "temperature_c",
                      "humidity_percent", "cloud_cover_percent"]

            for field_name in fields:
                values = [(item.get(field_name, 0), item.get("source", "unknown"))
                         for item in group if item.get(field_name) is not None]

                if len(values) < 2:
                    continue

                nums = [v[0] for v in values]
                median = statistics.median(nums)

                # Check for outliers
                max_diff = self.config.max_source_diff.get(field_name, float('inf'))
                for val, src in values:
                    if abs(val - median) > max_diff * 1.5:
                        anomalies.append(f"{time_key} {field_name}: {src}={val:.1f} (median={median:.1f})")

            corrected_data.extend(group)

        if anomalies:
            self._log_anomaly({
                "timestamp": datetime.now().isoformat(),
                "type": "hourly_forecast",
                "anomaly_count": len(anomalies),
                "sample_anomalies": anomalies[:10]  # First 10 for log
            })

        return corrected_data, anomalies

    def _validate_wind_direction(self, results: List['WeatherData'],
                                  anomalies: List[str], corrections: Dict,
                                  agreement_scores: Dict):
        """Validate wind direction with circular math"""
        directions = [(r.wind_direction_deg, r.source) for r in results]

        if len(directions) < 2:
            return

        # Calculate circular mean
        x_sum = sum(math.cos(math.radians(d)) for d, _ in directions)
        y_sum = sum(math.sin(math.radians(d)) for d, _ in directions)
        mean_dir = math.degrees(math.atan2(y_sum, x_sum)) % 360

        # Check angular differences
        max_diff = self.config.max_source_diff.get("wind_direction_deg", 45)
        outliers = []

        for deg, src in directions:
            # Calculate angular difference
            diff = abs(((deg - mean_dir + 180) % 360) - 180)
            if diff > max_diff:
                outliers.append((deg, src, diff))

        if outliers:
            anomalies.append(f"wind_direction: sources disagree")
            for deg, src, diff in outliers:
                anomalies.append(f"  -> {src}: {deg}° (diff from mean: {diff:.0f}°)")
            corrections["wind_direction_deg"] = int(mean_dir)
            agreement_scores["wind_direction_deg"] = 0.5
        else:
            agreement_scores["wind_direction_deg"] = 1.0

    def _log_anomaly(self, anomaly: Dict):
        """Log anomaly for monitoring"""
        self.anomaly_log.append(anomaly)
        # Keep only last 100 anomalies
        if len(self.anomaly_log) > 100:
            self.anomaly_log = self.anomaly_log[-100:]

        logger.warning(f"Weather data anomaly detected: {anomaly.get('type')} - {len(anomaly.get('anomalies', []))} issues")

    def get_anomaly_report(self) -> Dict:
        """Get recent anomaly report"""
        return {
            "total_anomalies": len(self.anomaly_log),
            "recent": self.anomaly_log[-10:] if self.anomaly_log else [],
            "generated_at": datetime.now().isoformat()
        }


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
    Includes cross-source validation and anomaly detection.
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
        self.validator = DataValidator()

        enabled = [s.name for s in self.sources if getattr(s, 'enabled', True)]
        logger.info(f"MultiSourceWeather initialized with sources: {enabled}")

    async def close(self):
        await self.client.aclose()

    async def fetch_current(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetch, validate, and combine current weather from all sources"""
        tasks = [source.fetch_current(lat, lon) for source in self.sources]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        valid_results = [r for r in results if isinstance(r, WeatherData)]

        if not valid_results:
            logger.error(f"All weather sources failed for {lat}, {lon}")
            return {}

        # Validate data across sources
        validation = self.validator.validate_current(valid_results)

        combined = self._combine_current(valid_results)

        # Apply corrections if needed
        if validation.corrections:
            for field, value in validation.corrections.items():
                if field in combined:
                    logger.info(f"Applying correction: {field} = {value} (was {combined[field]})")
                    combined[field] = value

        # Add validation metadata
        combined["sources_used"] = [r.source for r in valid_results]
        combined["source_count"] = len(valid_results)
        combined["validation"] = {
            "is_valid": validation.is_valid,
            "confidence": validation.confidence,
            "anomaly_count": len(validation.anomalies),
            "source_agreement": validation.source_agreement
        }

        # Include per-source raw data for transparency
        combined["source_data"] = {
            r.source: {
                "wind_speed_knots": r.wind_speed_knots,
                "wind_direction_deg": r.wind_direction_deg,
                "temperature_c": r.temperature_c
            } for r in valid_results
        }

        return combined

    async def fetch_hourly(self, lat: float, lon: float, hours: int = 24) -> List[Dict]:
        """Fetch, validate, and combine hourly forecast from all sources"""
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

        # Validate hourly data
        validated_data, anomalies = self.validator.validate_hourly(all_hourly)

        if anomalies:
            logger.warning(f"Hourly validation found {len(anomalies)} anomalies")

        # Group by time and combine
        return self._combine_hourly(validated_data, hours)

    def get_validation_report(self) -> Dict:
        """Get validation/anomaly report"""
        return self.validator.get_anomaly_report()

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
