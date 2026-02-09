"""
Forecast Accuracy Tracking System
Compares predictions with actual conditions to track source accuracy.
"""

import logging
import math
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json
import os

logger = logging.getLogger('accuracy_tracker')


@dataclass
class ForecastRecord:
    """Record of a forecast for later comparison"""
    source: str
    location_id: str
    forecast_time: datetime  # When forecast was made
    target_time: datetime    # Time the forecast is for
    predicted: Dict[str, float]
    actual: Optional[Dict[str, float]] = None
    errors: Optional[Dict[str, float]] = None


@dataclass
class SourceAccuracy:
    """Accuracy statistics for a weather source"""
    source: str
    total_forecasts: int = 0
    verified_forecasts: int = 0
    field_errors: Dict[str, List[float]] = field(default_factory=lambda: defaultdict(list))

    def add_error(self, field: str, error: float) -> None:
        self.field_errors[field].append(error)
        # Keep only last 500 errors per field
        if len(self.field_errors[field]) > 500:
            self.field_errors[field] = self.field_errors[field][-500:]

    def get_mae(self, field: str) -> Optional[float]:
        """Get Mean Absolute Error for a field"""
        errors = self.field_errors.get(field, [])
        if not errors:
            return None
        return sum(abs(e) for e in errors) / len(errors)

    def get_rmse(self, field: str) -> Optional[float]:
        """Get Root Mean Square Error for a field"""
        errors = self.field_errors.get(field, [])
        if not errors:
            return None
        return math.sqrt(sum(e**2 for e in errors) / len(errors))

    def get_accuracy_score(self) -> float:
        """
        Calculate overall accuracy score (0-100).
        Based on normalized errors across all fields.
        """
        # Expected error ranges for normalization
        expected_ranges = {
            "wind_speed_knots": 5,
            "wind_direction_deg": 30,
            "temperature_c": 2,
            "humidity_percent": 15,
            "cloud_cover_percent": 20,
            "visibility_km": 3
        }

        scores = []
        for field, expected_error in expected_ranges.items():
            mae = self.get_mae(field)
            if mae is not None:
                # Score: 100 if error is 0, 0 if error is 2x expected
                score = max(0, 100 * (1 - mae / (expected_error * 2)))
                scores.append(score)

        return sum(scores) / len(scores) if scores else 50

    def to_dict(self) -> Dict:
        return {
            "source": self.source,
            "total_forecasts": self.total_forecasts,
            "verified_forecasts": self.verified_forecasts,
            "accuracy_score": round(self.get_accuracy_score(), 1),
            "field_mae": {
                f: round(self.get_mae(f), 2) for f in self.field_errors
                if self.get_mae(f) is not None
            },
            "field_rmse": {
                f: round(self.get_rmse(f), 2) for f in self.field_errors
                if self.get_rmse(f) is not None
            }
        }


class AccuracyTracker:
    """
    Tracks forecast accuracy by comparing predictions to actual observations.
    Adjusts source weights based on historical accuracy.
    """

    # Fields to track
    TRACKED_FIELDS = [
        "wind_speed_knots",
        "wind_direction_deg",
        "temperature_c",
        "humidity_percent",
        "cloud_cover_percent",
        "visibility_km"
    ]

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or "/tmp/weather_accuracy"
        self.pending_forecasts: List[ForecastRecord] = []
        self.source_accuracy: Dict[str, SourceAccuracy] = {}
        self.location_calibration: Dict[str, Dict[str, float]] = {}

        # Try to load existing data
        self._load_data()

    def record_forecast(self, source: str, location_id: str,
                        forecast: Dict, target_time: datetime) -> None:
        """Record a forecast for later verification"""
        record = ForecastRecord(
            source=source,
            location_id=location_id,
            forecast_time=datetime.now(),
            target_time=target_time,
            predicted={f: forecast.get(f) for f in self.TRACKED_FIELDS if f in forecast}
        )

        self.pending_forecasts.append(record)

        # Initialize source if needed
        if source not in self.source_accuracy:
            self.source_accuracy[source] = SourceAccuracy(source=source)
        self.source_accuracy[source].total_forecasts += 1

        # Cleanup old pending forecasts (older than 48 hours)
        cutoff = datetime.now() - timedelta(hours=48)
        self.pending_forecasts = [
            f for f in self.pending_forecasts
            if f.target_time > cutoff
        ]

    def verify_forecast(self, source: str, location_id: str,
                        actual: Dict, observation_time: datetime) -> Optional[Dict]:
        """
        Verify a previous forecast against actual observations.
        Returns error metrics if a matching forecast was found.
        """
        # Find matching forecast (within 1 hour of target time)
        matching = None
        for forecast in self.pending_forecasts:
            if (forecast.source == source and
                forecast.location_id == location_id and
                abs((forecast.target_time - observation_time).total_seconds()) < 3600):
                matching = forecast
                break

        if not matching:
            return None

        # Calculate errors
        errors = {}
        for field in self.TRACKED_FIELDS:
            predicted = matching.predicted.get(field)
            observed = actual.get(field)

            if predicted is not None and observed is not None:
                if field == "wind_direction_deg":
                    # Circular difference for wind direction
                    diff = ((predicted - observed + 180) % 360) - 180
                    errors[field] = abs(diff)
                else:
                    errors[field] = predicted - observed

                # Record error
                if source in self.source_accuracy:
                    self.source_accuracy[source].add_error(field, errors[field])

        # Update record
        matching.actual = {f: actual.get(f) for f in self.TRACKED_FIELDS if f in actual}
        matching.errors = errors

        # Mark as verified
        if source in self.source_accuracy:
            self.source_accuracy[source].verified_forecasts += 1

        # Remove from pending
        self.pending_forecasts.remove(matching)

        # Save data periodically
        if len(self.pending_forecasts) % 10 == 0:
            self._save_data()

        return errors

    def get_source_weights(self) -> Dict[str, float]:
        """
        Get recommended source weights based on accuracy.
        Higher accuracy = higher weight.
        """
        weights = {}

        for source, accuracy in self.source_accuracy.items():
            score = accuracy.get_accuracy_score()
            # Convert 0-100 score to weight (0.5-1.5 range)
            weights[source] = 0.5 + (score / 100)

        return weights

    def get_location_calibration(self, location_id: str) -> Dict[str, float]:
        """
        Get calibration factors for a specific location.
        Returns bias corrections for each field.
        """
        return self.location_calibration.get(location_id, {})

    def update_location_calibration(self, location_id: str,
                                     source: str, errors: Dict) -> None:
        """
        Update location-specific calibration based on errors.
        Uses exponential moving average.
        """
        if location_id not in self.location_calibration:
            self.location_calibration[location_id] = {}

        alpha = 0.1  # Learning rate

        for field, error in errors.items():
            current = self.location_calibration[location_id].get(field, 0)
            # Update calibration: positive error means we over-predicted
            self.location_calibration[location_id][field] = current * (1 - alpha) + error * alpha

    def get_accuracy_report(self) -> Dict:
        """Get comprehensive accuracy report"""
        return {
            "sources": {
                source: acc.to_dict()
                for source, acc in self.source_accuracy.items()
            },
            "recommended_weights": self.get_source_weights(),
            "pending_verifications": len(self.pending_forecasts),
            "locations_calibrated": len(self.location_calibration),
            "generated_at": datetime.now().isoformat()
        }

    def _load_data(self) -> None:
        """Load existing accuracy data from disk"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            filepath = os.path.join(self.data_dir, "accuracy_data.json")
            if os.path.exists(filepath):
                with open(filepath) as f:
                    data = json.load(f)
                    self.location_calibration = data.get("calibration", {})
                    logger.info(f"Loaded accuracy data: {len(self.location_calibration)} locations")
        except Exception as e:
            logger.warning(f"Could not load accuracy data: {e}")

    def _save_data(self) -> None:
        """Save accuracy data to disk"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            filepath = os.path.join(self.data_dir, "accuracy_data.json")
            data = {
                "calibration": self.location_calibration,
                "saved_at": datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Could not save accuracy data: {e}")


# Global instance
accuracy_tracker = AccuracyTracker()
