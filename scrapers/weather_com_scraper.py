import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base_scraper import BaseScraper
from models import ForecastData
from datetime import datetime, timedelta
from typing import List

class WeatherComScraper(BaseScraper):
    """Scraper for Weather.com (Israel locations)"""

    def __init__(self):
        super().__init__('weather_com')
        self.base_url = 'https://weather.com'

        # Location codes for major Israeli cities
        self.location_codes = {
            'Tel Aviv': 'l/2be3c5d3e1ed61c0cf696b1ca5e8f05e4b4d18bc21f8bc',
            'Jerusalem': 'l/2b79b9926589bd07c1e50bbf61e6e28efd6ff8b2b32f7c',
            'Haifa': 'l/2e51b8b65d4e0f5e6f1e6e0f6e6d6e6d6e6d6e6d6e',
            'Beer Sheva': 'l/2a79b9926589bd07c1e50bbf61e6e28efd6ff8b2b32f7c'
        }

    def get_location_code(self, location: str) -> str:
        """Get Weather.com location code for Israeli city"""
        # Return the code if we have it, otherwise default to Tel Aviv
        return self.location_codes.get(location, self.location_codes['Tel Aviv'])

    def scrape(self, location: str) -> List[ForecastData]:
        """
        Scrape Weather.com forecast
        Note: This is a template - actual selectors need to be adjusted
        based on the real HTML structure of weather.com
        """
        forecasts = []

        try:
            location_code = self.get_location_code(location)
            url = f'{self.base_url}/weather/tenday/{location_code}'
            soup = self.get_html(url)

            if not soup:
                return forecasts

            # TODO: Adjust selectors based on actual HTML structure
            # Weather.com often uses JavaScript, so may need Selenium
            forecast_days = soup.select('[data-testid="DailyForecast"]')  # Example selector

            for i, day in enumerate(forecast_days[:7]):  # Get up to 7 days
                try:
                    date = datetime.now() + timedelta(days=i)

                    # Extract temperature
                    temp_high_elem = day.select_one('[data-testid="TemperatureValue"]')
                    temp_low_elem = day.select_one('[data-testid="TemperatureValueLow"]')

                    temp_high = self.clean_temp(temp_high_elem.text) if temp_high_elem else None
                    temp_low = self.clean_temp(temp_low_elem.text) if temp_low_elem else None

                    # Extract wind data
                    wind_elem = day.select_one('[data-testid="Wind"]')
                    wind_speed = None
                    wind_direction = None

                    if wind_elem:
                        wind_text = wind_elem.text
                        wind_speed = self.clean_wind_speed(wind_text)
                        # Extract direction (usually first few letters like NE, SW, etc.)
                        import re
                        direction_match = re.search(r'\b([NESW]{1,3})\b', wind_text)
                        if direction_match:
                            wind_direction = direction_match.group(1)

                    # Extract cloud data (if available)
                    cloud_cover_elem = day.select_one('.cloud-cover')
                    cloud_level_elem = day.select_one('.cloud-ceiling')

                    cloud_cover = self.clean_cloud_cover(cloud_cover_elem.text) if cloud_cover_elem else None
                    cloud_min_level = self.clean_cloud_level(cloud_level_elem.text) if cloud_level_elem else None

                    # Extract sun/moon data (often in details section)
                    sunrise_elem = day.select_one('[data-testid="SunriseValue"]')
                    sunset_elem = day.select_one('[data-testid="SunsetValue"]')
                    moonrise_elem = day.select_one('[data-testid="MoonriseValue"]')
                    moonset_elem = day.select_one('[data-testid="MoonsetValue"]')
                    moon_phase_elem = day.select_one('[data-testid="MoonPhase"]')

                    sunrise = self.parse_time(sunrise_elem.text) if sunrise_elem else None
                    sunset = self.parse_time(sunset_elem.text) if sunset_elem else None
                    moonrise = self.parse_time(moonrise_elem.text) if moonrise_elem else None
                    moonset = self.parse_time(moonset_elem.text) if moonset_elem else None
                    moon_illumination = self.clean_moon_illumination(moon_phase_elem.text) if moon_phase_elem else None

                    forecast = ForecastData(
                        source=self.source_name,
                        location=location,
                        date=date,
                        temp_high=temp_high,
                        temp_low=temp_low,
                        wind_speed=wind_speed,
                        wind_direction=wind_direction,
                        cloud_cover=cloud_cover,
                        cloud_min_level=cloud_min_level,
                        sunrise=sunrise,
                        sunset=sunset,
                        moonrise=moonrise,
                        moonset=moonset,
                        moon_illumination=moon_illumination
                    )
                    forecasts.append(forecast)

                except Exception as e:
                    print(f"Error parsing Weather.com day {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error scraping Weather.com: {e}")

        return forecasts
