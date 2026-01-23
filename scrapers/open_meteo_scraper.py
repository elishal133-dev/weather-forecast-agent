import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base_scraper import BaseScraper
from models import ForecastData
from datetime import datetime, timedelta, time
from typing import List
import requests
from moon_calculator import MoonCalculator

class OpenMeteoScraper(BaseScraper):
    """Scraper for Open-Meteo API (free, no API key required)"""

    def __init__(self):
        super().__init__('open_meteo')
        self.base_url = 'https://api.open-meteo.com/v1/forecast'
        self.moon_calc = MoonCalculator()

        # Location coordinates for Israeli cities
        self.locations = {
            'Tel Aviv': {'lat': 32.0853, 'lon': 34.7818},
            'Jerusalem': {'lat': 31.7683, 'lon': 35.2137},
            'Haifa': {'lat': 32.7940, 'lon': 34.9896},
            'Beer Sheva': {'lat': 31.2518, 'lon': 34.7913}
        }

    def scrape(self, location: str) -> List[ForecastData]:
        """Fetch weather forecast from Open-Meteo API"""
        forecasts = []

        try:
            # Get coordinates for location
            coords = self.locations.get(location, self.locations['Tel Aviv'])

            # API parameters
            params = {
                'latitude': coords['lat'],
                'longitude': coords['lon'],
                'daily': [
                    'temperature_2m_max',
                    'temperature_2m_min',
                    'windspeed_10m_max',
                    'winddirection_10m_dominant',
                    'cloudcover_mean',
                    'sunrise',
                    'sunset'
                ],
                'timezone': 'Asia/Jerusalem',
                'forecast_days': 7
            }

            # Make API request
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse daily forecasts
            daily = data.get('daily', {})
            dates = daily.get('time', [])
            temp_highs = daily.get('temperature_2m_max', [])
            temp_lows = daily.get('temperature_2m_min', [])
            wind_speeds = daily.get('windspeed_10m_max', [])
            wind_directions = daily.get('winddirection_10m_dominant', [])
            cloud_covers = daily.get('cloudcover_mean', [])
            sunrises = daily.get('sunrise', [])
            sunsets = daily.get('sunset', [])

            for i in range(len(dates)):
                try:
                    # Parse date
                    date = datetime.fromisoformat(dates[i])

                    # Parse sunrise/sunset times
                    sunrise = None
                    sunset = None
                    if i < len(sunrises) and sunrises[i]:
                        sunrise_dt = datetime.fromisoformat(sunrises[i])
                        sunrise = sunrise_dt.time()
                    if i < len(sunsets) and sunsets[i]:
                        sunset_dt = datetime.fromisoformat(sunsets[i])
                        sunset = sunset_dt.time()

                    # Convert wind direction from degrees to cardinal
                    wind_dir = None
                    if i < len(wind_directions) and wind_directions[i] is not None:
                        wind_dir = self._degrees_to_cardinal(wind_directions[i])

                    # Estimate freezing altitude (rough calculation)
                    temp_high = temp_highs[i] if i < len(temp_highs) else None
                    freezing_altitude = self._estimate_freezing_altitude(temp_high) if temp_high else None

                    # Calculate moon data
                    moon_data = self.moon_calc.get_moon_data(location, date.date())

                    forecast = ForecastData(
                        source=self.source_name,
                        location=location,
                        date=date,
                        temp_high=temp_highs[i] if i < len(temp_highs) else None,
                        temp_low=temp_lows[i] if i < len(temp_lows) else None,
                        wind_speed=wind_speeds[i] if i < len(wind_speeds) else None,
                        wind_direction=wind_dir,
                        cloud_cover=cloud_covers[i] if i < len(cloud_covers) else None,
                        cloud_min_level=None,  # Not provided by Open-Meteo
                        freezing_altitude=freezing_altitude,
                        sunrise=sunrise,
                        sunset=sunset,
                        moonrise=moon_data['moonrise'],
                        moonset=moon_data['moonset'],
                        moon_illumination=moon_data['moon_illumination']
                    )
                    forecasts.append(forecast)

                except Exception as e:
                    print(f"Error parsing Open-Meteo day {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error fetching Open-Meteo data: {e}")

        return forecasts

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
        # Rough estimate: altitude where temp would be 0°C
        # Assuming sea level temp is the given temperature
        altitude = (temp_celsius / 6.5) * 1000
        return altitude
