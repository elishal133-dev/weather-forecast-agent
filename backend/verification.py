"""
Data Verification Module
Non-blocking async validation for all weather/forecast data
Runs in background to verify data integrity without slowing down responses
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('verification')


class VerificationLevel(Enum):
    """Severity of verification issues"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class VerificationResult:
    """Result of a data verification check"""
    field: str
    value: Any
    level: VerificationLevel
    message: str
    timestamp: datetime


class DataVerifier:
    """
    Async data verification service
    Validates weather data without blocking main request flow
    """

    # Reasonable ranges for weather data (Israel region)
    WIND_SPEED_RANGE = (0, 80)  # knots
    WIND_GUSTS_RANGE = (0, 100)  # knots
    WAVE_HEIGHT_RANGE = (0, 10)  # meters
    TEMPERATURE_RANGE = (-10, 50)  # celsius
    VISIBILITY_RANGE = (0, 100)  # km
    CLOUD_COVER_RANGE = (0, 100)  # percent
    HUMIDITY_RANGE = (0, 100)  # percent
    MOON_ILLUMINATION_RANGE = (0, 100)  # percent

    def __init__(self, max_issues: int = 100):
        self.issues: List[VerificationResult] = []
        self.max_issues = max_issues
        self._lock = asyncio.Lock()
        self.total_checks = 0
        self.failed_checks = 0

    def _add_issue(self, result: VerificationResult):
        """Add verification issue with thread safety"""
        if len(self.issues) < self.max_issues:
            self.issues.append(result)
        self.failed_checks += 1

        # Log based on severity
        if result.level == VerificationLevel.CRITICAL:
            logger.error(f"[CRITICAL] {result.field}: {result.message} (value={result.value})")
        elif result.level == VerificationLevel.ERROR:
            logger.warning(f"[ERROR] {result.field}: {result.message} (value={result.value})")
        elif result.level == VerificationLevel.WARNING:
            logger.info(f"[WARNING] {result.field}: {result.message} (value={result.value})")

    def _check_range(
        self,
        field: str,
        value: Any,
        min_val: float,
        max_val: float,
        allow_none: bool = True
    ) -> bool:
        """Check if value is within expected range"""
        self.total_checks += 1

        if value is None:
            if not allow_none:
                self._add_issue(VerificationResult(
                    field=field,
                    value=value,
                    level=VerificationLevel.WARNING,
                    message=f"Value is None (expected {min_val}-{max_val})",
                    timestamp=datetime.now()
                ))
                return False
            return True

        try:
            num_value = float(value)
            if num_value < min_val or num_value > max_val:
                level = VerificationLevel.ERROR if (
                    num_value < min_val * 0.5 or num_value > max_val * 1.5
                ) else VerificationLevel.WARNING

                self._add_issue(VerificationResult(
                    field=field,
                    value=value,
                    level=level,
                    message=f"Out of range [{min_val}, {max_val}]",
                    timestamp=datetime.now()
                ))
                return False
            return True
        except (TypeError, ValueError):
            self._add_issue(VerificationResult(
                field=field,
                value=value,
                level=VerificationLevel.ERROR,
                message=f"Invalid numeric value",
                timestamp=datetime.now()
            ))
            return False

    def _check_not_none(self, field: str, value: Any) -> bool:
        """Check if required value is not None"""
        self.total_checks += 1
        if value is None:
            self._add_issue(VerificationResult(
                field=field,
                value=value,
                level=VerificationLevel.ERROR,
                message="Required value is None",
                timestamp=datetime.now()
            ))
            return False
        return True

    def _check_consistency(
        self,
        field1: str,
        value1: float,
        field2: str,
        value2: float,
        relation: str = "lte"
    ) -> bool:
        """Check logical consistency between two values"""
        self.total_checks += 1

        if value1 is None or value2 is None:
            return True

        valid = True
        if relation == "lte" and value1 > value2:
            valid = False
        elif relation == "gte" and value1 < value2:
            valid = False
        elif relation == "lt" and value1 >= value2:
            valid = False
        elif relation == "gt" and value1 <= value2:
            valid = False

        if not valid:
            self._add_issue(VerificationResult(
                field=f"{field1} vs {field2}",
                value=f"{value1} vs {value2}",
                level=VerificationLevel.WARNING,
                message=f"Inconsistent: {field1}={value1} should be {relation} {field2}={value2}",
                timestamp=datetime.now()
            ))
        return valid

    async def verify_wind_data(self, wind_data: Dict[str, Any], spot_id: str = "") -> bool:
        """Verify wind data integrity"""
        prefix = f"wind[{spot_id}]" if spot_id else "wind"
        all_valid = True

        all_valid &= self._check_range(
            f"{prefix}.speed",
            wind_data.get("wind_speed_knots") or wind_data.get("speed_knots"),
            *self.WIND_SPEED_RANGE
        )
        all_valid &= self._check_range(
            f"{prefix}.gusts",
            wind_data.get("wind_gusts_knots") or wind_data.get("gusts_knots"),
            *self.WIND_GUSTS_RANGE
        )

        # Gusts should be >= wind speed
        speed = wind_data.get("wind_speed_knots") or wind_data.get("speed_knots")
        gusts = wind_data.get("wind_gusts_knots") or wind_data.get("gusts_knots")
        if speed is not None and gusts is not None:
            all_valid &= self._check_consistency(
                f"{prefix}.speed", speed,
                f"{prefix}.gusts", gusts,
                "lte"
            )

        # Wind direction should be 0-360
        direction = wind_data.get("wind_direction") or wind_data.get("direction")
        if direction is not None:
            all_valid &= self._check_range(f"{prefix}.direction", direction, 0, 360)

        return all_valid

    async def verify_wave_data(self, wave_data: Dict[str, Any], spot_id: str = "") -> bool:
        """Verify wave data integrity"""
        if wave_data is None:
            return True  # Wave data may not be available for inland spots

        prefix = f"wave[{spot_id}]" if spot_id else "wave"
        all_valid = True

        all_valid &= self._check_range(
            f"{prefix}.height",
            wave_data.get("wave_height_m") or wave_data.get("height_m"),
            *self.WAVE_HEIGHT_RANGE
        )

        period = wave_data.get("wave_period_s") or wave_data.get("period_s")
        if period is not None:
            all_valid &= self._check_range(f"{prefix}.period", period, 0, 30)

        return all_valid

    async def verify_helicopter_conditions(self, conditions: Dict[str, Any], location: str = "") -> bool:
        """Verify helicopter forecast data"""
        prefix = f"heli[{location}]" if location else "heli"
        all_valid = True

        all_valid &= self._check_range(
            f"{prefix}.wind",
            conditions.get("wind_speed_knots"),
            *self.WIND_SPEED_RANGE
        )
        all_valid &= self._check_range(
            f"{prefix}.gusts",
            conditions.get("wind_gusts_knots"),
            *self.WIND_GUSTS_RANGE
        )
        all_valid &= self._check_range(
            f"{prefix}.visibility",
            conditions.get("visibility_km"),
            *self.VISIBILITY_RANGE
        )
        all_valid &= self._check_range(
            f"{prefix}.cloud_cover",
            conditions.get("cloud_cover_percent"),
            *self.CLOUD_COVER_RANGE
        )
        all_valid &= self._check_range(
            f"{prefix}.temperature",
            conditions.get("temperature_c"),
            *self.TEMPERATURE_RANGE
        )
        all_valid &= self._check_range(
            f"{prefix}.humidity",
            conditions.get("humidity_percent"),
            *self.HUMIDITY_RANGE
        )

        # Cloud base should be non-negative
        cloud_base = conditions.get("cloud_base_ft")
        if cloud_base is not None:
            all_valid &= self._check_range(f"{prefix}.cloud_base", cloud_base, 0, 50000)

        # Score should be 0-100
        score = conditions.get("score")
        if score is not None:
            all_valid &= self._check_range(f"{prefix}.score", score, 0, 100)

        return all_valid

    async def verify_stargazing_conditions(self, conditions: Dict[str, Any], location: str = "") -> bool:
        """Verify stargazing forecast data"""
        prefix = f"stars[{location}]" if location else "stars"
        all_valid = True

        all_valid &= self._check_range(
            f"{prefix}.moon_illumination",
            conditions.get("moon_illumination"),
            *self.MOON_ILLUMINATION_RANGE
        )
        all_valid &= self._check_range(
            f"{prefix}.cloud_cover",
            conditions.get("cloud_cover_night"),
            *self.CLOUD_COVER_RANGE
        )
        all_valid &= self._check_range(
            f"{prefix}.score",
            conditions.get("score"),
            0, 100
        )

        return all_valid

    async def verify_kite_ranking(self, ranking: Dict[str, Any]) -> bool:
        """Verify kite spot ranking data"""
        spot_id = ranking.get("spot_id", "unknown")
        prefix = f"kite[{spot_id}]"
        all_valid = True

        all_valid &= await self.verify_wind_data({
            "wind_speed_knots": ranking.get("wind_speed_knots"),
            "wind_gusts_knots": ranking.get("wind_gusts_knots"),
            "wind_direction": ranking.get("wind_direction_deg")
        }, spot_id)

        all_valid &= await self.verify_wave_data({
            "wave_height_m": ranking.get("wave_height_m")
        }, spot_id)

        # Scores should be 0-100
        for score_field in ["overall_score", "wind_score", "wave_score", "direction_score"]:
            score = ranking.get(score_field)
            if score is not None:
                all_valid &= self._check_range(f"{prefix}.{score_field}", score, 0, 100)

        return all_valid

    def get_summary(self) -> Dict[str, Any]:
        """Get verification summary"""
        return {
            "total_checks": self.total_checks,
            "failed_checks": self.failed_checks,
            "success_rate": round((1 - self.failed_checks / max(self.total_checks, 1)) * 100, 2),
            "issues_count": len(self.issues),
            "critical_count": sum(1 for i in self.issues if i.level == VerificationLevel.CRITICAL),
            "error_count": sum(1 for i in self.issues if i.level == VerificationLevel.ERROR),
            "warning_count": sum(1 for i in self.issues if i.level == VerificationLevel.WARNING),
            "recent_issues": [
                {
                    "field": i.field,
                    "value": str(i.value),
                    "level": i.level.value,
                    "message": i.message,
                    "timestamp": i.timestamp.isoformat()
                }
                for i in self.issues[-10:]
            ]
        }

    def clear(self):
        """Clear verification state"""
        self.issues.clear()
        self.total_checks = 0
        self.failed_checks = 0


# Global verifier instance
verifier = DataVerifier()


async def verify_kite_rankings_background(rankings: List[Dict[str, Any]]):
    """Background task to verify all kite rankings"""
    for ranking in rankings:
        await verifier.verify_kite_ranking(ranking)
    logger.info(f"Kite verification complete: {verifier.get_summary()['success_rate']}% success rate")


async def verify_helicopter_forecast_background(forecast: Dict[str, Any]):
    """Background task to verify helicopter forecast"""
    location = forecast.get("location", {}).get("name", "unknown")
    for condition in forecast.get("forecast", []):
        await verifier.verify_helicopter_conditions(condition, location)
    logger.info(f"Helicopter verification complete for {location}")


async def verify_stars_forecast_background(forecast: Dict[str, Any]):
    """Background task to verify stargazing forecast"""
    location = forecast.get("location", {}).get("name", "unknown")
    for day in forecast.get("forecast", []):
        await verifier.verify_stargazing_conditions(day, location)
    logger.info(f"Stars verification complete for {location}")


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division that handles zero denominator"""
    if denominator == 0:
        logger.warning(f"Division by zero avoided: {numerator}/{denominator}, returning {default}")
        return default
    return numerator / denominator


def safe_average(values: List[float], default: float = 0.0) -> float:
    """Safe average that handles empty lists"""
    if not values:
        return default
    return sum(values) / len(values)


def clamp(value: float, min_val: float, max_val: float) -> float:
    """Clamp value to range"""
    return max(min_val, min(max_val, value))
