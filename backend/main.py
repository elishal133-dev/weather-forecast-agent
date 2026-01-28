"""
Israel Outdoor Forecast - Unified Backend
Three activity modes: Helicopter, Kite, Stargazing
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Kite imports
from spots import (
    get_all_spots, get_spot_by_id, get_spots_by_region,
    get_spot_coordinates, KiteSpot, Region, Difficulty
)
from weather import WeatherService, SpotForecast, get_current_conditions
from ranking import rank_all_spots, get_best_spots_today, SpotRating

# Helicopter imports
from helicopter import HelicopterService, HELICOPTER_LOCATIONS

# Stargazing imports
from stars import StarsService, STARGAZING_LOCATIONS


# ============ App State ============
class AppState:
    def __init__(self):
        self.weather_service: Optional[WeatherService] = None
        self.helicopter_service: Optional[HelicopterService] = None
        self.stars_service: Optional[StarsService] = None
        # Kite data
        self.kite_forecasts: List[SpotForecast] = []
        self.kite_rankings: List[SpotRating] = []
        self.last_update: Optional[datetime] = None
        self.is_updating: bool = False


app_state = AppState()


# ============ Background Tasks ============
async def refresh_kite_data():
    """Refresh kite forecast data"""
    if app_state.is_updating:
        return

    app_state.is_updating = True
    try:
        spots = get_all_spots()
        spot_coords = get_spot_coordinates()

        app_state.kite_forecasts = await app_state.weather_service.fetch_all_spots_forecast(
            spot_coords, days=3
        )
        app_state.kite_rankings = rank_all_spots(spots, app_state.kite_forecasts)
        app_state.last_update = datetime.now()
        print(f"[{datetime.now()}] Kite data refreshed: {len(app_state.kite_forecasts)} spots")
    except Exception as e:
        print(f"Error refreshing kite data: {e}")
    finally:
        app_state.is_updating = False


# ============ Lifespan ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("=" * 50)
    print("  Israel Outdoor Forecast")
    print("  Modes: Helicopter | Kite | Stars")
    print("=" * 50)

    # Initialize services
    app_state.weather_service = WeatherService()
    app_state.helicopter_service = HelicopterService()
    app_state.stars_service = StarsService()

    # Initial data fetch
    await refresh_kite_data()

    yield

    print("Shutting down...")
    if app_state.weather_service:
        await app_state.weather_service.close()


# ============ FastAPI App ============
app = FastAPI(
    title="Israel Outdoor Forecast",
    description="Unified forecast for Helicopter flights, Kite surfing, and Stargazing",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Static Files ============
frontend_path = Path(__file__).parent.parent / "frontend"

@app.get("/")
async def root():
    return FileResponse(frontend_path / "index.html")

@app.get("/style.css")
async def serve_css():
    return FileResponse(frontend_path / "style.css", media_type="text/css")

@app.get("/app.js")
async def serve_js():
    return FileResponse(frontend_path / "app.js", media_type="application/javascript")

@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse(frontend_path / "manifest.json", media_type="application/json")


# ============ Health Check ============
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "version": "2.0.0",
        "modes": ["helicopter", "kite", "stars"],
        "last_update": app_state.last_update.isoformat() if app_state.last_update else None
    }


# ============ KITE ENDPOINTS ============
@app.get("/api/kite/spots")
async def get_kite_spots(region: Optional[str] = None):
    """Get all kite spots"""
    spots = get_all_spots()
    if region:
        try:
            region_enum = Region(region.lower())
            spots = get_spots_by_region(region_enum)
        except ValueError:
            raise HTTPException(400, f"Invalid region: {region}")

    return [
        {
            "id": s.id,
            "name": s.name,
            "name_he": s.name_he,
            "region": s.region.value,
            "latitude": s.latitude,
            "longitude": s.longitude,
            "difficulty": s.difficulty.value,
            "water_type": s.water_type,
            "description": s.description
        }
        for s in spots
    ]


@app.get("/api/kite/rankings")
async def get_kite_rankings(
    region: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50)
):
    """Get ranked kite spots by current conditions"""
    if not app_state.kite_rankings:
        raise HTTPException(503, "Data not yet available")

    rankings = app_state.kite_rankings

    if region:
        rankings = [r for r in rankings if r.region == region.lower()]

    return {
        "last_update": app_state.last_update.isoformat() if app_state.last_update else None,
        "count": len(rankings[:limit]),
        "rankings": [
            {
                "rank": i + 1,
                "spot_id": r.spot_id,
                "spot_name": r.spot_name,
                "spot_name_he": r.spot_name_he,
                "region": r.region,
                "overall_score": r.overall_score,
                "overall_rating": r.overall_rating.value,
                "wind_speed_knots": r.wind_speed_knots,
                "wind_gusts_knots": r.wind_gusts_knots,
                "wind_direction": r.wind_direction,
                "wave_height_m": r.wave_height_m,
                "wind_description": r.wind_description,
                "wave_description": r.wave_description,
                "recommendation": r.recommendation,
                "difficulty": r.difficulty,
                "is_suitable_for_beginners": r.is_suitable_for_beginners
            }
            for i, r in enumerate(rankings[:limit])
        ]
    }


@app.get("/api/kite/forecast/{spot_id}")
async def get_kite_spot_forecast(spot_id: str, hours: int = Query(24, ge=1, le=72)):
    """Get hourly forecast for a kite spot"""
    spot = get_spot_by_id(spot_id)
    if not spot:
        raise HTTPException(404, "Spot not found")

    forecast = next((f for f in app_state.kite_forecasts if f.spot_id == spot_id), None)
    if not forecast:
        raise HTTPException(503, "Forecast not available")

    hourly = []
    for i, wind in enumerate(forecast.wind_data[:hours]):
        hour_data = {
            "time": wind.timestamp.isoformat(),
            "wind_speed_knots": round(wind.wind_speed_knots, 1),
            "wind_gusts_knots": round(wind.wind_gusts_knots, 1),
            "wind_direction": wind.wind_direction,
            "wind_direction_cardinal": wind.wind_direction_cardinal
        }
        if forecast.wave_data and i < len(forecast.wave_data):
            wave = forecast.wave_data[i]
            hour_data["wave_height_m"] = round(wave.wave_height_m, 2)
        hourly.append(hour_data)

    return {
        "spot_id": spot_id,
        "spot_name": spot.name,
        "spot_name_he": spot.name_he,
        "hourly": hourly
    }


# ============ HELICOPTER ENDPOINTS ============
@app.get("/api/helicopter/locations")
async def get_helicopter_locations():
    """Get available helicopter flight locations"""
    return HELICOPTER_LOCATIONS


@app.get("/api/helicopter/forecast/{location}")
async def get_helicopter_forecast(location: str, days: int = Query(3, ge=1, le=7)):
    """Get helicopter flight conditions forecast"""
    forecast = await app_state.helicopter_service.get_forecast(location, days)
    if not forecast:
        raise HTTPException(404, f"Location not found: {location}")
    return forecast


@app.get("/api/helicopter/rankings")
async def get_helicopter_rankings():
    """Get ranked locations by helicopter flight conditions"""
    return await app_state.helicopter_service.get_rankings()


# ============ STARGAZING ENDPOINTS ============
@app.get("/api/stars/locations")
async def get_stars_locations():
    """Get stargazing locations in Israel"""
    return STARGAZING_LOCATIONS


@app.get("/api/stars/forecast/{location}")
async def get_stars_forecast(location: str, days: int = Query(7, ge=1, le=14)):
    """Get stargazing conditions forecast"""
    forecast = await app_state.stars_service.get_forecast(location, days)
    if not forecast:
        raise HTTPException(404, f"Location not found: {location}")
    return forecast


@app.get("/api/stars/tonight")
async def get_stars_tonight():
    """Get best stargazing conditions for tonight"""
    return await app_state.stars_service.get_best_tonight()


@app.get("/api/stars/rankings")
async def get_stars_rankings():
    """Get ranked locations by stargazing conditions"""
    return await app_state.stars_service.get_rankings()


# ============ REFRESH ============
@app.post("/api/refresh")
async def refresh_all(background_tasks: BackgroundTasks):
    """Force refresh all forecast data"""
    if app_state.is_updating:
        return {"message": "Update in progress"}

    background_tasks.add_task(refresh_kite_data)
    return {"message": "Refresh started"}


# ============ Main ============
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
