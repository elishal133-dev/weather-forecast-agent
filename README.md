# Weather Forecast Aggregator

A Python-based weather forecast aggregation agent that collects data from 4 Israeli weather sources and creates a consensus-based forecast with accuracy weighting. The forecasts are displayed in a beautiful web dashboard.

## Features

- **Multi-Source Aggregation**: Collects forecasts from 4 weather sources:
  - IMS (Israel Meteorological Service)
  - Ynet Weather
  - Mako Weather
  - Weather.com (Israel)

- **Comprehensive Weather Data**:
  - Temperature (high/low)
  - Wind speed and direction
  - Cloud cover percentage
  - Cloud minimum level (cloud base/ceiling)
  - Sunrise and sunset times
  - Moonrise and moonset times
  - Moon illumination percentage

- **Intelligent Aggregation**:
  - Consensus-based algorithm
  - Weighted by historical accuracy
  - Confidence scoring
  - Handles missing data gracefully

- **Interactive Web Dashboard**:
  - Clean, modern UI
  - Location selector (Tel Aviv, Jerusalem, Haifa, Beer Sheva)
  - 5-7 day forecast display
  - View individual source data
  - Real-time data fetching

## Installation

1. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify installation**:
   ```bash
   python -c "import flask; import requests; import bs4"
   ```

## Usage

1. **Start the web server**:
   ```bash
   python app.py
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:5000
   ```

3. **Select your location** from the dropdown menu and click "Refresh" to fetch the latest forecasts.

## Configuration

Edit `config.py` to customize:

- **Accuracy weights** for each source (0.0-1.0)
- **Consensus threshold** (minimum sources required)
- **Tolerance values** for temperature, wind, cloud cover, etc.
- **Default location**

Example:
```python
ACCURACY_WEIGHTS = {
    'ims': 1.0,      # Most reliable
    'ynet': 0.85,
    'mako': 0.80,
    'weather_com': 0.90
}

CONSENSUS_THRESHOLD = 2  # At least 2 sources must agree
TEMP_TOLERANCE = 2       # °C
WIND_TOLERANCE = 5       # km/h
```

## Project Structure

```
weather-forecast-agent/
├── app.py                  # Flask web application
├── aggregator.py           # Forecast aggregation logic
├── models.py               # Data models
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── scrapers/
│   ├── __init__.py
│   ├── base_scraper.py    # Base scraper class
│   ├── ims_scraper.py     # IMS scraper
│   ├── ynet_scraper.py    # Ynet scraper
│   ├── mako_scraper.py    # Mako scraper
│   └── weather_com_scraper.py  # Weather.com scraper
├── templates/
│   └── index.html         # Dashboard HTML
└── static/
    └── style.css          # Dashboard styles
```

## How It Works

### 1. Data Collection
Each scraper fetches forecast data from its respective source in parallel using threading.

### 2. Aggregation
The `ForecastAggregator` processes all forecasts:
- Groups forecasts by date
- Calculates weighted averages for numeric values (temperature, wind speed, cloud cover, moon illumination)
- Determines consensus for categorical values (wind direction)
- Averages time values (sunrise, sunset, moonrise, moonset)
- Calculates confidence score based on agreement among sources

### 3. Confidence Score
Confidence is calculated based on:
- Standard deviation of temperature predictions
- Agreement in wind speed
- Agreement in cloud cover
- Number of sources contributing data

Score ranges:
- **80-100%**: High confidence (most sources agree)
- **60-79%**: Medium confidence (moderate agreement)
- **<60%**: Low confidence (sources disagree)

## Customizing Scrapers

The current scrapers use **template selectors** that need to be adjusted based on actual website HTML structures. To customize:

1. Open the scraper file (e.g., `scrapers/ims_scraper.py`)
2. Update the CSS selectors to match the actual HTML elements:
   ```python
   temp_high_elem = day.select_one('.actual-class-name')
   ```
3. Test the scraper:
   ```python
   from scrapers import IMSScraper
   scraper = IMSScraper()
   forecasts = scraper.scrape("Tel Aviv")
   print(forecasts)
   ```

### Tips for Finding Selectors:
1. Open the weather website in your browser
2. Right-click on the element you want to scrape
3. Select "Inspect" or "Inspect Element"
4. Note the class names, IDs, or data attributes
5. Use those in your CSS selectors

## Important Notes

⚠️ **Web Scraping Considerations**:
- The scrapers need to be updated with actual CSS selectors from the websites
- Some websites may require JavaScript rendering (use Selenium if needed)
- Be respectful of rate limits and robots.txt
- Consider caching to reduce server load

⚠️ **Website Changes**:
- Weather websites may change their HTML structure
- Scrapers will need periodic maintenance
- Error handling is built-in for graceful failures

## Troubleshooting

### Scrapers Return Empty Data
- Check if website HTML structure has changed
- Update CSS selectors in scraper files
- Check if website requires JavaScript rendering
- Verify internet connection

### Dashboard Not Loading
- Ensure Flask is running: `python app.py`
- Check console for error messages
- Verify port 5000 is not in use

### Low Confidence Scores
- Normal when sources disagree significantly
- Check individual source data to see discrepancies
- Adjust accuracy weights if certain sources are consistently wrong

## Future Enhancements

- Add more weather sources
- Store historical data for accuracy tracking
- Implement automatic scraper selector updates
- Add precipitation forecasting
- Email/SMS alerts
- Mobile app version
- API endpoints for external access

## License

This project is for educational and personal use. Please respect the terms of service of the weather websites being scraped.

## Credits

Aggregates data from:
- Israel Meteorological Service (ims.gov.il)
- Ynet Weather (ynet.co.il/weather)
- Mako Weather (mako.co.il/weather)
- Weather.com
