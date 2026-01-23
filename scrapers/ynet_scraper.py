import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base_scraper import BaseScraper
from models import ForecastData
from datetime import datetime, timedelta
from typing import List

class YnetScraper(BaseScraper):
    """Scraper for Ynet Weather (ynet.co.il/weather)"""

    def __init__(self):
        super().__init__('ynet')
        self.base_url = 'https://www.ynet.co.il/weather'

    def scrape(self, location: str) -> List[ForecastData]:
        """
        Scrape Ynet weather forecast
        Note: This is a template - actual selectors need to be adjusted
        based on the real HTML structure of ynet.co.il/weather
        """
        forecasts = []

        try:
            # Ynet weather page
            url = self.base_url
            soup = self.get_html(url)

            if not soup:
                return forecasts

            # TODO: Adjust selectors based on actual HTML structure
            # This is a template that needs to be customized
            forecast_days = soup.select('.weather-day-item')  # Example selector

            for i, day in enumerate(forecast_days[:7]):  # Get up to 7 days
                try:
                    date = datetime.now() + timedelta(days=i)

                    # Extract temperature
                    temp_high_elem = day.select_one('.max-temp')
                    temp_low_elem = day.select_one('.min-temp')

                    temp_high = self.clean_temp(temp_high_elem.text) if temp_high_elem else None
                    temp_low = self.clean_temp(temp_low_elem.text) if temp_low_elem else None

                    # Extract wind data
                    wind_speed_elem = day.select_one('.wind')
                    wind_dir_elem = day.select_one('.wind-dir')

                    wind_speed = self.clean_wind_speed(wind_speed_elem.text) if wind_speed_elem else None
                    wind_direction = wind_dir_elem.text.strip() if wind_dir_elem else None

                    # Extract cloud data
                    cloud_cover_elem = day.select_one('.clouds')
                    cloud_level_elem = day.select_one('.cloud-height')

                    cloud_cover = self.clean_cloud_cover(cloud_cover_elem.text) if cloud_cover_elem else None
                    cloud_min_level = self.clean_cloud_level(cloud_level_elem.text) if cloud_level_elem else None

                    # Extract sun/moon times
                    sunrise_elem = day.select_one('.sunrise-time')
                    sunset_elem = day.select_one('.sunset-time')
                    moonrise_elem = day.select_one('.moonrise-time')
                    moonset_elem = day.select_one('.moonset-time')
                    moon_illum_elem = day.select_one('.moon-phase')

                    sunrise = self.parse_time(sunrise_elem.text) if sunrise_elem else None
                    sunset = self.parse_time(sunset_elem.text) if sunset_elem else None
                    moonrise = self.parse_time(moonrise_elem.text) if moonrise_elem else None
                    moonset = self.parse_time(moonset_elem.text) if moonset_elem else None
                    moon_illumination = self.clean_moon_illumination(moon_illum_elem.text) if moon_illum_elem else None

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
                    print(f"Error parsing Ynet day {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error scraping Ynet: {e}")

        return forecasts
