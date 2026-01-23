import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.base_scraper import BaseScraper
from models import ForecastData
from datetime import datetime, timedelta
from typing import List

class IMSScraper(BaseScraper):
    """Scraper for Israel Meteorological Service (ims.gov.il)"""

    def __init__(self):
        super().__init__('ims')
        self.base_url = 'https://ims.gov.il'

    def scrape(self, location: str) -> List[ForecastData]:
        """
        Scrape IMS weather forecast
        Note: This is a template - actual selectors need to be adjusted
        based on the real HTML structure of ims.gov.il
        """
        forecasts = []

        try:
            # IMS typically has an English version at /en/forecast
            url = f'{self.base_url}/en/forecast'
            soup = self.get_html(url)

            if not soup:
                return forecasts

            # TODO: Adjust selectors based on actual HTML structure
            # This is a template that needs to be customized
            forecast_days = soup.select('.forecast-day')  # Example selector

            for i, day in enumerate(forecast_days[:7]):  # Get up to 7 days
                try:
                    date = datetime.now() + timedelta(days=i)

                    # Extract temperature
                    temp_high_elem = day.select_one('.temp-high')
                    temp_low_elem = day.select_one('.temp-low')

                    temp_high = self.clean_temp(temp_high_elem.text) if temp_high_elem else None
                    temp_low = self.clean_temp(temp_low_elem.text) if temp_low_elem else None

                    # Extract wind data
                    wind_speed_elem = day.select_one('.wind-speed')
                    wind_dir_elem = day.select_one('.wind-direction')

                    wind_speed = self.clean_wind_speed(wind_speed_elem.text) if wind_speed_elem else None
                    wind_direction = wind_dir_elem.text.strip() if wind_dir_elem else None

                    # Extract cloud data
                    cloud_cover_elem = day.select_one('.cloud-cover')
                    cloud_level_elem = day.select_one('.cloud-level')

                    cloud_cover = self.clean_cloud_cover(cloud_cover_elem.text) if cloud_cover_elem else None
                    cloud_min_level = self.clean_cloud_level(cloud_level_elem.text) if cloud_level_elem else None

                    # Extract sun/moon times
                    sunrise_elem = day.select_one('.sunrise')
                    sunset_elem = day.select_one('.sunset')
                    moonrise_elem = day.select_one('.moonrise')
                    moonset_elem = day.select_one('.moonset')
                    moon_illum_elem = day.select_one('.moon-illumination')

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
                    print(f"Error parsing IMS day {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error scraping IMS: {e}")

        return forecasts
