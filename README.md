# Israel Outdoor Forecast

Three outdoor activity forecasts in one app:
- **🚁 Helicopter** - Flight conditions
- **🪁 Kite** - Surfing conditions
- **⭐ Stars** - Stargazing conditions

## Live Demo

**https://khyzvy-hzvy.onrender.com**

## Features

### 🚁 Helicopter Mode
- 7 locations across Israel
- Wind speed & gusts evaluation
- Visibility tracking
- Precipitation alerts
- Flight safety scoring (0-100)

### 🪁 Kite Mode
- 20 kite spots (Mediterranean, Eilat, Kinneret)
- Wind speed & direction
- Wave height tracking
- Region filtering
- Beginner-friendly indicators

### ⭐ Stars Mode
- 8 dark sky locations
- Moon phase & illumination
- Cloud cover forecast
- Light pollution ratings
- 7-day forecast

## Tech Stack

- **Backend**: Python, FastAPI
- **Frontend**: PWA (HTML, CSS, JavaScript)
- **Weather API**: Open-Meteo (free)
- **Hosting**: Render

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI app
│   ├── helicopter.py    # Flight conditions
│   ├── kite.py          # Kite spots (spots.py, ranking.py)
│   ├── stars.py         # Stargazing
│   └── weather.py       # Weather API
├── frontend/
│   ├── index.html       # PWA
│   ├── app.js           # Frontend logic
│   └── style.css        # Dark theme
└── render.yaml          # Deployment config
```

## Run Locally

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open http://localhost:8000

## API Endpoints

| Mode | Endpoint | Description |
|------|----------|-------------|
| Kite | `/api/kite/rankings` | Ranked spots |
| Kite | `/api/kite/forecast/{id}` | Spot forecast |
| Helicopter | `/api/helicopter/rankings` | Ranked locations |
| Helicopter | `/api/helicopter/forecast/{id}` | Location forecast |
| Stars | `/api/stars/rankings` | Ranked locations |
| Stars | `/api/stars/tonight` | Best spot tonight |

## License

MIT
