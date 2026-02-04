"""
Israel Outdoor Forecast - Unified Backend
Three activity modes: Helicopter, Kite, Stargazing
With automatic data verification
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

import httpx
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

# Verification imports
from verification import (
    verifier, verify_kite_rankings_background,
    verify_helicopter_forecast_background, verify_stars_forecast_background
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('main')


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
async def keep_alive():
    """Ping own health endpoint every 10 min to prevent Render free tier spin-down"""
    url = os.environ.get("RENDER_EXTERNAL_URL")
    if not url:
        logger.info("[keep-alive] RENDER_EXTERNAL_URL not set, skipping")
        return

    health_url = f"{url}/api/health"
    logger.info(f"[keep-alive] Started, pinging {health_url} every 10 min")

    async with httpx.AsyncClient(timeout=15.0) as client:
        while True:
            await asyncio.sleep(600)  # 10 minutes
            try:
                resp = await client.get(health_url)
                logger.debug(f"[keep-alive] Ping OK: {resp.status_code}")
            except Exception as e:
                logger.warning(f"[keep-alive] Ping failed: {e}")


async def refresh_kite_data():
    """Refresh kite forecast data with background verification"""
    if app_state.is_updating:
        logger.info("Kite data refresh already in progress, skipping")
        return

    app_state.is_updating = True
    try:
        spots = get_all_spots()
        spot_coords = get_spot_coordinates()

        logger.info(f"Fetching forecasts for {len(spot_coords)} kite spots...")
        app_state.kite_forecasts = await app_state.weather_service.fetch_all_spots_forecast(
            spot_coords, days=3
        )
        app_state.kite_rankings = rank_all_spots(spots, app_state.kite_forecasts)
        app_state.last_update = datetime.now()
        logger.info(f"Kite data refreshed: {len(app_state.kite_forecasts)} spots")

        # Run verification in background (non-blocking)
        rankings_data = [
            {
                "spot_id": r.spot_id,
                "wind_speed_knots": r.wind_speed_knots,
                "wind_gusts_knots": r.wind_gusts_knots,
                "wind_direction_deg": r.wind_direction_deg,
                "wave_height_m": r.wave_height_m,
                "overall_score": r.overall_score,
                "wind_score": r.wind_score,
                "wave_score": r.wave_score,
                "direction_score": r.direction_score
            }
            for r in app_state.kite_rankings
        ]
        asyncio.create_task(verify_kite_rankings_background(rankings_data))

    except Exception as e:
        logger.error(f"Error refreshing kite data: {e}", exc_info=True)
    finally:
        app_state.is_updating = False


# ============ Lifespan ============
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info("  Israel Outdoor Forecast")
    logger.info("  Modes: Helicopter | Kite | Stars")
    logger.info("  Data verification: ENABLED")
    logger.info("=" * 50)

    # Initialize services
    app_state.weather_service = WeatherService()
    app_state.helicopter_service = HelicopterService()
    app_state.stars_service = StarsService()
    logger.info("All services initialized")

    # Initial data fetch
    await refresh_kite_data()

    # Start keep-alive pinger
    keep_alive_task = asyncio.create_task(keep_alive())

    yield

    keep_alive_task.cancel()

    logger.info("Shutting down...")
    if app_state.weather_service:
        await app_state.weather_service.close()
    if app_state.helicopter_service:
        await app_state.helicopter_service.close()
    if app_state.stars_service:
        await app_state.stars_service.close()
    logger.info("Shutdown complete")


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
    verification_summary = verifier.get_summary()
    return {
        "status": "healthy",
        "version": "2.1.0",
        "modes": ["helicopter", "kite", "stars"],
        "last_update": app_state.last_update.isoformat() if app_state.last_update else None,
        "verification": {
            "enabled": True,
            "success_rate": verification_summary["success_rate"],
            "total_checks": verification_summary["total_checks"]
        }
    }


@app.get("/api/verification")
async def get_verification_status():
    """Get data verification status and recent issues"""
    return verifier.get_summary()


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
                "wind_direction_deg": r.wind_direction_deg,
                "wave_height_m": r.wave_height_m,
                "wave_danger": r.wave_height_m is not None and r.wave_height_m > 1.5,
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
            "wind_direction_cardinal": wind.wind_direction_cardinal,
            "wind_direction_deg": wind.wind_direction
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
    """Get helicopter flight conditions forecast with background verification"""
    forecast = await app_state.helicopter_service.get_forecast(location, days)
    if not forecast:
        raise HTTPException(404, f"Location not found: {location}")

    # Run verification in background (non-blocking)
    asyncio.create_task(verify_helicopter_forecast_background(forecast))

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
    """Get stargazing conditions forecast with background verification"""
    forecast = await app_state.stars_service.get_forecast(location, days)
    if not forecast:
        raise HTTPException(404, f"Location not found: {location}")

    # Run verification in background (non-blocking)
    asyncio.create_task(verify_stars_forecast_background(forecast))

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
