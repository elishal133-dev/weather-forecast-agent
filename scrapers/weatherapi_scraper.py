import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base_scraper import BaseScraper
from models import ForecastData
from datetime import datetime, time
from typing import List
import requests

class WeatherAPIScraper(BaseScraper):
    """Scraper for WeatherAPI.com (requires API key)"""

    def __init__(self, api_key: str = None):
        super().__init__('weatherapi')
        self.base_url = 'https://api.weatherapi.com/v1/forecast.json'
        self.api_key = api_key or os.environ.get('WEATHERAPI_KEY', '')

        # Location names for WeatherAPI
        self.locations = {
            'Tel Aviv': 'Tel Aviv,Israel',
            'Jerusalem': 'Jerusalem,Israel',
            'Haifa': 'Haifa,Israel',
            'Beer Sheva': 'Beersheba,Israel'
        }

    def scrape(self, location: str) -> List[ForecastData]:
        """Fetch weather forecast from WeatherAPI.com"""
        forecasts = []

        # Skip if no API key
        if not self.api_key:
            print(f"WeatherAPI: No API key configured. Skipping {self.source_name}.")
            print("To enable: Set WEATHERAPI_KEY environment variable or add to config.")
            return forecasts

        try:
            # Get location query string
            location_query = self.locations.get(location, 'Tel Aviv,Israel')

            # API parameters
            params = {
                'key': self.api_key,
                'q': location_query,
                'days': 7,
                'aqi': 'no',
                'alerts': 'no'
            }

            # Make API request
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Parse forecast days
            forecast_days = data.get('forecast', {}).get('forecastday', [])

            for day_data in forecast_days:
                try:
                    # Parse date
                    date = datetime.strptime(day_data['date'], '%Y-%m-%d')

                    # Day data
                    day = day_data.get('day', {})
                    astro = day_data.get('astro', {})

                    # Parse times
                    sunrise = self.parse_time(astro.get('sunrise', ''))
                    sunset = self.parse_time(astro.get('sunset', ''))
                    moonrise = self.parse_time(astro.get('moonrise', ''))
                    moonset = self.parse_time(astro.get('moonset', ''))

                    # Wind direction
                    wind_dir = None
                    if day_data.get('hour'):
                        # Get most common wind direction from hourly data
                        wind_dir = day_data['hour'][12].get('wind_dir', 'N')  # Use noon wind

                    # Estimate freezing altitude
                    temp_high = day.get('maxtemp_c')
                    freezing_altitude = self._estimate_freezing_altitude(temp_high) if temp_high else None

                    forecast = ForecastData(
                        source=self.source_name,
                        location=location,
                        date=date,
                        temp_high=day.get('maxtemp_c'),
                        temp_low=day.get('mintemp_c'),
                        wind_speed=day.get('maxwind_kph'),
                        wind_direction=wind_dir,
                        cloud_cover=day.get('avgvis_km'),  # Using visibility as proxy
                        cloud_min_level=None,  # Not provided
                        freezing_altitude=freezing_altitude,
                        sunrise=sunrise,
                        sunset=sunset,
                        moonrise=moonrise,
                        moonset=moonset,
                        moon_illumination=float(astro.get('moon_illumination', '0').replace('%', ''))
                    )
                    forecasts.append(forecast)

                except Exception as e:
                    print(f"Error parsing WeatherAPI day: {e}")
                    continue

        except Exception as e:
            print(f"Error fetching WeatherAPI data: {e}")

        return forecasts

    def _estimate_freezing_altitude(self, temp_celsius: float) -> float:
        """Estimate freezing altitude (same as Open-Meteo)"""
        if temp_celsius <= 0:
            return 0
        altitude = (temp_celsius / 6.5) * 1000
        return altitude
