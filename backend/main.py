"""
Kite Forecast Israel - FastAPI Backend
Main application entry point
"""

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from spots import (
    get_all_spots,
    get_spot_by_id,
    get_spots_by_region,
    get_spot_coordinates,
    KiteSpot,
    Region,
    Difficulty
)
from weather import WeatherService, SpotForecast, get_current_conditions
from ranking import rank_all_spots, get_best_spots_today, should_notify, SpotRating
from notifications import (
    NotificationService,
    create_kite_notification,
    send_notifications_to_all,
    NotificationPayload
)


# ============ Configuration ============

class Config:
    """Application configuration"""
    # Data refresh interval (minutes)
    REFRESH_INTERVAL_MINUTES = 30

    # Notification threshold (score)
    NOTIFICATION_THRESHOLD = 70

    # VAPID keys for push notifications (generate with: vapid --gen)
    # These are placeholder keys - replace with your own!
    VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_CLAIMS = {"sub": "mailto:admin@kiteforecast.local"}

    # Database
    DB_PATH = "data/kite_forecast.db"


# ============ Global State ============

class AppState:
    """Application state for caching forecasts"""
    def __init__(self):
        self.forecasts: List[SpotForecast] = []
        self.ratings: List[SpotRating] = []
        self.last_update: Optional[datetime] = None
        self.weather_service: Optional[WeatherService] = None
        self.notification_service: Optional[NotificationService] = None
        self.is_updating: bool = False


app_state = AppState()


# ============ Pydantic Models ============

class SubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscriptionRequest(BaseModel):
    endpoint: str
    keys: SubscriptionKeys


class SpotResponse(BaseModel):
    id: str
    name: str
    name_he: str
    region: str
    latitude: float
    longitude: float
    difficulty: str
    water_type: str
    description: str
    optimal_wind_directions: List[str]


class RatingResponse(BaseModel):
    spot_id: str
    spot_name: str
    spot_name_he: str
    region: str
    overall_score: float
    overall_rating: str
    wind_score: float
    wave_score: float
    direction_score: float
    wind_speed_knots: float
    wind_gusts_knots: float
    wind_direction: str
    wave_height_m: Optional[float]
    wind_description: str
    wave_description: str
    recommendation: str
    difficulty: str
    is_suitable_for_beginners: bool


class ForecastResponse(BaseModel):
    spot_id: str
    spot_name: str
    hourly: List[Dict[str, Any]]


# ============ Background Tasks ============

async def refresh_forecasts():
    """Background task to refresh weather forecasts"""
    if app_state.is_updating:
        return

    app_state.is_updating = True

    try:
        spots = get_all_spots()
        spot_coords = get_spot_coordinates()

        # Fetch all forecasts
        app_state.forecasts = await app_state.weather_service.fetch_all_spots_forecast(
            spot_coords,
            days=3
        )

        # Calculate ratings
        app_state.ratings = rank_all_spots(spots, app_state.forecasts)
        app_state.last_update = datetime.now()

        print(f"[{datetime.now()}] Forecasts refreshed for {len(app_state.forecasts)} spots")

        # Check if we should send notifications
        if should_notify(app_state.ratings, Config.NOTIFICATION_THRESHOLD):
            await send_good_conditions_notification()

    except Exception as e:
        print(f"Error refreshing forecasts: {e}")
    finally:
        app_state.is_updating = False


async def send_good_conditions_notification():
    """Send push notification for good conditions"""
    if not Config.VAPID_PRIVATE_KEY:
        print("VAPID keys not configured, skipping notifications")
        return

    best_spots = get_best_spots_today(app_state.ratings, Config.NOTIFICATION_THRESHOLD)

    if not best_spots:
        return

    # Convert ratings to dicts for notification
    spots_data = [
        {
            "spot_id": r.spot_id,
            "spot_name": r.spot_name,
            "overall_score": r.overall_score,
            "wind_speed_knots": r.wind_speed_knots,
            "wave_height_m": r.wave_height_m
        }
        for r in best_spots[:5]  # Top 5 spots
    ]

    payload = create_kite_notification(spots_data, Config.NOTIFICATION_THRESHOLD)

    if payload:
        results = await send_notifications_to_all(
            app_state.notification_service,
            payload,
            Config.VAPID_PRIVATE_KEY,
            Config.VAPID_CLAIMS
        )
        print(f"Notifications sent: {results}")


async def periodic_refresh():
    """Periodically refresh forecasts"""
    while True:
        await refresh_forecasts()
        await asyncio.sleep(Config.REFRESH_INTERVAL_MINUTES * 60)


# ============ Lifespan ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting Kite Forecast Israel...")

    # Initialize services
    app_state.weather_service = WeatherService()
    app_state.notification_service = NotificationService(Config.DB_PATH)

    # Initial forecast fetch
    await refresh_forecasts()

    # Start background refresh task
    refresh_task = asyncio.create_task(periodic_refresh())

    yield

    # Shutdown
    print("Shutting down...")
    refresh_task.cancel()
    if app_state.weather_service:
        await app_state.weather_service.close()


# ============ FastAPI App ============

app = FastAPI(
    title="Kite Forecast Israel",
    description="Real-time kite surfing conditions for all spots in Israel",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ API Routes ============

@app.get("/")
async def root():
    """Serve the PWA frontend"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "index.html"
    if frontend_path.exists():
        return FileResponse(frontend_path)
    return {"message": "Kite Forecast Israel API", "docs": "/docs"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "last_update": app_state.last_update.isoformat() if app_state.last_update else None,
        "spots_count": len(app_state.forecasts),
        "version": "1.0.0"
    }


@app.get("/api/spots", response_model=List[SpotResponse])
async def get_spots(
    region: Optional[str] = Query(None, description="Filter by region: north, central, south, eilat, kinneret")
):
    """Get all kite spots or filter by region"""
    spots = get_all_spots()

    if region:
        try:
            region_enum = Region(region.lower())
            spots = get_spots_by_region(region_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid region: {region}")

    return [
        SpotResponse(
            id=spot.id,
            name=spot.name,
            name_he=spot.name_he,
            region=spot.region.value,
            latitude=spot.latitude,
            longitude=spot.longitude,
            difficulty=spot.difficulty.value,
            water_type=spot.water_type,
            description=spot.description,
            optimal_wind_directions=[d.value for d in spot.optimal_wind_directions]
        )
        for spot in spots
    ]


@app.get("/api/spots/{spot_id}")
async def get_spot(spot_id: str):
    """Get details for a specific spot"""
    spot = get_spot_by_id(spot_id)
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found")

    return SpotResponse(
        id=spot.id,
        name=spot.name,
        name_he=spot.name_he,
        region=spot.region.value,
        latitude=spot.latitude,
        longitude=spot.longitude,
        difficulty=spot.difficulty.value,
        water_type=spot.water_type,
        description=spot.description,
        optimal_wind_directions=[d.value for d in spot.optimal_wind_directions]
    )


@app.get("/api/rankings")
async def get_rankings(
    region: Optional[str] = None,
    min_score: float = Query(0, ge=0, le=100),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Get ranked spots by current conditions

    Returns spots sorted by overall score (best conditions first)
    """
    if not app_state.ratings:
        raise HTTPException(status_code=503, detail="Forecast data not yet available")

    ratings = app_state.ratings

    # Filter by region if specified
    if region:
        ratings = [r for r in ratings if r.region == region.lower()]

    # Filter by minimum score
    ratings = [r for r in ratings if r.overall_score >= min_score]

    # Limit results
    ratings = ratings[:limit]

    return {
        "last_update": app_state.last_update.isoformat() if app_state.last_update else None,
        "count": len(ratings),
        "rankings": [
            {
                "rank": i + 1,
                "spot_id": r.spot_id,
                "spot_name": r.spot_name,
                "spot_name_he": r.spot_name_he,
                "region": r.region,
                "overall_score": r.overall_score,
                "overall_rating": r.overall_rating.value,
                "wind_score": r.wind_score,
                "wave_score": r.wave_score,
                "direction_score": r.direction_score,
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
            for i, r in enumerate(ratings)
        ]
    }


@app.get("/api/rankings/best")
async def get_best_conditions(
    threshold: float = Query(60, ge=0, le=100)
):
    """Get spots with good conditions today"""
    if not app_state.ratings:
        raise HTTPException(status_code=503, detail="Forecast data not yet available")

    best = get_best_spots_today(app_state.ratings, threshold)

    if not best:
        return {
            "message": "No spots with good conditions right now",
            "threshold": threshold,
            "spots": []
        }

    return {
        "message": f"Found {len(best)} spots with conditions above {threshold}",
        "threshold": threshold,
        "last_update": app_state.last_update.isoformat() if app_state.last_update else None,
        "spots": [
            {
                "spot_id": r.spot_id,
                "spot_name": r.spot_name,
                "spot_name_he": r.spot_name_he,
                "region": r.region,
                "overall_score": r.overall_score,
                "overall_rating": r.overall_rating.value,
                "wind_speed_knots": r.wind_speed_knots,
                "wind_direction": r.wind_direction,
                "wave_height_m": r.wave_height_m,
                "recommendation": r.recommendation
            }
            for r in best
        ]
    }


@app.get("/api/forecast/{spot_id}")
async def get_spot_forecast(spot_id: str, hours: int = Query(24, ge=1, le=72)):
    """Get detailed hourly forecast for a specific spot"""
    spot = get_spot_by_id(spot_id)
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found")

    forecast = next((f for f in app_state.forecasts if f.spot_id == spot_id), None)
    if not forecast:
        raise HTTPException(status_code=503, detail="Forecast data not available for this spot")

    # Build hourly data
    hourly = []
    for i, wind in enumerate(forecast.wind_data[:hours]):
        hour_data = {
            "time": wind.timestamp.isoformat(),
            "wind_speed_knots": round(wind.wind_speed_knots, 1),
            "wind_gusts_knots": round(wind.wind_gusts_knots, 1),
            "wind_direction": wind.wind_direction,
            "wind_direction_cardinal": wind.wind_direction_cardinal
        }

        # Add wave data if available
        if forecast.wave_data and i < len(forecast.wave_data):
            wave = forecast.wave_data[i]
            hour_data["wave_height_m"] = round(wave.wave_height_m, 2)
            hour_data["wave_period_s"] = round(wave.wave_period_s, 1)
            hour_data["wave_direction"] = wave.wave_direction

        hourly.append(hour_data)

    return {
        "spot_id": spot_id,
        "spot_name": spot.name,
        "spot_name_he": spot.name_he,
        "latitude": spot.latitude,
        "longitude": spot.longitude,
        "fetched_at": forecast.fetched_at.isoformat(),
        "hourly": hourly
    }


# ============ Push Notification Routes ============

@app.post("/api/notifications/subscribe")
async def subscribe_to_notifications(subscription: PushSubscriptionRequest):
    """Subscribe to push notifications"""
    try:
        sub_id = app_state.notification_service.save_subscription(
            endpoint=subscription.endpoint,
            p256dh_key=subscription.keys.p256dh,
            auth_key=subscription.keys.auth
        )
        return {"success": True, "subscription_id": sub_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/notifications/unsubscribe")
async def unsubscribe_from_notifications(subscription: PushSubscriptionRequest):
    """Unsubscribe from push notifications"""
    try:
        app_state.notification_service.remove_subscription(subscription.endpoint)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notifications/vapid-public-key")
async def get_vapid_public_key():
    """Get the VAPID public key for push subscription"""
    if not Config.VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push notifications not configured")
    return {"publicKey": Config.VAPID_PUBLIC_KEY}


# ============ Admin/Debug Routes ============

@app.post("/api/admin/refresh")
async def force_refresh(background_tasks: BackgroundTasks):
    """Force refresh of forecast data"""
    if app_state.is_updating:
        return {"message": "Update already in progress"}

    background_tasks.add_task(refresh_forecasts)
    return {"message": "Refresh started"}


# ============ Static Files ============

# Serve individual static files with explicit routes for better compatibility
frontend_path = Path(__file__).parent.parent / "frontend"

@app.get("/style.css")
async def serve_css():
    return FileResponse(frontend_path / "style.css", media_type="text/css")

@app.get("/app.js")
async def serve_js():
    return FileResponse(frontend_path / "app.js", media_type="application/javascript")

@app.get("/manifest.json")
async def serve_manifest():
    return FileResponse(frontend_path / "manifest.json", media_type="application/json")

@app.get("/sw.js")
async def serve_sw():
    return FileResponse(frontend_path / "sw.js", media_type="application/javascript")

# Mount for any other static files (icons, etc.)
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_path)), name="static")


# ============ Main ============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
