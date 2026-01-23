import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base_scraper import BaseScraper
from models import ForecastData
from datetime import datetime, timedelta, time
from typing import List
import requests
from moon_calculator import MoonCalculator

class SevenTimerScraper(BaseScraper):
    """Scraper for 7Timer API (free, no API key required)"""

    def __init__(self):
        super().__init__('7timer')
        self.base_url = 'https://www.7timer.info/bin/api.pl'
        self.moon_calc = MoonCalculator()

        # Location coordinates for Israeli cities
        self.locations = {
            'Tel Aviv': {'lat': 32.0853, 'lon': 34.7818},
            'Jerusalem': {'lat': 31.7683, 'lon': 35.2137},
            'Haifa': {'lat': 32.7940, 'lon': 34.9896},
            'Beer Sheva': {'lat': 31.2518, 'lon': 34.7913}
        }

    def scrape(self, location: str) -> List[ForecastData]:
        """Fetch weather forecast from 7Timer API"""
        forecasts = []

        try:
            # Get coordinates for location
            coords = self.locations.get(location, self.locations['Tel Aviv'])

            # API parameters for CIVIL product (most detailed)
            params = {
                'lon': coords['lon'],
                'lat': coords['lat'],
                'product': 'civil',
                'output': 'json'
            }

            # Make API request
            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            # Group 3-hourly data into daily forecasts
            dataseries = data.get('dataseries', [])
            daily_data = {}

            for item in dataseries[:56]:  # Up to 7 days of 3-hour data
                try:
                    # Parse timepoint (hours from init time)
                    init_time = data.get('init', '2024010100')
                    init_dt = datetime.strptime(init_time, '%Y%m%d%H')
                    timepoint = item.get('timepoint', 0)
                    forecast_dt = init_dt + timedelta(hours=timepoint)
                    date_key = forecast_dt.date()

                    if date_key not in daily_data:
                        daily_data[date_key] = {
                            'temps': [],
                            'wind_speeds': [],
                            'wind_dirs': [],
                            'clouds': []
                        }

                    # Temperature (in Celsius)
                    temp = item.get('temp2m', 0)
                    daily_data[date_key]['temps'].append(temp)

                    # Wind
                    wind = item.get('wind10m', {})
                    daily_data[date_key]['wind_speeds'].append(wind.get('speed', 0))
                    daily_data[date_key]['wind_dirs'].append(wind.get('direction', 'N'))

                    # Cloud cover (convert cloudcover code to percentage)
                    cloudcover_code = item.get('cloudcover', 1)
                    cloud_pct = self._cloudcover_to_percent(cloudcover_code)
                    daily_data[date_key]['clouds'].append(cloud_pct)

                except Exception as e:
                    print(f"Error parsing 7Timer item: {e}")
                    continue

            # Create daily forecasts
            for date_key, day_data in sorted(daily_data.items()):
                try:
                    temps = day_data['temps']
                    if not temps:
                        continue

                    temp_high = max(temps)
                    temp_low = min(temps)

                    # Max wind speed
                    wind_speeds = day_data['wind_speeds']
                    wind_speed = max(wind_speeds) if wind_speeds else 0

                    # Most common wind direction
                    wind_dirs = day_data['wind_dirs']
                    wind_direction = max(set(wind_dirs), key=wind_dirs.count) if wind_dirs else 'N'

                    # Average cloud cover
                    clouds = day_data['clouds']
                    cloud_cover = sum(clouds) / len(clouds) if clouds else 0

                    # Estimate freezing altitude
                    freezing_altitude = self._estimate_freezing_altitude(temp_high)

                    # Calculate accurate sunrise/sunset and moon data
                    sun_data = self.moon_calc.get_sun_data(location, date_key)
                    moon_data = self.moon_calc.get_moon_data(location, date_key)

                    sunrise = sun_data['sunrise']
                    sunset = sun_data['sunset']

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
                        moonrise=moon_data['moonrise'],
                        moonset=moon_data['moonset'],
                        moon_illumination=moon_data['moon_illumination']
                    )
                    forecasts.append(forecast)

                except Exception as e:
                    print(f"Error creating 7Timer forecast: {e}")
                    continue

        except Exception as e:
            print(f"Error fetching 7Timer data: {e}")

        return forecasts

    def _cloudcover_to_percent(self, code: int) -> float:
        """Convert 7Timer cloud cover code to percentage"""
        mapping = {
            1: 0,    # Clear
            2: 20,   # Partly cloudy
            3: 40,   # Partly cloudy
            4: 60,   # Cloudy
            5: 80,   # Cloudy
            6: 90,   # Overcast
            7: 100,  # Overcast
            8: 100,  # Overcast
            9: 50    # Fog/other
        }
        return mapping.get(code, 50)

    def _estimate_freezing_altitude(self, temp_celsius: float) -> float:
        """Estimate freezing altitude"""
        if temp_celsius <= 0:
            return 0
        altitude = (temp_celsius / 6.5) * 1000
        return altitude
