"""
User Feedback System
Allows users to report actual conditions to improve forecast accuracy.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import os

logger = logging.getLogger('user_feedback')


class FeedbackType(Enum):
    WIND_STRONGER = "wind_stronger"
    WIND_WEAKER = "wind_weaker"
    WIND_DIRECTION_WRONG = "wind_direction_wrong"
    TEMPERATURE_HIGHER = "temp_higher"
    TEMPERATURE_LOWER = "temp_lower"
    MORE_CLOUDS = "more_clouds"
    LESS_CLOUDS = "less_clouds"
    VISIBILITY_WORSE = "visibility_worse"
    VISIBILITY_BETTER = "visibility_better"
    RAIN_UNEXPECTED = "rain_unexpected"
    NO_RAIN = "no_rain"
    CONDITIONS_PERFECT = "perfect"
    CONDITIONS_WRONG = "wrong"


@dataclass
class UserFeedback:
    """Single user feedback entry"""
    id: str
    location_id: str
    timestamp: datetime
    feedback_type: FeedbackType
    predicted: Optional[Dict[str, float]] = None
    reported: Optional[Dict[str, float]] = None
    comment: Optional[str] = None
    user_id: Optional[str] = None  # Anonymous by default

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "location_id": self.location_id,
            "timestamp": self.timestamp.isoformat(),
            "feedback_type": self.feedback_type.value,
            "predicted": self.predicted,
            "reported": self.reported,
            "comment": self.comment
        }


class UserFeedbackSystem:
    """
    Collects and processes user feedback to improve forecasts.
    """

    def __init__(self, data_dir: str = None):
        self.data_dir = data_dir or "/tmp/weather_feedback"
        self.feedback_log: List[UserFeedback] = []
        self.location_adjustments: Dict[str, Dict[str, float]] = {}
        self.feedback_count = 0

        self._load_data()

    def submit_feedback(self, location_id: str, feedback_type: str,
                        predicted: Dict = None, reported: Dict = None,
                        comment: str = None, user_id: str = None) -> Dict:
        """Submit user feedback about conditions"""
        try:
            fb_type = FeedbackType(feedback_type)
        except ValueError:
            return {"error": f"Invalid feedback type: {feedback_type}"}

        self.feedback_count += 1
        feedback = UserFeedback(
            id=f"fb_{self.feedback_count}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            location_id=location_id,
            timestamp=datetime.now(),
            feedback_type=fb_type,
            predicted=predicted,
            reported=reported,
            comment=comment,
            user_id=user_id
        )

        self.feedback_log.append(feedback)

        # Keep only last 1000 feedback entries
        if len(self.feedback_log) > 1000:
            self.feedback_log = self.feedback_log[-1000:]

        # Process feedback to update adjustments
        self._process_feedback(feedback)

        # Periodically save
        if len(self.feedback_log) % 10 == 0:
            self._save_data()

        logger.info(f"Feedback received for {location_id}: {feedback_type}")

        return {
            "status": "received",
            "feedback_id": feedback.id,
            "message": "Thank you for your feedback!"
        }

    def _process_feedback(self, feedback: UserFeedback) -> None:
        """Process feedback to update location adjustments"""
        location = feedback.location_id

        if location not in self.location_adjustments:
            self.location_adjustments[location] = {
                "wind_bias": 0,
                "temp_bias": 0,
                "cloud_bias": 0,
                "feedback_count": 0
            }

        adj = self.location_adjustments[location]
        adj["feedback_count"] += 1

        # Learning rate - decreases as we get more feedback
        alpha = max(0.05, 0.3 / (1 + adj["feedback_count"] / 20))

        # Apply adjustments based on feedback type
        if feedback.feedback_type == FeedbackType.WIND_STRONGER:
            adj["wind_bias"] = adj["wind_bias"] * (1 - alpha) + 3 * alpha  # Under-predicting by ~3 knots
        elif feedback.feedback_type == FeedbackType.WIND_WEAKER:
            adj["wind_bias"] = adj["wind_bias"] * (1 - alpha) - 3 * alpha  # Over-predicting

        elif feedback.feedback_type == FeedbackType.TEMPERATURE_HIGHER:
            adj["temp_bias"] = adj["temp_bias"] * (1 - alpha) + 2 * alpha  # Under-predicting by ~2°C
        elif feedback.feedback_type == FeedbackType.TEMPERATURE_LOWER:
            adj["temp_bias"] = adj["temp_bias"] * (1 - alpha) - 2 * alpha

        elif feedback.feedback_type == FeedbackType.MORE_CLOUDS:
            adj["cloud_bias"] = adj["cloud_bias"] * (1 - alpha) + 15 * alpha  # Under-predicting by ~15%
        elif feedback.feedback_type == FeedbackType.LESS_CLOUDS:
            adj["cloud_bias"] = adj["cloud_bias"] * (1 - alpha) - 15 * alpha

        # If user reports actual values, use them directly
        if feedback.predicted and feedback.reported:
            for field in ["wind_speed_knots", "temperature_c", "cloud_cover_percent"]:
                if field in feedback.predicted and field in feedback.reported:
                    error = feedback.reported[field] - feedback.predicted[field]
                    if field == "wind_speed_knots":
                        adj["wind_bias"] = adj["wind_bias"] * (1 - alpha) + error * alpha
                    elif field == "temperature_c":
                        adj["temp_bias"] = adj["temp_bias"] * (1 - alpha) + error * alpha
                    elif field == "cloud_cover_percent":
                        adj["cloud_bias"] = adj["cloud_bias"] * (1 - alpha) + error * alpha

    def get_location_adjustment(self, location_id: str) -> Dict[str, float]:
        """Get adjustment factors for a location based on feedback"""
        return self.location_adjustments.get(location_id, {
            "wind_bias": 0,
            "temp_bias": 0,
            "cloud_bias": 0
        })

    def apply_adjustments(self, location_id: str, weather_data: Dict) -> Dict:
        """Apply learned adjustments to weather data"""
        adj = self.get_location_adjustment(location_id)

        if not adj or adj.get("feedback_count", 0) < 5:
            # Not enough feedback yet
            return weather_data

        adjusted = weather_data.copy()

        if "wind_speed_knots" in adjusted and adj.get("wind_bias"):
            adjusted["wind_speed_knots"] = max(0, adjusted["wind_speed_knots"] + adj["wind_bias"])

        if "temperature_c" in adjusted and adj.get("temp_bias"):
            adjusted["temperature_c"] = adjusted["temperature_c"] + adj["temp_bias"]

        if "cloud_cover_percent" in adjusted and adj.get("cloud_bias"):
            adjusted["cloud_cover_percent"] = max(0, min(100,
                adjusted["cloud_cover_percent"] + adj["cloud_bias"]))

        adjusted["adjustments_applied"] = True

        return adjusted

    def get_feedback_stats(self, location_id: str = None) -> Dict:
        """Get feedback statistics"""
        if location_id:
            location_feedback = [f for f in self.feedback_log if f.location_id == location_id]
        else:
            location_feedback = self.feedback_log

        # Count by type
        type_counts = {}
        for fb in location_feedback[-100:]:  # Last 100
            t = fb.feedback_type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_feedback": len(self.feedback_log),
            "location_count": len(self.location_adjustments),
            "recent_by_type": type_counts,
            "locations_with_adjustments": [
                {"location": loc, **adj}
                for loc, adj in self.location_adjustments.items()
                if adj.get("feedback_count", 0) >= 5
            ],
            "generated_at": datetime.now().isoformat()
        }

    def get_recent_feedback(self, limit: int = 20) -> List[Dict]:
        """Get recent feedback entries"""
        return [fb.to_dict() for fb in self.feedback_log[-limit:]]

    def _load_data(self) -> None:
        """Load existing feedback data"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            filepath = os.path.join(self.data_dir, "feedback_data.json")
            if os.path.exists(filepath):
                with open(filepath) as f:
                    data = json.load(f)
                    self.location_adjustments = data.get("adjustments", {})
                    self.feedback_count = data.get("count", 0)
                    logger.info(f"Loaded feedback data: {len(self.location_adjustments)} locations")
        except Exception as e:
            logger.warning(f"Could not load feedback data: {e}")

    def _save_data(self) -> None:
        """Save feedback data"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            filepath = os.path.join(self.data_dir, "feedback_data.json")
            data = {
                "adjustments": self.location_adjustments,
                "count": self.feedback_count,
                "saved_at": datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Could not save feedback data: {e}")


# Global instance
feedback_system = UserFeedbackSystem()


# Feedback type descriptions for API
FEEDBACK_TYPES = {
    "wind_stronger": {"he": "רוח חזקה יותר מהתחזית", "en": "Wind stronger than forecast"},
    "wind_weaker": {"he": "רוח חלשה יותר מהתחזית", "en": "Wind weaker than forecast"},
    "wind_direction_wrong": {"he": "כיוון רוח שגוי", "en": "Wind direction was wrong"},
    "temp_higher": {"he": "חם יותר מהתחזית", "en": "Temperature higher than forecast"},
    "temp_lower": {"he": "קר יותר מהתחזית", "en": "Temperature lower than forecast"},
    "more_clouds": {"he": "יותר עננים מהתחזית", "en": "More clouds than forecast"},
    "less_clouds": {"he": "פחות עננים מהתחזית", "en": "Fewer clouds than forecast"},
    "visibility_worse": {"he": "ראות גרועה יותר", "en": "Visibility worse than forecast"},
    "visibility_better": {"he": "ראות טובה יותר", "en": "Visibility better than forecast"},
    "rain_unexpected": {"he": "גשם לא צפוי", "en": "Unexpected rain"},
    "no_rain": {"he": "לא ירד גשם כצפוי", "en": "Expected rain didn't occur"},
    "perfect": {"he": "תחזית מדויקת!", "en": "Forecast was perfect!"},
    "wrong": {"he": "תחזית שגויה", "en": "Forecast was wrong"}
}
