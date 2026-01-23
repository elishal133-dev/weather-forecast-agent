"""
Example script showing how to use the weather forecast aggregator programmatically
"""

from scrapers import IMSScraper, YnetScraper, MakoScraper, WeatherComScraper
from aggregator import ForecastAggregator
from config import DEFAULT_LOCATION

def main():
    """Run a simple example of the forecast aggregator"""
    print("Weather Forecast Aggregator - Example")
    print("=" * 50)

    location = DEFAULT_LOCATION
    print(f"\nFetching forecasts for: {location}")
    print("-" * 50)

    # Initialize scrapers
    scrapers = [
        IMSScraper(),
        YnetScraper(),
        MakoScraper(),
        WeatherComScraper()
    ]

    # Collect forecasts from all sources
    all_forecasts = []
    for scraper in scrapers:
        print(f"\nScraping {scraper.source_name}...")
        try:
            forecasts = scraper.scrape(location)
            print(f"  ✓ Found {len(forecasts)} days of forecast data")
            all_forecasts.extend(forecasts)
        except Exception as e:
            print(f"  ✗ Error: {e}")

    print(f"\nTotal forecasts collected: {len(all_forecasts)}")

    # Aggregate forecasts
    print("\nAggregating forecasts...")
    aggregator = ForecastAggregator()
    aggregated = aggregator.aggregate_forecasts(all_forecasts, location)

    print(f"Aggregated {len(aggregated)} days of forecast")
    print("\n" + "=" * 50)

    # Display aggregated forecasts
    if aggregated:
        print("\nAGGREGATED FORECAST:")
        print("=" * 50)

        for day in aggregated:
            print(f"\n📅 {day.date.strftime('%A, %B %d, %Y')}")
            print(f"   Confidence: {day.confidence:.1f}%")
            print(f"   🌡️  High: {day.temp_high:.1f}°C | Low: {day.temp_low:.1f}°C")
            print(f"   💨 Wind: {day.wind_speed:.1f} km/h {day.wind_direction}")
            print(f"   ☁️  Cloud Cover: {day.cloud_cover:.1f}%")
            if day.cloud_min_level:
                print(f"   ⬆️  Cloud Base: {day.cloud_min_level:.0f}m")
            print(f"   🌅 Sunrise: {day.sunrise.strftime('%H:%M')} | Sunset: {day.sunset.strftime('%H:%M')}")
            print(f"   🌔 Moonrise: {day.moonrise.strftime('%H:%M')} | Moonset: {day.moonset.strftime('%H:%M')}")
            print(f"   🌙 Moon Illumination: {day.moon_illumination:.1f}%")
            print(f"   Sources: {', '.join(day.sources_used)}")
            print("-" * 50)
    else:
        print("\n⚠️  No forecasts could be aggregated.")
        print("This is expected if the scrapers haven't been configured with actual website selectors yet.")

    print("\n" + "=" * 50)
    print("Example complete!")
    print("\nNote: If you see no data, the scrapers need to be updated with actual")
    print("CSS selectors from the weather websites. See README.md for instructions.")

if __name__ == "__main__":
    main()
