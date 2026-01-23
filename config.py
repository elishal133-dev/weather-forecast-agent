# Configuration for weather forecast agent

# Default location (can be modified)
DEFAULT_LOCATION = "Tel Aviv"

# API Keys (optional - leave empty if not using)
# Get free API keys from:
# - OpenWeatherMap: https://openweathermap.org/api (1000 calls/day free)
# - WeatherAPI: https://www.weatherapi.com/ (free tier available)
OPENWEATHER_API_KEY = ""  # Optional: Add your OpenWeatherMap API key here
WEATHERAPI_API_KEY = ""   # Optional: Add your WeatherAPI key here

# Accuracy weights for each source (based on observed performance)
# These can be adjusted based on your observations
ACCURACY_WEIGHTS = {
    'open_meteo': 1.0,      # Open-Meteo - high resolution models
    '7timer': 0.85,         # 7Timer - good free alternative
    'openweather': 0.95,    # OpenWeatherMap - reliable when API key provided
    'weatherapi': 0.90      # WeatherAPI - good accuracy when API key provided
}

# Minimum consensus threshold (how many sources must agree)
CONSENSUS_THRESHOLD = 2

# Temperature tolerance for consensus (degrees Celsius)
TEMP_TOLERANCE = 2

# Wind speed tolerance for consensus (km/h)
WIND_TOLERANCE = 5

# Cloud cover tolerance for consensus (percentage)
CLOUD_COVER_TOLERANCE = 10

# Cloud minimum level tolerance for consensus (meters)
CLOUD_MIN_LEVEL_TOLERANCE = 200

# Freezing altitude tolerance for consensus (meters)
FREEZING_ALTITUDE_TOLERANCE = 200

# Time tolerance for consensus (minutes) - for sunrise/sunset/moonrise/moonset
TIME_TOLERANCE = 5

# Moon illumination tolerance for consensus (percentage)
MOON_ILLUMINATION_TOLERANCE = 5
