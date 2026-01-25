from dataclasses import dataclass
from datetime import datetime, time
from typing import Optional, List

def validate_temperature(temp: Optional[float]) -> Optional[float]:
    """
    Validate temperature values to filter out unrealistic data.
    Returns None if temperature is outside reasonable range:
    - Below -70°C (coldest ever recorded on Earth: -89.2°C)
    - Above 65°C (hottest ever recorded: 56.7°C)
    This helps filter out data scraping errors and display N/A for invalid values.
    """
    if temp is None:
        return None
    if temp < -70 or temp > 65:
        return None
    return temp

@dataclass
class ForecastData:
    """Data model for weather forecast"""
    source: str
    location: str
    date: datetime
    temp_high: Optional[float] = None
    temp_low: Optional[float] = None
    feels_like_high: Optional[float] = None
    feels_like_low: Optional[float] = None
    precipitation_prob: Optional[float] = None  # Percentage (0-100)
    humidity: Optional[float] = None  # Percentage (0-100)
    weather_condition: Optional[str] = None  # e.g., "Clear", "Cloudy", "Rain"
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
            'temp_high': validate_temperature(self.temp_high),
            'temp_low': validate_temperature(self.temp_low),
            'feels_like_high': validate_temperature(self.feels_like_high),
            'feels_like_low': validate_temperature(self.feels_like_low),
            'precipitation_prob': self.precipitation_prob,
            'humidity': self.humidity,
            'weather_condition': self.weather_condition,
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
    feels_like: Optional[float] = None
    precipitation_prob: Optional[float] = None
    humidity: Optional[float] = None
    weather_condition: Optional[str] = None
    wind_speed: Optional[float] = None
    wind_direction: Optional[str] = None
    cloud_cover: Optional[float] = None
    cloud_base: Optional[float] = None  # Cloud base altitude in meters
    freezing_altitude: Optional[float] = None

    def to_dict(self):
        # Validate and round temperature values
        temp = validate_temperature(self.temperature)
        feels = validate_temperature(self.feels_like)

        return {
            'time': self.time.strftime('%H:%M'),
            'temperature': round(temp, 1) if temp is not None else None,
            'feels_like': round(feels, 1) if feels is not None else None,
            'precipitation_prob': round(self.precipitation_prob, 1) if self.precipitation_prob else None,
            'humidity': round(self.humidity, 1) if self.humidity else None,
            'weather_condition': self.weather_condition,
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
    feels_like_high: Optional[float] = None
    feels_like_low: Optional[float] = None
    precipitation_prob: Optional[float] = None
    humidity: Optional[float] = None
    weather_condition: Optional[str] = None
    wind_speed: float = 0
    wind_direction: str = ""
    cloud_cover: float = 0
    cloud_min_level: Optional[float] = None
    freezing_altitude: Optional[float] = None
    sunrise: time = None
    sunset: time = None
    moonrise: time = None
    moonset: time = None
    moon_illumination: float = 0
    confidence: float = 0  # 0-100%
    sources_used: list = None
    hourly_data: Optional[List[HourlyForecast]] = None  # 3-hourly forecasts

    def to_dict(self):
        # Validate all temperature values
        temp_high = validate_temperature(self.temp_high)
        temp_low = validate_temperature(self.temp_low)
        feels_high = validate_temperature(self.feels_like_high)
        feels_low = validate_temperature(self.feels_like_low)

        result = {
            'location': self.location,
            'date': self.date.strftime('%Y-%m-%d'),
            'temp_high': round(temp_high, 1) if temp_high is not None else None,
            'temp_low': round(temp_low, 1) if temp_low is not None else None,
            'feels_like_high': round(feels_high, 1) if feels_high is not None else None,
            'feels_like_low': round(feels_low, 1) if feels_low is not None else None,
            'precipitation_prob': round(self.precipitation_prob, 1) if self.precipitation_prob else None,
            'humidity': round(self.humidity, 1) if self.humidity else None,
            'weather_condition': self.weather_condition,
            'wind_speed': round(self.wind_speed, 1),
            'wind_direction': self.wind_direction,
            'cloud_cover': round(self.cloud_cover, 1),
            'cloud_min_level': round(self.cloud_min_level, 1) if self.cloud_min_level else None,
            'freezing_altitude': round(self.freezing_altitude, 1) if self.freezing_altitude else None,
            'sunrise': self.sunrise.strftime('%H:%M') if self.sunrise else None,
            'sunset': self.sunset.strftime('%H:%M') if self.sunset else None,
            'moonrise': self.moonrise.strftime('%H:%M') if self.moonrise else None,
            'moonset': self.moonset.strftime('%H:%M') if self.moonset else None,
            'moon_illumination': round(self.moon_illumination, 1),
            'confidence': round(self.confidence, 1),
            'sources_used': self.sources_used if self.sources_used else []
        }
        if self.hourly_data:
            result['hourly'] = [h.to_dict() for h in self.hourly_data]
        return result
