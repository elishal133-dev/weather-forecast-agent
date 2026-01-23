"""Test script to verify API scrapers are working"""

from scrapers import OpenMeteoScraper, SevenTimerScraper

print("Testing Weather API Scrapers")
print("=" * 60)

# Test Open-Meteo
print("\n1. Testing Open-Meteo (no API key needed)...")
scraper1 = OpenMeteoScraper()
forecasts1 = scraper1.scrape("Tel Aviv")
print(f"   Found {len(forecasts1)} forecast days")
if forecasts1:
    print(f"   Sample: {forecasts1[0].date.date()} - High: {forecasts1[0].temp_high}°C, Low: {forecasts1[0].temp_low}°C")

# Test 7Timer
print("\n2. Testing 7Timer (no API key needed)...")
scraper2 = SevenTimerScraper()
forecasts2 = scraper2.scrape("Tel Aviv")
print(f"   Found {len(forecasts2)} forecast days")
if forecasts2:
    print(f"   Sample: {forecasts2[0].date.date()} - High: {forecasts2[0].temp_high}°C, Low: {forecasts2[0].temp_low}°C")

print("\n" + "=" * 60)
print(f"Total forecasts collected: {len(forecasts1) + len(forecasts2)}")
print("\nIf you see forecasts above, the APIs are working!")
print("Refresh your browser at http://localhost:5000 to see real data.")
