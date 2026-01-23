import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import HourlyForecast
from datetime import datetime, timedelta, time
from typing import List, Dict
import requests

class HourlyScraper:
    """Scraper for hourly/3-hourly weather data from Open-Meteo API"""

    def __init__(self):
        self.source_name = 'open_meteo_hourly'
        self.base_url = 'https://api.open-meteo.com/v1/forecast'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        # Location coordinates for Israeli cities
        self.locations = {
            'Tel Aviv': {'lat': 32.0853, 'lon': 34.7818},
            'Jerusalem': {'lat': 31.7683, 'lon': 35.2137},
            'Haifa': {'lat': 32.7940, 'lon': 34.9896},
            'Beer Sheva': {'lat': 31.2518, 'lon': 34.7913}
        }

    def scrape_hourly(self, location: str, days: int = 7) -> Dict[str, List[HourlyForecast]]:
        """
        Fetch 3-hourly weather forecast from Open-Meteo API
        Returns: Dict mapping date strings to lists of hourly forecasts
        """
        hourly_by_date = {}

        try:
            # Get coordinates for location
            coords = self.locations.get(location, self.locations['Tel Aviv'])

            # API parameters for hourly data
            params = {
                'latitude': coords['lat'],
                'longitude': coords['lon'],
                'hourly': [
                    'temperature_2m',
                    'windspeed_10m',
                    'winddirection_10m',
                    'cloudcover'
                ],
                'timezone': 'Asia/Jerusalem',
                'forecast_days': days
            }

            # Make API request
            response = self.session.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            # Parse hourly forecasts
            hourly = data.get('hourly', {})
            times = hourly.get('time', [])
            temperatures = hourly.get('temperature_2m', [])
            wind_speeds = hourly.get('windspeed_10m', [])
            wind_directions = hourly.get('winddirection_10m', [])
            cloud_covers = hourly.get('cloudcover', [])

            # Process hourly data - take every 3rd hour (00:00, 03:00, 06:00, etc.)
            for i in range(0, len(times), 3):
                try:
                    # Parse datetime
                    dt = datetime.fromisoformat(times[i])
                    date_key = dt.date().isoformat()

                    # Extract data
                    temp = temperatures[i] if i < len(temperatures) else None
                    wind_speed = wind_speeds[i] if i < len(wind_speeds) else None
                    wind_dir_deg = wind_directions[i] if i < len(wind_directions) else None
                    cloud = cloud_covers[i] if i < len(cloud_covers) else None

                    # Convert wind direction
                    wind_dir = self._degrees_to_cardinal(wind_dir_deg) if wind_dir_deg is not None else None

                    # Estimate freezing altitude
                    freezing_alt = self._estimate_freezing_altitude(temp) if temp is not None else None

                    # Create hourly forecast
                    hourly_forecast = HourlyForecast(
                        time=dt,
                        temperature=temp,
                        wind_speed=wind_speed,
                        wind_direction=wind_dir,
                        cloud_cover=cloud,
                        cloud_base=None,  # Will be set from daily data in app.py
                        freezing_altitude=freezing_alt
                    )

                    # Group by date
                    if date_key not in hourly_by_date:
                        hourly_by_date[date_key] = []
                    hourly_by_date[date_key].append(hourly_forecast)

                except Exception as e:
                    print(f"Error parsing hourly data at index {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error fetching hourly data: {e}")

        return hourly_by_date

    def _degrees_to_cardinal(self, degrees: float) -> str:
        """Convert wind direction from degrees to cardinal direction"""
        directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                     'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
        index = round(degrees / 22.5) % 16
        return directions[index]

    def _estimate_freezing_altitude(self, temp_celsius: float) -> float:
        """
        Estimate freezing altitude based on temperature
        Using standard lapse rate: ~6.5°C per 1000m
        """
        if temp_celsius <= 0:
            return 0
        altitude = (temp_celsius / 6.5) * 1000
        return altitude
