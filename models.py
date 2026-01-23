from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, List

@dataclass
class ForecastData:
    """Data model for weather forecast"""
    source: str
    location: str
    date: datetime
    temp_high: Optional[float] = None
    temp_low: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    cloud_cover: Optional[float] = None  # Percentage (0-100)
    cloud_min_level: Optional[float] = None  # Cloud base/ceiling in meters
    freezing_altitude: Optional[float] = None  # Altitude where temperature is 0°C in meters
    sunrise: Optional[time] = None
    sunset: Optional[time] = None
    moonrise: Optional[time] = None
    moonset: Optional[time] = None
    moon_illumination: Optional[float] = None  # Moon phase percentage (0-100)
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def to_dict(self):
        return {
            'source': self.source,
            'location': self.location,
            'date': self.date.strftime('%Y-%m-%d'),
            'temp_high': self.temp_high,
            'temp_low': self.temp_low,
            'wind_speed': self.wind_speed,
            'wind_direction': self.wind_direction,
            'cloud_cover': self.cloud_cover,
            'cloud_min_level': self.cloud_min_level,
            'freezing_altitude': self.freezing_altitude,
            'sunrise': self.sunrise.strftime('%H:%M') if self.sunrise else None,
            'sunset': self.sunset.strftime('%H:%M') if self.sunset else None,
            'moonrise': self.moonrise.strftime('%H:%M') if self.moonrise else None,
            'moonset': self.moonset.strftime('%H:%M') if self.moonset else None,
            'moon_illumination': self.moon_illumination,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        }

@dataclass
class HourlyForecast:
    """Hourly weather forecast data"""
    time: datetime  # Specific hour
    temperature: Optional[float] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    cloud_cover: Optional[float] = None
    cloud_base: Optional[float] = None  # Cloud base altitude in meters
    freezing_altitude: Optional[float] = None

    def to_dict(self):
        return {
            'time': self.time.strftime('%H:%M'),
            'temperature': round(self.temperature, 1) if self.temperature else None,
            'wind_speed': round(self.wind_speed, 1) if self.wind_speed else None,
            'wind_direction': self.wind_direction,
            'cloud_cover': round(self.cloud_cover, 1) if self.cloud_cover else None,
            'cloud_base': round(self.cloud_base, 1) if self.cloud_base else None,
            'freezing_altitude': round(self.freezing_altitude, 1) if self.freezing_altitude else None
        }

@dataclass
class AggregatedForecast:
    """Aggregated forecast from multiple sources"""
    location: str
    date: datetime
    temp_high: float
    temp_low: float
    wind_speed: float
    wind_direction: str
    cloud_cover: float
    cloud_min_level: Optional[float]
    freezing_altitude: Optional[float]
    sunrise: time
    sunset: time
    moonrise: time
    moonset: time
    moon_illumination: float
    confidence: float  # 0-100%
    sources_used: list
    hourly_data: Optional[List[HourlyForecast]] = None  # 3-hourly forecasts

    def to_dict(self):
        result = {
            'location': self.location,
            'date': self.date.strftime('%Y-%m-%d'),
            'temp_high': round(self.temp_high, 1),
            'temp_low': round(self.temp_low, 1),
            'wind_speed': round(self.wind_speed, 1),
            'wind_direction': self.wind_direction,
            'cloud_cover': round(self.cloud_cover, 1),
            'cloud_min_level': round(self.cloud_min_level, 1) if self.cloud_min_level else None,
            'freezing_altitude': round(self.freezing_altitude, 1) if self.freezing_altitude else None,
            'sunrise': self.sunrise.strftime('%H:%M'),
            'sunset': self.sunset.strftime('%H:%M'),
            'moonrise': self.moonrise.strftime('%H:%M'),
            'moonset': self.moonset.strftime('%H:%M'),
            'moon_illumination': round(self.moon_illumination, 1),
            'confidence': round(self.confidence, 1),
            'sources_used': self.sources_used
        }
        if self.hourly_data:
            result['hourly'] = [h.to_dict() for h in self.hourly_data]
        return result
