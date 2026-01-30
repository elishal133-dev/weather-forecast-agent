"""
Kite Spot Ranking Algorithm
Ranks spots based on current conditions for kite surfing
Priority: Wind first (higher = better), then Waves (higher = worse)
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

from spots import KiteSpot, WindDirection, get_spot_by_id
from weather import SpotForecast, get_current_conditions


class RatingLevel(Enum):
    """Overall rating level for a spot"""
    EPIC = "epic"           # Perfect conditions!
    GOOD = "good"           # Great for kiting
    FAIR = "fair"           # Decent, rideable
    MARGINAL = "marginal"   # Barely rideable
    POOR = "poor"           # Not recommended


@dataclass
class SpotRating:
    """Complete rating for a kite spot"""
    spot_id: str
    spot_name: str
    spot_name_he: str
    region: str
    overall_score: float         # 0-100
    overall_rating: RatingLevel
    wind_score: float            # 0-100
    wave_score: float            # 0-100 (100 = flat/safe, 0 = dangerous)
    direction_score: float       # 0-100 (how well wind matches optimal)

    # Current conditions
    wind_speed_knots: float
    wind_gusts_knots: float
    wind_direction: str
    wave_height_m: Optional[float]

    # Descriptive
    wind_description: str
    wave_description: str
    recommendation: str

    # Metadata
    difficulty: str
    is_suitable_for_beginners: bool
    timestamp: datetime


def calculate_wind_score(wind_speed: float, wind_gusts: float) -> float:
    """
    Calculate wind score (0-100)
    Ideal kite wind: 15-25 knots
    Good range: 12-30 knots
    Rideable: 10-35 knots
    """
    if wind_speed < 8:
        # Too light
        return max(0, wind_speed * 5)  # 0-40
    elif wind_speed < 12:
        # Light but rideable for big kites
        return 40 + (wind_speed - 8) * 7.5  # 40-70
    elif wind_speed < 15:
        # Good wind
        return 70 + (wind_speed - 12) * 5  # 70-85
    elif wind_speed <= 25:
        # Ideal wind range
        return 85 + min(15, (wind_speed - 15)) * 1  # 85-100
    elif wind_speed <= 30:
        # Strong but still good
        return 100 - (wind_speed - 25) * 3  # 100-85
    elif wind_speed <= 35:
        # Very strong, experts only
        return 85 - (wind_speed - 30) * 5  # 85-60
    else:
        # Too strong for most
        return max(20, 60 - (wind_speed - 35) * 4)

    # Penalize gusty conditions (difference between gusts and speed)
    gust_penalty = 0
    gust_diff = wind_gusts - wind_speed
    if gust_diff > 10:
        gust_penalty = min(20, (gust_diff - 10) * 2)

    return max(0, min(100, calculate_wind_score.__wrapped__(wind_speed, wind_gusts) - gust_penalty))


def calculate_wave_score(wave_height: Optional[float], spot: KiteSpot) -> float:
    """
    Calculate wave score (0-100)
    For kite surfing: lower waves = safer = better score
    100 = flat water (best for safety/learning)
    0 = dangerous waves

    Note: Some advanced riders prefer waves, but for general ranking
    we prioritize safety (lower waves = higher score)
    """
    if wave_height is None:
        # Inland spot (Kinneret) - flat water
        return 100

    if spot.water_type == "flat":
        # Flat water spots - waves are undesirable
        if wave_height < 0.3:
            return 100
        elif wave_height < 0.5:
            return 90
        elif wave_height < 1.0:
            return 70
        else:
            return max(30, 100 - wave_height * 40)

    elif spot.water_type == "waves":
        # Wave spots - moderate waves OK, but still penalize big waves
        if wave_height < 0.5:
            return 95  # Almost flat, great
        elif wave_height < 1.0:
            return 90  # Small waves, good
        elif wave_height < 1.5:
            return 80  # Medium waves, manageable
        elif wave_height < 2.0:
            return 65  # Getting challenging
        elif wave_height < 2.5:
            return 50  # Challenging
        else:
            return max(20, 100 - wave_height * 25)

    else:  # mixed
        if wave_height < 0.5:
            return 100
        elif wave_height < 1.0:
            return 85
        elif wave_height < 1.5:
            return 70
        elif wave_height < 2.0:
            return 55
        else:
            return max(25, 100 - wave_height * 30)


def calculate_direction_score(
    wind_direction_degrees: int,
    optimal_directions: List[WindDirection]
) -> float:
    """
    Calculate how well the current wind direction matches optimal directions
    100 = perfect match, 0 = completely wrong direction
    """
    if not optimal_directions:
        return 50  # No preference

    # Convert optimal directions to degrees
    direction_to_degrees = {
        WindDirection.N: 0,
        WindDirection.NE: 45,
        WindDirection.E: 90,
        WindDirection.SE: 135,
        WindDirection.S: 180,
        WindDirection.SW: 225,
        WindDirection.W: 270,
        WindDirection.NW: 315
    }

    # Find the closest optimal direction
    min_diff = 180
    for opt_dir in optimal_directions:
        opt_degrees = direction_to_degrees[opt_dir]
        diff = abs(wind_direction_degrees - opt_degrees)
        if diff > 180:
            diff = 360 - diff
        min_diff = min(min_diff, diff)

    # Score based on difference
    # 0-22.5 degrees: 100-90
    # 22.5-45 degrees: 90-75
    # 45-90 degrees: 75-50
    # 90-135 degrees: 50-25
    # 135-180 degrees: 25-0
    if min_diff <= 22.5:
        return 100 - (min_diff / 22.5) * 10
    elif min_diff <= 45:
        return 90 - ((min_diff - 22.5) / 22.5) * 15
    elif min_diff <= 90:
        return 75 - ((min_diff - 45) / 45) * 25
    elif min_diff <= 135:
        return 50 - ((min_diff - 90) / 45) * 25
    else:
        return max(0, 25 - ((min_diff - 135) / 45) * 25)


def get_wind_description(wind_speed: float, wind_gusts: float) -> str:
    """Generate human-readable wind description"""
    gust_diff = wind_gusts - wind_speed

    if wind_speed < 8:
        base = "Too light for kiting"
    elif wind_speed < 12:
        base = "Light wind - big kite needed"
    elif wind_speed < 15:
        base = "Moderate wind - good for learning"
    elif wind_speed < 20:
        base = "Good wind - ideal conditions"
    elif wind_speed < 25:
        base = "Strong wind - perfect for experienced riders"
    elif wind_speed < 30:
        base = "Very strong - experts only"
    else:
        base = "Extreme wind - dangerous"

    if gust_diff > 15:
        base += " (very gusty!)"
    elif gust_diff > 10:
        base += " (gusty)"

    return base


def get_wave_description(wave_height: Optional[float]) -> str:
    """Generate human-readable wave description"""
    if wave_height is None:
        return "Flat water (inland)"

    if wave_height < 0.3:
        return "Flat - perfect for beginners"
    elif wave_height < 0.5:
        return "Very small waves"
    elif wave_height < 1.0:
        return "Small waves - manageable"
    elif wave_height < 1.5:
        return "Medium waves"
    elif wave_height < 2.0:
        return "Moderate waves - intermediate+"
    elif wave_height < 2.5:
        return "Large waves - advanced"
    else:
        return f"Big waves ({wave_height:.1f}m) - experts only"


def get_overall_rating(score: float) -> RatingLevel:
    """Convert numeric score to rating level"""
    if score >= 85:
        return RatingLevel.EPIC
    elif score >= 70:
        return RatingLevel.GOOD
    elif score >= 55:
        return RatingLevel.FAIR
    elif score >= 40:
        return RatingLevel.MARGINAL
    else:
        return RatingLevel.POOR


def get_recommendation(
    rating: RatingLevel,
    wind_speed: float,
    wave_height: Optional[float],
    is_beginner_spot: bool
) -> str:
    """Generate recommendation text"""
    if rating == RatingLevel.EPIC:
        if is_beginner_spot:
            return "Perfect conditions! Great for all levels. Go now!"
        return "Epic conditions! Advanced riders - don't miss this!"

    elif rating == RatingLevel.GOOD:
        if wind_speed > 25:
            return "Strong wind - great for experienced riders"
        return "Good conditions for kiting. Recommended!"

    elif rating == RatingLevel.FAIR:
        if wind_speed < 12:
            return "Light wind - bring a big kite"
        if wave_height and wave_height > 1.5:
            return "Rideable but waves are challenging"
        return "Decent conditions - worth a session"

    elif rating == RatingLevel.MARGINAL:
        if wind_speed < 10:
            return "Barely enough wind - might be frustrating"
        return "Marginal conditions - only if nearby"

    else:
        if wind_speed < 8:
            return "Not enough wind today"
        if wind_speed > 35:
            return "Too windy - dangerous conditions"
        return "Conditions not recommended for kiting"


def rate_spot(
    spot: KiteSpot,
    forecast: SpotForecast
) -> SpotRating:
    """Calculate complete rating for a spot based on current conditions"""

    # Get current conditions
    current = get_current_conditions(forecast)

    wind_speed = current["wind"]["speed_knots"] if current["wind"] else 0
    wind_gusts = current["wind"]["gusts_knots"] if current["wind"] else 0
    wind_dir_degrees = current["wind"]["direction"] if current["wind"] else 0
    wind_dir_cardinal = current["wind"]["direction_cardinal"] if current["wind"] else "N"
    wave_height = current["wave"]["height_m"] if current["wave"] else None

    # Calculate component scores
    wind_score = calculate_wind_score(wind_speed, wind_gusts)
    wave_score = calculate_wave_score(wave_height, spot)
    direction_score = calculate_direction_score(wind_dir_degrees, spot.optimal_wind_directions)

    # Calculate overall score
    # Weights: Wind 60%, Direction match 30%, Wave safety 10%
    # Per requirements: wind first priority, waves low weight unless dangerous
    overall_score = (wind_score * 0.60) + (direction_score * 0.30) + (wave_score * 0.10)

    # Apply bonus/penalty for direction match
    if direction_score < 50:
        overall_score *= 0.85  # 15% penalty for poor wind direction

    overall_rating = get_overall_rating(overall_score)

    # Check if suitable for beginners
    from spots import Difficulty
    is_beginner_friendly = spot.difficulty in [Difficulty.BEGINNER, Difficulty.ALL_LEVELS]
    is_suitable = is_beginner_friendly and wave_height is not None and wave_height < 1.0 and wind_speed < 20

    return SpotRating(
        spot_id=spot.id,
        spot_name=spot.name,
        spot_name_he=spot.name_he,
        region=spot.region.value,
        overall_score=round(overall_score, 1),
        overall_rating=overall_rating,
        wind_score=round(wind_score, 1),
        wave_score=round(wave_score, 1),
        direction_score=round(direction_score, 1),
        wind_speed_knots=round(wind_speed, 1),
        wind_gusts_knots=round(wind_gusts, 1),
        wind_direction=wind_dir_cardinal,
        wave_height_m=round(wave_height, 2) if wave_height else None,
        wind_description=get_wind_description(wind_speed, wind_gusts),
        wave_description=get_wave_description(wave_height),
        recommendation=get_recommendation(overall_rating, wind_speed, wave_height, is_beginner_friendly),
        difficulty=spot.difficulty.value,
        is_suitable_for_beginners=is_suitable,
        timestamp=datetime.now()
    )


def rank_all_spots(
    spots: List[KiteSpot],
    forecasts: List[SpotForecast]
) -> List[SpotRating]:
    """Rate and rank all spots, returning sorted by overall score"""

    # Create forecast lookup
    forecast_map = {f.spot_id: f for f in forecasts}

    ratings = []
    for spot in spots:
        if spot.id in forecast_map:
            rating = rate_spot(spot, forecast_map[spot.id])
            ratings.append(rating)

    # Sort by overall score (descending)
    ratings.sort(key=lambda r: r.overall_score, reverse=True)

    return ratings


def get_best_spots_today(ratings: List[SpotRating], min_score: float = 60) -> List[SpotRating]:
    """Get spots with good conditions today"""
    return [r for r in ratings if r.overall_score >= min_score]


def should_notify(ratings: List[SpotRating], threshold: float = 70) -> bool:
    """Check if conditions are good enough to send notification"""
    return any(r.overall_score >= threshold for r in ratings)
