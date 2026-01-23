from models import ForecastData, AggregatedForecast
from config import ACCURACY_WEIGHTS, CONSENSUS_THRESHOLD
from typing import List, Dict, Optional
from datetime import datetime, time, timedelta
from collections import Counter
import statistics

class ForecastAggregator:
    """Aggregates weather forecasts from multiple sources using consensus and weighting"""

    def __init__(self):
        self.weights = ACCURACY_WEIGHTS
        self.min_sources = CONSENSUS_THRESHOLD

    def aggregate_forecasts(self, all_forecasts: List[ForecastData], location: str) -> List[AggregatedForecast]:
        """
        Aggregate forecasts from multiple sources for multiple days
        Returns list of AggregatedForecast objects
        """
        # Group forecasts by date
        forecasts_by_date = self._group_by_date(all_forecasts)

        aggregated = []
        for date, forecasts in forecasts_by_date.items():
            if len(forecasts) >= self.min_sources:
                agg_forecast = self._aggregate_single_day(forecasts, location, date)
                if agg_forecast:
                    aggregated.append(agg_forecast)

        # Sort by date
        aggregated.sort(key=lambda x: x.date)
        return aggregated

    def _group_by_date(self, forecasts: List[ForecastData]) -> Dict[datetime, List[ForecastData]]:
        """Group forecasts by date"""
        grouped = {}
        for forecast in forecasts:
            date_key = forecast.date.date()
            if date_key not in grouped:
                grouped[date_key] = []
            grouped[date_key].append(forecast)
        return grouped

    def _aggregate_single_day(self, forecasts: List[ForecastData], location: str, date: datetime) -> Optional[AggregatedForecast]:
        """Aggregate forecasts for a single day"""
        try:
            # Calculate weighted averages for numeric values
            temp_high = self._weighted_average('temp_high', forecasts)
            temp_low = self._weighted_average('temp_low', forecasts)
            wind_speed = self._weighted_average('wind_speed', forecasts)
            cloud_cover = self._weighted_average('cloud_cover', forecasts)
            cloud_min_level = self._weighted_average('cloud_min_level', forecasts)
            freezing_altitude = self._weighted_average('freezing_altitude', forecasts)
            moon_illumination = self._weighted_average('moon_illumination', forecasts)

            # Get consensus for categorical/text values
            wind_direction = self._get_consensus_value('wind_direction', forecasts)

            # Get consensus for time values
            sunrise = self._get_consensus_time('sunrise', forecasts)
            sunset = self._get_consensus_time('sunset', forecasts)
            moonrise = self._get_consensus_time('moonrise', forecasts)
            moonset = self._get_consensus_time('moonset', forecasts)

            # Calculate confidence score
            confidence = self._calculate_confidence(forecasts)

            # Get list of sources used
            sources_used = [f.source for f in forecasts]

            return AggregatedForecast(
                location=location,
                date=datetime.combine(date, time()),
                temp_high=temp_high,
                temp_low=temp_low,
                wind_speed=wind_speed,
                wind_direction=wind_direction,
                cloud_cover=cloud_cover,
                cloud_min_level=cloud_min_level,
                freezing_altitude=freezing_altitude,
                sunrise=sunrise,
                sunset=sunset,
                moonrise=moonrise,
                moonset=moonset,
                moon_illumination=moon_illumination,
                confidence=confidence,
                sources_used=sources_used
            )
        except Exception as e:
            print(f"Error aggregating forecasts for {date}: {e}")
            return None

    def _weighted_average(self, field: str, forecasts: List[ForecastData]) -> float:
        """Calculate weighted average for a numeric field"""
        values = []
        weights = []

        for forecast in forecasts:
            value = getattr(forecast, field, None)
            if value is not None:
                values.append(value)
                weight = self.weights.get(forecast.source, 0.5)
                weights.append(weight)

        if not values:
            return 0.0

        # Calculate weighted average
        weighted_sum = sum(v * w for v, w in zip(values, weights))
        total_weight = sum(weights)

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def _get_consensus_value(self, field: str, forecasts: List[ForecastData]) -> str:
        """Get consensus value for categorical field using weighted voting"""
        value_weights = {}

        for forecast in forecasts:
            value = getattr(forecast, field, None)
            if value is not None:
                weight = self.weights.get(forecast.source, 0.5)
                if value in value_weights:
                    value_weights[value] += weight
                else:
                    value_weights[value] = weight

        if not value_weights:
            return "Unknown"

        # Return value with highest weight
        return max(value_weights.items(), key=lambda x: x[1])[0]

    def _get_consensus_time(self, field: str, forecasts: List[ForecastData]) -> time:
        """Get consensus time value using weighted average of minutes since midnight"""
        values = []
        weights = []

        for forecast in forecasts:
            value = getattr(forecast, field, None)
            if value is not None and isinstance(value, time):
                # Convert to minutes since midnight
                minutes = value.hour * 60 + value.minute
                values.append(minutes)
                weight = self.weights.get(forecast.source, 0.5)
                weights.append(weight)

        if not values:
            return time(0, 0)

        # Calculate weighted average
        weighted_sum = sum(v * w for v, w in zip(values, weights))
        total_weight = sum(weights)
        avg_minutes = int(weighted_sum / total_weight) if total_weight > 0 else 0

        # Convert back to time
        hours = avg_minutes // 60
        minutes = avg_minutes % 60
        return time(hours % 24, minutes)

    def _calculate_confidence(self, forecasts: List[ForecastData]) -> float:
        """
        Calculate confidence score based on agreement among sources
        Returns value between 0-100
        """
        if len(forecasts) < self.min_sources:
            return 0.0

        # Calculate agreement for temperature
        temp_highs = [f.temp_high for f in forecasts if f.temp_high is not None]
        temp_lows = [f.temp_low for f in forecasts if f.temp_low is not None]

        confidence_scores = []

        # Temperature agreement
        if len(temp_highs) >= 2:
            temp_high_std = statistics.stdev(temp_highs) if len(temp_highs) > 1 else 0
            # Lower std dev = higher confidence
            temp_confidence = max(0, 100 - (temp_high_std * 10))
            confidence_scores.append(temp_confidence)

        if len(temp_lows) >= 2:
            temp_low_std = statistics.stdev(temp_lows) if len(temp_lows) > 1 else 0
            temp_confidence = max(0, 100 - (temp_low_std * 10))
            confidence_scores.append(temp_confidence)

        # Wind speed agreement
        wind_speeds = [f.wind_speed for f in forecasts if f.wind_speed is not None]
        if len(wind_speeds) >= 2:
            wind_std = statistics.stdev(wind_speeds) if len(wind_speeds) > 1 else 0
            wind_confidence = max(0, 100 - (wind_std * 2))
            confidence_scores.append(wind_confidence)

        # Cloud cover agreement
        cloud_covers = [f.cloud_cover for f in forecasts if f.cloud_cover is not None]
        if len(cloud_covers) >= 2:
            cloud_std = statistics.stdev(cloud_covers) if len(cloud_covers) > 1 else 0
            cloud_confidence = max(0, 100 - cloud_std)
            confidence_scores.append(cloud_confidence)

        # Number of sources factor
        source_factor = min(100, (len(forecasts) / 4) * 100)
        confidence_scores.append(source_factor)

        # Return average confidence
        return sum(confidence_scores) / len(confidence_scores) if confidence_scores else 50.0
