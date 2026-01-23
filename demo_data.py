"""
Demo data generator for testing the weather forecast aggregator
Uses consistent seed-based random data so values don't change on each refresh
"""
from models import ForecastData, AggregatedForecast
from datetime import datetime, timedelta, time
import random

def generate_demo_forecasts(location: str, days: int = 5) -> list:
    """Generate demo forecast data for testing with consistent values"""
    forecasts = []
    sources = ['ims', 'ynet', 'mako', 'weather_com']

    # Use consistent seed based on current date (not time) so data stays same for the day
    today = datetime.now().date()
    seed_value = int(today.strftime('%Y%m%d'))

    for day_offset in range(days):
        date = datetime.now() + timedelta(days=day_offset)

        # Create a unique but consistent seed for each day
        day_seed = seed_value + day_offset * 1000
        random.seed(day_seed)

        # Base temperatures with some variation
        base_high = 22 + random.randint(-3, 5)
        base_low = 14 + random.randint(-2, 3)
        base_wind = random.uniform(10, 30)
        base_cloud = random.uniform(20, 80)
        base_freezing = random.uniform(2500, 4000)

        # Sun/moon times (consistent for the day)
        sunrise_time = time(6, random.randint(0, 30))
        sunset_time = time(17, random.randint(30, 59))
        moonrise_time = time(random.randint(18, 22), random.randint(0, 59))
        moonset_time = time(random.randint(5, 9), random.randint(0, 59))
        base_moon_illum = random.uniform(20, 95)

        for idx, source in enumerate(sources):
            # Use source-specific seed for slight variations
            random.seed(day_seed + idx)

            # Add slight variations per source
            temp_high = base_high + random.uniform(-1.5, 1.5)
            temp_low = base_low + random.uniform(-1, 1)
            wind_speed = base_wind + random.uniform(-3, 3)
            cloud_cover = base_cloud + random.uniform(-5, 5)
            freezing_altitude = base_freezing + random.uniform(-100, 100)
            moon_illumination = base_moon_illum + random.uniform(-2, 2)

            forecast = ForecastData(
                source=source,
                location=location,
                date=date,
                temp_high=round(temp_high, 1),
                temp_low=round(temp_low, 1),
                wind_speed=round(wind_speed, 1),
                wind_direction=random.choice(['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']),
                cloud_cover=round(max(0, min(100, cloud_cover)), 1),
                cloud_min_level=round(random.uniform(800, 2000), 0) if random.random() > 0.3 else None,
                freezing_altitude=round(freezing_altitude, 0),
                sunrise=sunrise_time,
                sunset=sunset_time,
                moonrise=moonrise_time,
                moonset=moonset_time,
                moon_illumination=round(max(0, min(100, moon_illumination)), 1)
            )
            forecasts.append(forecast)

    # Reset random seed to avoid affecting other random operations
    random.seed()

    return forecasts
