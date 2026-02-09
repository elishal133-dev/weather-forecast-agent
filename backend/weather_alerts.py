"""
Severe Weather Alert System
Monitors conditions and generates alerts for dangerous weather.
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger('weather_alerts')


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    SEVERE = "severe"
    EXTREME = "extreme"


class AlertType(Enum):
    STRONG_WIND = "strong_wind"
    EXTREME_WIND = "extreme_wind"
    LOW_VISIBILITY = "low_visibility"
    THUNDERSTORM = "thunderstorm"
    HEAT_WAVE = "heat_wave"
    COLD_WAVE = "cold_wave"
    HEAVY_RAIN = "heavy_rain"
    SANDSTORM = "sandstorm"
    HIGH_WAVES = "high_waves"
    NO_FLY = "no_fly"
    NO_KITE = "no_kite"


@dataclass
class WeatherAlert:
    """Single weather alert"""
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    title_he: str
    description: str
    description_he: str
    location: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None
    value: Optional[float] = None  # The actual measured value
    threshold: Optional[float] = None  # The threshold that was exceeded

    def to_dict(self) -> Dict:
        return {
            "type": self.alert_type.value,
            "severity": self.severity.value,
            "title": self.title,
            "title_he": self.title_he,
            "description": self.description,
            "description_he": self.description_he,
            "location": self.location,
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "value": self.value,
            "threshold": self.threshold
        }


class AlertThresholds:
    """Configurable thresholds for weather alerts"""

    # Wind thresholds (knots)
    WIND_WARNING = 25
    WIND_SEVERE = 35
    WIND_EXTREME = 50

    # Gust thresholds (knots)
    GUST_WARNING = 35
    GUST_SEVERE = 45
    GUST_EXTREME = 60

    # Visibility thresholds (km)
    VISIBILITY_WARNING = 5
    VISIBILITY_SEVERE = 2
    VISIBILITY_EXTREME = 0.5

    # Temperature thresholds (°C)
    HEAT_WARNING = 35
    HEAT_SEVERE = 40
    HEAT_EXTREME = 45
    COLD_WARNING = 5
    COLD_SEVERE = 0
    COLD_EXTREME = -5

    # Precipitation thresholds (mm/hour)
    RAIN_WARNING = 10
    RAIN_SEVERE = 25
    RAIN_EXTREME = 50

    # Wave height thresholds (meters) for kite/water sports
    WAVE_WARNING = 2.0
    WAVE_SEVERE = 3.0
    WAVE_EXTREME = 4.0

    # Flight-specific thresholds
    FLIGHT_MAX_WIND = 30
    FLIGHT_MAX_GUSTS = 40
    FLIGHT_MIN_VISIBILITY = 3
    FLIGHT_MIN_CLOUD_BASE = 1500  # feet

    # Kite-specific thresholds
    KITE_MAX_WIND = 35
    KITE_MIN_WIND = 8
    KITE_MAX_GUSTS = 45


class WeatherAlertSystem:
    """
    Monitors weather conditions and generates alerts.
    """

    def __init__(self, thresholds: AlertThresholds = None):
        self.thresholds = thresholds or AlertThresholds()
        self.active_alerts: List[WeatherAlert] = []
        self.alert_history: List[Dict] = []

    def check_conditions(self, weather_data: Dict, location: str = None) -> List[WeatherAlert]:
        """Check weather data and generate any applicable alerts"""
        alerts = []

        wind = weather_data.get("wind_speed_knots", 0)
        gusts = weather_data.get("wind_gusts_knots", 0)
        visibility = weather_data.get("visibility_km", 50)
        temp = weather_data.get("temperature_c", 20)
        precip = weather_data.get("precipitation_mm", 0)
        cloud_base = weather_data.get("cloud_base_ft", 10000)

        # Wind alerts
        if wind >= self.thresholds.WIND_EXTREME or gusts >= self.thresholds.GUST_EXTREME:
            alerts.append(WeatherAlert(
                alert_type=AlertType.EXTREME_WIND,
                severity=AlertSeverity.EXTREME,
                title="Extreme Wind Warning",
                title_he="אזהרת רוח קיצונית",
                description=f"Dangerous winds of {wind:.0f} knots with gusts to {gusts:.0f} knots",
                description_he=f"רוחות מסוכנות של {wind:.0f} קשר עם משבים עד {gusts:.0f} קשר",
                location=location,
                value=wind,
                threshold=self.thresholds.WIND_EXTREME
            ))
        elif wind >= self.thresholds.WIND_SEVERE or gusts >= self.thresholds.GUST_SEVERE:
            alerts.append(WeatherAlert(
                alert_type=AlertType.STRONG_WIND,
                severity=AlertSeverity.SEVERE,
                title="Strong Wind Warning",
                title_he="אזהרת רוח חזקה",
                description=f"Strong winds of {wind:.0f} knots with gusts to {gusts:.0f} knots",
                description_he=f"רוחות חזקות של {wind:.0f} קשר עם משבים עד {gusts:.0f} קשר",
                location=location,
                value=wind,
                threshold=self.thresholds.WIND_SEVERE
            ))
        elif wind >= self.thresholds.WIND_WARNING or gusts >= self.thresholds.GUST_WARNING:
            alerts.append(WeatherAlert(
                alert_type=AlertType.STRONG_WIND,
                severity=AlertSeverity.WARNING,
                title="Wind Advisory",
                title_he="התראת רוח",
                description=f"Wind {wind:.0f} knots, gusts {gusts:.0f} knots",
                description_he=f"רוח {wind:.0f} קשר, משבים {gusts:.0f} קשר",
                location=location,
                value=wind,
                threshold=self.thresholds.WIND_WARNING
            ))

        # Visibility alerts
        if visibility < self.thresholds.VISIBILITY_EXTREME:
            alerts.append(WeatherAlert(
                alert_type=AlertType.LOW_VISIBILITY,
                severity=AlertSeverity.EXTREME,
                title="Extreme Low Visibility",
                title_he="ראות קיצונית נמוכה",
                description=f"Visibility only {visibility:.1f} km - dangerous conditions",
                description_he=f"ראות רק {visibility:.1f} ק״מ - תנאים מסוכנים",
                location=location,
                value=visibility,
                threshold=self.thresholds.VISIBILITY_EXTREME
            ))
        elif visibility < self.thresholds.VISIBILITY_SEVERE:
            alerts.append(WeatherAlert(
                alert_type=AlertType.LOW_VISIBILITY,
                severity=AlertSeverity.SEVERE,
                title="Very Low Visibility",
                title_he="ראות נמוכה מאוד",
                description=f"Visibility {visibility:.1f} km",
                description_he=f"ראות {visibility:.1f} ק״מ",
                location=location,
                value=visibility,
                threshold=self.thresholds.VISIBILITY_SEVERE
            ))

        # Temperature alerts
        if temp >= self.thresholds.HEAT_EXTREME:
            alerts.append(WeatherAlert(
                alert_type=AlertType.HEAT_WAVE,
                severity=AlertSeverity.EXTREME,
                title="Extreme Heat Warning",
                title_he="אזהרת חום קיצוני",
                description=f"Temperature {temp:.0f}°C - life threatening",
                description_he=f"טמפרטורה {temp:.0f}°C - סכנת חיים",
                location=location,
                value=temp,
                threshold=self.thresholds.HEAT_EXTREME
            ))
        elif temp >= self.thresholds.HEAT_SEVERE:
            alerts.append(WeatherAlert(
                alert_type=AlertType.HEAT_WAVE,
                severity=AlertSeverity.SEVERE,
                title="Heat Wave",
                title_he="גל חום",
                description=f"Temperature {temp:.0f}°C",
                description_he=f"טמפרטורה {temp:.0f}°C",
                location=location,
                value=temp,
                threshold=self.thresholds.HEAT_SEVERE
            ))

        if temp <= self.thresholds.COLD_EXTREME:
            alerts.append(WeatherAlert(
                alert_type=AlertType.COLD_WAVE,
                severity=AlertSeverity.EXTREME,
                title="Extreme Cold Warning",
                title_he="אזהרת קור קיצוני",
                description=f"Temperature {temp:.0f}°C - risk of hypothermia",
                description_he=f"טמפרטורה {temp:.0f}°C - סכנת היפותרמיה",
                location=location,
                value=temp,
                threshold=self.thresholds.COLD_EXTREME
            ))

        # Heavy rain alerts
        if precip >= self.thresholds.RAIN_SEVERE:
            alerts.append(WeatherAlert(
                alert_type=AlertType.HEAVY_RAIN,
                severity=AlertSeverity.SEVERE,
                title="Heavy Rain Warning",
                title_he="אזהרת גשם כבד",
                description=f"Precipitation {precip:.1f} mm/hour",
                description_he=f"משקעים {precip:.1f} מ״מ לשעה",
                location=location,
                value=precip,
                threshold=self.thresholds.RAIN_SEVERE
            ))

        # Flight-specific alerts
        if wind >= self.thresholds.FLIGHT_MAX_WIND or gusts >= self.thresholds.FLIGHT_MAX_GUSTS:
            alerts.append(WeatherAlert(
                alert_type=AlertType.NO_FLY,
                severity=AlertSeverity.WARNING,
                title="No-Fly Conditions",
                title_he="תנאים לא מתאימים לטיסה",
                description=f"Wind {wind:.0f}kts exceeds flight limits",
                description_he=f"רוח {wind:.0f} קשר חורגת ממגבלות טיסה",
                location=location,
                value=wind,
                threshold=self.thresholds.FLIGHT_MAX_WIND
            ))

        if visibility < self.thresholds.FLIGHT_MIN_VISIBILITY:
            alerts.append(WeatherAlert(
                alert_type=AlertType.NO_FLY,
                severity=AlertSeverity.WARNING,
                title="Low Visibility - No Fly",
                title_he="ראות נמוכה - אין טיסה",
                description=f"Visibility {visibility:.1f}km below minimum",
                description_he=f"ראות {visibility:.1f} ק״מ מתחת למינימום",
                location=location,
                value=visibility,
                threshold=self.thresholds.FLIGHT_MIN_VISIBILITY
            ))

        if cloud_base < self.thresholds.FLIGHT_MIN_CLOUD_BASE:
            alerts.append(WeatherAlert(
                alert_type=AlertType.NO_FLY,
                severity=AlertSeverity.WARNING,
                title="Low Cloud Base",
                title_he="בסיס עננים נמוך",
                description=f"Cloud base {cloud_base}ft below minimum",
                description_he=f"בסיס עננים {cloud_base} רגל מתחת למינימום",
                location=location,
                value=cloud_base,
                threshold=self.thresholds.FLIGHT_MIN_CLOUD_BASE
            ))

        # Store alerts
        self.active_alerts = alerts
        if alerts:
            self._log_alerts(alerts)

        return alerts

    def check_kite_conditions(self, weather_data: Dict, location: str = None) -> List[WeatherAlert]:
        """Check conditions specifically for kite sports"""
        alerts = self.check_conditions(weather_data, location)

        wind = weather_data.get("wind_speed_knots", 0)
        gusts = weather_data.get("wind_gusts_knots", 0)

        # Too windy for kite
        if wind >= self.thresholds.KITE_MAX_WIND or gusts >= self.thresholds.KITE_MAX_GUSTS:
            alerts.append(WeatherAlert(
                alert_type=AlertType.NO_KITE,
                severity=AlertSeverity.WARNING,
                title="Too Windy for Kiting",
                title_he="רוח חזקה מדי לקייט",
                description=f"Wind {wind:.0f}kts too strong for safe kiting",
                description_he=f"רוח {wind:.0f} קשר חזקה מדי לקייט בטוח",
                location=location,
                value=wind,
                threshold=self.thresholds.KITE_MAX_WIND
            ))

        # Too light for kite
        if wind < self.thresholds.KITE_MIN_WIND and wind > 0:
            alerts.append(WeatherAlert(
                alert_type=AlertType.NO_KITE,
                severity=AlertSeverity.INFO,
                title="Light Wind",
                title_he="רוח קלה",
                description=f"Wind {wind:.0f}kts - may be too light",
                description_he=f"רוח {wind:.0f} קשר - עשויה להיות קלה מדי",
                location=location,
                value=wind,
                threshold=self.thresholds.KITE_MIN_WIND
            ))

        return alerts

    def _log_alerts(self, alerts: List[WeatherAlert]) -> None:
        """Log alerts for history"""
        for alert in alerts:
            entry = {
                "timestamp": datetime.now().isoformat(),
                **alert.to_dict()
            }
            self.alert_history.append(entry)

            # Keep only last 200 alerts
            if len(self.alert_history) > 200:
                self.alert_history = self.alert_history[-200:]

            # Log to system logger
            if alert.severity in [AlertSeverity.SEVERE, AlertSeverity.EXTREME]:
                logger.warning(f"ALERT: {alert.title} - {alert.description}")

    def get_active_alerts(self) -> List[Dict]:
        """Get currently active alerts"""
        return [a.to_dict() for a in self.active_alerts]

    def get_alert_summary(self) -> Dict:
        """Get summary of alert system"""
        severity_counts = {}
        for alert in self.alert_history[-50:]:
            sev = alert.get("severity", "unknown")
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        return {
            "active_count": len(self.active_alerts),
            "active_alerts": self.get_active_alerts(),
            "history_count": len(self.alert_history),
            "recent_by_severity": severity_counts,
            "generated_at": datetime.now().isoformat()
        }


# Global instance
alert_system = WeatherAlertSystem()
