from flask import Flask, render_template, request, jsonify
from scrapers import OpenMeteoScraper, SevenTimerScraper, OpenWeatherScraper, WeatherAPIScraper
from scrapers.hourly_scraper import HourlyScraper
from aggregator import ForecastAggregator
from config import DEFAULT_LOCATION, OPENWEATHER_API_KEY, WEATHERAPI_API_KEY
import threading
import time
import os

app = Flask(__name__)

# Security: Add secret key for session management
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Security: Add security headers
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Whitelist of allowed locations (security: prevent injection)
ALLOWED_LOCATIONS = [
    'Tel Aviv', 'Jerusalem', 'Haifa', 'Beer Sheva',
    'Eilat', 'Tiberias', 'Netanya', 'Ashdod', 'Rishon LeZion',
    'Petah Tikva', 'Herzliya', 'Acre', 'Nazareth', 'Safed'
]

# Global cache for forecasts with thread safety
forecast_cache = {
    'data': None,
    'location': None,
    'timestamp': None,
    'loading': False
}
cache_lock = threading.Lock()  # Thread safety

def fetch_forecasts(location):
    """Fetch forecasts from all sources in separate threads"""
    global forecast_cache

    with cache_lock:
        forecast_cache['loading'] = True

    # Initialize API-based scrapers
    # Open-Meteo and 7Timer are always available (no API key needed)
    scrapers = [
        OpenMeteoScraper(),
        SevenTimerScraper(),
    ]

    # Add optional scrapers if API keys are configured
    if OPENWEATHER_API_KEY:
        scrapers.append(OpenWeatherScraper(OPENWEATHER_API_KEY))
    if WEATHERAPI_API_KEY:
        scrapers.append(WeatherAPIScraper(WEATHERAPI_API_KEY))

    print(f"Using {len(scrapers)} weather data sources")

    all_forecasts = []
    threads = []
    results = {}

    def scrape_source(scraper, loc, results_dict):
        """Thread function to scrape a single source"""
        try:
            print(f"Scraping {scraper.source_name}...")
            forecasts = scraper.scrape(loc)
            results_dict[scraper.source_name] = forecasts
            print(f"Completed {scraper.source_name}: {len(forecasts)} forecasts")
        except Exception as e:
            print(f"Error scraping {scraper.source_name}: {e}")
            results_dict[scraper.source_name] = []

    # Start all scrapers in parallel
    for scraper in scrapers:
        thread = threading.Thread(target=scrape_source, args=(scraper, location, results))
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete (with timeout)
    for thread in threads:
        thread.join(timeout=30)

    # Collect all forecasts
    for source_forecasts in results.values():
        all_forecasts.extend(source_forecasts)

    print(f"Total forecasts collected: {len(all_forecasts)}")

    if len(all_forecasts) == 0:
        print("WARNING: No forecast data collected from any source!")
        print("This shouldn't happen with Open-Meteo and 7Timer (no API keys needed).")
        print("Check your internet connection or firewall settings.")

    # Aggregate forecasts
    aggregator = ForecastAggregator()
    aggregated = aggregator.aggregate_forecasts(all_forecasts, location)

    print(f"Aggregated forecasts: {len(aggregated)}")

    # Fetch hourly data
    print("Fetching 3-hourly data...")
    hourly_scraper = HourlyScraper()
    hourly_data_by_date = hourly_scraper.scrape_hourly(location, days=7)
    print(f"Fetched hourly data for {len(hourly_data_by_date)} days")

    # Attach hourly data to aggregated forecasts and adjust daily max/min
    for agg_forecast in aggregated:
        date_key = agg_forecast.date.date().isoformat()
        if date_key in hourly_data_by_date:
            agg_forecast.hourly_data = hourly_data_by_date[date_key]

            # Add cloud base altitude to hourly forecasts only if real data available
            if agg_forecast.cloud_min_level and agg_forecast.cloud_min_level > 0:
                for hourly in agg_forecast.hourly_data:
                    hourly.cloud_base = agg_forecast.cloud_min_level

            # Adjust daily max/min to be consistent with hourly data
            hourly_temps = [h.temperature for h in agg_forecast.hourly_data if h.temperature is not None]
            if hourly_temps:
                hourly_max = max(hourly_temps)
                hourly_min = min(hourly_temps)

                # Ensure daily max is at least as high as hourly max
                if agg_forecast.temp_high < hourly_max:
                    print(f"Adjusting daily max for {date_key}: {agg_forecast.temp_high}°C -> {hourly_max}°C")
                    agg_forecast.temp_high = hourly_max

                # Ensure daily min is at least as low as hourly min
                if agg_forecast.temp_low > hourly_min:
                    print(f"Adjusting daily min for {date_key}: {agg_forecast.temp_low}°C -> {hourly_min}°C")
                    agg_forecast.temp_low = hourly_min

    # Update cache with thread safety
    with cache_lock:
        forecast_cache['data'] = {
            'aggregated': [f.to_dict() for f in aggregated],
            'raw': [f.to_dict() for f in all_forecasts]
        }
        forecast_cache['location'] = location
        forecast_cache['timestamp'] = time.time()
        forecast_cache['loading'] = False

@app.route('/')
def index():
    """Main dashboard page"""
    response = app.make_response(render_template('index.html', default_location=DEFAULT_LOCATION))
    # Force no-cache for HTML to ensure users get latest version
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/api/forecast')
def get_forecast():
    """API endpoint to get forecast data"""
    location = request.args.get('location', DEFAULT_LOCATION)

    # Security: Validate location input (whitelist)
    if location not in ALLOWED_LOCATIONS:
        return jsonify({
            'status': 'error',
            'message': f'Invalid location. Allowed locations: {", ".join(ALLOWED_LOCATIONS)}'
        }), 400

    # Check if we have cached data for this location (valid for 30 minutes)
    with cache_lock:
        cached_data = forecast_cache['data']
        cached_location = forecast_cache['location']
        cached_timestamp = forecast_cache['timestamp']
        is_loading = forecast_cache['loading']

    if (cached_data is not None and
        cached_location == location and
        cached_timestamp is not None and
        time.time() - cached_timestamp < 1800):
        return jsonify({
            'status': 'success',
            'data': cached_data,
            'cached': True
        })

    # Check if already loading
    if is_loading:
        return jsonify({
            'status': 'loading',
            'message': 'Forecast data is being fetched...'
        })

    # Fetch new data in background thread
    thread = threading.Thread(target=fetch_forecasts, args=(location,))
    thread.start()

    return jsonify({
        'status': 'loading',
        'message': 'Fetching forecast data from all sources...'
    })

@app.route('/api/status')
def get_status():
    """Check if forecast data is ready"""
    with cache_lock:
        is_loading = forecast_cache['loading']
        cached_data = forecast_cache['data']

    if is_loading:
        return jsonify({
            'status': 'loading',
            'message': 'Still fetching data...'
        })
    elif cached_data is not None:
        return jsonify({
            'status': 'ready',
            'data': cached_data
        })
    else:
        return jsonify({
            'status': 'empty',
            'message': 'No data available'
        })

if __name__ == '__main__':
    print("Starting Weather Forecast Aggregator...")
    print(f"Default location: {DEFAULT_LOCATION}")

    # Security: Only enable debug mode in development
    is_development = os.environ.get('FLASK_ENV') == 'development'

    if is_development:
        print("WARNING: Running in DEVELOPMENT mode")
        print("Dashboard will be available at http://localhost:5000")
        app.run(debug=True, host='0.0.0.0', port=5000)
    else:
        print("Running in PRODUCTION mode (debug disabled)")
        port = int(os.environ.get('PORT', 5000))
        app.run(debug=False, host='0.0.0.0', port=port)
