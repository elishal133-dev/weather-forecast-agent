import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base_scraper import BaseScraper
from models import ForecastData
from datetime import datetime, time
from typing import List
import requests

class OpenWeatherScraper(BaseScraper):
    """Scraper for OpenWeatherMap API (requires API key)"""

    def __init__(self, api_key: str = None):
        super().__init__('openweather')
        self.base_url = 'https://api.openweathermap.org/data/2.5/forecast'
        self.api_key = api_key or os.environ.get('OPENWEATHER_KEY', '')

        # Location coordinates for Israeli cities
        self.locations = {
            'Tel Aviv': {'lat': 32.0853, 'lon': 34.7818},
            'Jerusalem': {'lat': 31.7683, 'lon': 35.2137},
            'Haifa': {'lat': 32.7940, 'lon': 34.9896},
            'Beer Sheva': {'lat': 31.2518, 'lon': 34.7913}
        }

    def scrape(self, location: str) -> List[ForecastData]:
        """Fetch weather forecast from OpenWeatherMap API"""
        forecasts = []

        # Skip if no API key
        if not self.api_key:
            print(f"OpenWeatherMap: No API key configured. Skipping {self.source_name}.")
            print("To enable: Set OPENWEATHER_KEY environment variable or add to config.")
            return forecasts

        try:
            # Get coordinates for location
            coords = self.locations.get(location, self.locations['Tel Aviv'])

            # API parameters
            params = {
                'lat': coords['lat'],
                'lon': coords['lon'],
                'appid': self.api_key,
                'units': 'metric',
                'cnt': 40  # 5 days of 3-hour forecasts
            }

            # Make API request
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Group 3-hour forecasts by day
            daily_data = {}
            for item in data.get('list', []):
                dt = datetime.fromtimestamp(item['dt'])
                date_key = dt.date()

                if date_key not in daily_data:
                    daily_data[date_key] = {
                        'temps': [],
                        'wind_speeds': [],
                        'wind_dirs': [],
                        'clouds': [],
                        'sunrise': None,
                        'sunset': None
                    }

                daily_data[date_key]['temps'].append(item['main']['temp'])
                daily_data[date_key]['wind_speeds'].append(item['wind']['speed'])
                daily_data[date_key]['wind_dirs'].append(item['wind'].get('deg', 0))
                daily_data[date_key]['clouds'].append(item['clouds']['all'])

            # Get sunrise/sunset from city data (same for all days, approximately)
            city_data = data.get('city', {})
            sunrise_ts = city_data.get('sunrise')
            sunset_ts = city_data.get('sunset')

            # Create daily forecasts
            for date_key, day_data in sorted(daily_data.items()):
                try:
                    temps = day_data['temps']
                    temp_high = max(temps) if temps else None
                    temp_low = min(temps) if temps else None

                    # Average wind
                    wind_speeds = day_data['wind_speeds']
                    wind_speed = max(wind_speeds) if wind_speeds else None

                    # Most common wind direction
                    wind_dirs = day_data['wind_dirs']
                    avg_wind_dir = sum(wind_dirs) / len(wind_dirs) if wind_dirs else 0
                    wind_direction = self._degrees_to_cardinal(avg_wind_dir)

                    # Average cloud cover
                    clouds = day_data['clouds']
                    cloud_cover = sum(clouds) / len(clouds) if clouds else None

                    # Sunrise/sunset
                    sunrise = datetime.fromtimestamp(sunrise_ts).time() if sunrise_ts else None
                    sunset = datetime.fromtimestamp(sunset_ts).time() if sunset_ts else None

                    # Estimate freezing altitude
                    freezing_altitude = self._estimate_freezing_altitude(temp_high) if temp_high else None

                    forecast = ForecastData(
                        source=self.source_name,
                        location=location,
                        date=datetime.combine(date_key, time()),
                        temp_high=temp_high,
                        temp_low=temp_low,
                        wind_speed=wind_speed,
                        wind_direction=wind_direction,
                        cloud_cover=cloud_cover,
                        cloud_min_level=None,  # Not provided
                        freezing_altitude=freezing_altitude,
                        sunrise=sunrise,
                        sunset=sunset,
                        moonrise=None,  # Not provided in free tier
                        moonset=None,  # Not provided in free tier
                        moon_illumination=None  # Not provided in free tier
                    )
                    forecasts.append(forecast)

                except Exception as e:
                    print(f"Error parsing OpenWeather day: {e}")
                    continue

        except Exception as e:
            print(f"Error fetching OpenWeather data: {e}")

        return forecasts

    def _degrees_to_cardinal(self, degrees: float) -> str:
        """Convert wind direction from degrees to cardinal direction"""
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                     'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        index = round(degrees / 22.5) % 16
        return directions[index]

    def _estimate_freezing_altitude(self, temp_celsius: float) -> float:
        """Estimate freezing altitude (same as Open-Meteo)"""
        if temp_celsius <= 0:
            return 0
        altitude = (temp_celsius / 6.5) * 1000
        return altitude
