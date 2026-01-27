# Kite Forecast Israel

Real-time kite surfing forecast for all spots in Israel. Get ranked recommendations for the best places to kite today based on wind speed, direction, and wave conditions.

## Features

- **20+ Kite Spots**: Complete coverage of Israeli kite spots including:
  - Mediterranean coast (Betzet to Ashkelon)
  - Eilat (Red Sea)
  - Kinneret (Sea of Galilee)

- **Smart Ranking Algorithm**: Spots are ranked based on:
  - Wind speed (15-25 knots ideal)
  - Wind direction (matching spot's optimal direction)
  - Wave height (lower = safer for kiting)

- **Real-time Data**: Weather forecasts from Open-Meteo API, updated every 30 minutes

- **PWA Support**: Install on your phone for native app experience

- **Push Notifications**: Get notified when conditions are good

- **Hebrew & English**: Full RTL support with Hebrew spot names

## Tech Stack

- **Backend**: Python, FastAPI
- **Frontend**: PWA (HTML, CSS, JavaScript)
- **Weather API**: Open-Meteo (free, no API key required)
- **Database**: SQLite

## Installation

### Prerequisites

- Python 3.10+
- pip

### Setup

1. Clone the repository:
```bash
cd kite-forecast
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. (Optional) Set up push notifications:
```bash
# Generate VAPID keys
pip install py-vapid
vapid --gen

# Copy keys to .env file
cp .env.example .env
# Edit .env with your VAPID keys
```

5. Run the server:
```bash
cd backend
python main.py
```

6. Open http://localhost:8000 in your browser

## API Endpoints

### Rankings
- `GET /api/rankings` - Get ranked spots by current conditions
- `GET /api/rankings/best?threshold=70` - Get spots with good conditions

### Spots
- `GET /api/spots` - List all kite spots
- `GET /api/spots/{spot_id}` - Get spot details

### Forecast
- `GET /api/forecast/{spot_id}?hours=24` - Get hourly forecast for a spot

### Notifications
- `POST /api/notifications/subscribe` - Subscribe to push notifications
- `POST /api/notifications/unsubscribe` - Unsubscribe
- `GET /api/notifications/vapid-public-key` - Get VAPID public key

### Admin
- `POST /api/admin/refresh` - Force refresh forecast data
- `GET /api/health` - Health check

## Kite Spots Included

### Northern Coast
- Betzet Beach (חוף בצת)
- Achziv Beach (חוף אכזיב)
- Acre Fortress (חוף המבצר עכו)
- Kiryat Yam (קרית ים)
- Bat Galim (בת גלים) - Advanced
- Dado Beach (חוף דדו)

### Central Coast
- Sdot Yam (שדות ים)
- Beit Yanai (בית ינאי) - Most popular!
- Poleg Beach (חוף פולג)
- Herzliya Marina (מרינה הרצליה)
- Tel Baruch (תל ברוך)
- Geula Beach (חוף גאולה) - Advanced
- Hilton Beach (חוף הילטון)
- Dolfinarium (דולפינריום)

### Southern Coast
- Bat Yam (בת ים)
- Ashdod (אשדוד)
- Ashkelon Goote (חוף גוטה אשקלון)
- Ashkelon Delilah (חוף דלילה אשקלון)

### Eilat (Red Sea)
- Reef Raf (ריף רף אילת) - 80% wind days!

### Kinneret
- Diamond Bay (מפרץ הדיאמונד)

## Ranking System

Spots are scored 0-100 based on:

| Rating | Score | Description |
|--------|-------|-------------|
| Epic | 85-100 | Perfect conditions |
| Good | 70-84 | Great for kiting |
| Fair | 55-69 | Decent, rideable |
| Marginal | 40-54 | Barely rideable |
| Poor | 0-39 | Not recommended |

### Scoring Factors
- **Wind Score (50%)**: Ideal wind is 15-25 knots
- **Wave Score (30%)**: Lower waves = higher score (safer)
- **Direction Score (20%)**: Match with spot's optimal wind direction

## Development

### Project Structure
```
kite-forecast/
├── backend/
│   ├── main.py          # FastAPI application
│   ├── spots.py         # Kite spots database
│   ├── weather.py       # Weather API integration
│   ├── ranking.py       # Ranking algorithm
│   └── notifications.py # Push notifications
├── frontend/
│   ├── index.html       # PWA main page
│   ├── app.js           # Frontend logic
│   ├── style.css        # Styles
│   ├── manifest.json    # PWA manifest
│   └── sw.js            # Service worker
├── data/                # SQLite database
├── requirements.txt
└── README.md
```

### Adding New Spots

Edit `backend/spots.py` and add a new `KiteSpot` entry:

```python
KiteSpot(
    id="new_spot",
    name="New Spot Name",
    name_he="שם חדש",
    region=Region.CENTRAL,
    latitude=32.0000,
    longitude=34.0000,
    optimal_wind_directions=[WindDirection.NW, WindDirection.W],
    difficulty=Difficulty.INTERMEDIATE,
    description="Description of the spot",
    water_type="mixed",  # "waves", "flat", or "mixed"
    best_months=[9, 10, 11, 12, 1, 2, 3, 4, 5],
)
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License

## Acknowledgments

- Weather data provided by [Open-Meteo](https://open-meteo.com/)
- Spot information compiled from Israeli kite surfing community resources
