"""
Moon data calculator using accurate astronomical calculations via PyEphem
Provides moonrise, moonset, and moon illumination for any location and date
"""
import ephem
from datetime import datetime, date, time, timedelta
import pytz

class MoonCalculator:
    """Calculate accurate moon data for any location and date using PyEphem"""

    def __init__(self):
        # Location coordinates for Israeli cities
        self.locations = {
            'Tel Aviv': {'lat': '32.0853', 'lon': '34.7818', 'tz': 'Asia/Jerusalem'},
            'Jerusalem': {'lat': '31.7683', 'lon': '35.2137', 'tz': 'Asia/Jerusalem'},
            'Haifa': {'lat': '32.7940', 'lon': '34.9896', 'tz': 'Asia/Jerusalem'},
            'Beer Sheva': {'lat': '31.2518', 'lon': '34.7913', 'tz': 'Asia/Jerusalem'}
        }

    def get_moon_data(self, location_name: str, target_date: date):
        """
        Get accurate moon data for a specific location and date using PyEphem
        Returns: dict with moonrise, moonset, moon_illumination
        """
        coords = self.locations.get(location_name, self.locations['Tel Aviv'])

        try:
            # Create observer for the location
            observer = ephem.Observer()
            observer.lat = coords['lat']
            observer.lon = coords['lon']

            # Set date to noon of target date to get moonrise/moonset for that day
            tz = pytz.timezone(coords['tz'])
            local_noon = tz.localize(datetime.combine(target_date, time(12, 0)))
            observer.date = local_noon.astimezone(pytz.UTC)

            # Create moon object
            moon = ephem.Moon()
            moon.compute(observer)

            # Calculate moon illumination (0-100%)
            illumination = moon.phase

            # Calculate moonrise for the target date
            try:
                # Get next moonrise after midnight of target date
                midnight = tz.localize(datetime.combine(target_date, time(0, 0)))
                observer.date = midnight.astimezone(pytz.UTC)

                moonrise_utc = observer.next_rising(ephem.Moon())
                moonrise_dt = ephem.Date(moonrise_utc).datetime()
                moonrise_local = pytz.UTC.localize(moonrise_dt).astimezone(tz)

                # Only use if it's on the target date
                if moonrise_local.date() == target_date:
                    moonrise_time = moonrise_local.time()
                else:
                    # Try previous rising
                    observer.date = midnight.astimezone(pytz.UTC)
                    moonrise_utc = observer.previous_rising(ephem.Moon())
                    moonrise_dt = ephem.Date(moonrise_utc).datetime()
                    moonrise_local = pytz.UTC.localize(moonrise_dt).astimezone(tz)
                    if moonrise_local.date() == target_date:
                        moonrise_time = moonrise_local.time()
                    else:
                        moonrise_time = None
            except (ephem.AlwaysUpError, ephem.NeverUpError):
                moonrise_time = None

            # Calculate moonset for the target date
            try:
                observer.date = midnight.astimezone(pytz.UTC)
                moonset_utc = observer.next_setting(ephem.Moon())
                moonset_dt = ephem.Date(moonset_utc).datetime()
                moonset_local = pytz.UTC.localize(moonset_dt).astimezone(tz)

                # Only use if it's on the target date
                if moonset_local.date() == target_date:
                    moonset_time = moonset_local.time()
                else:
                    # Try previous setting
                    observer.date = midnight.astimezone(pytz.UTC)
                    moonset_utc = observer.previous_setting(ephem.Moon())
                    moonset_dt = ephem.Date(moonset_utc).datetime()
                    moonset_local = pytz.UTC.localize(moonset_dt).astimezone(tz)
                    if moonset_local.date() == target_date:
                        moonset_time = moonset_local.time()
                    else:
                        moonset_time = None
            except (ephem.AlwaysUpError, ephem.NeverUpError):
                moonset_time = None

            return {
                'moonrise': moonrise_time,
                'moonset': moonset_time,
                'moon_illumination': round(illumination, 1)
            }

        except Exception as e:
            print(f"Error calculating moon data for {location_name} on {target_date}: {e}")
            import traceback
            traceback.print_exc()
            return {
                'moonrise': None,
                'moonset': None,
                'moon_illumination': None
            }

    def get_sun_data(self, location_name: str, target_date: date):
        """
        Get accurate sunrise and sunset times for a specific location and date
        Returns: dict with sunrise, sunset
        """
        coords = self.locations.get(location_name, self.locations['Tel Aviv'])

        try:
            # Create observer for the location
            observer = ephem.Observer()
            observer.lat = coords['lat']
            observer.lon = coords['lon']

            # Set date to midnight of target date
            tz = pytz.timezone(coords['tz'])
            midnight = tz.localize(datetime.combine(target_date, time(0, 0)))
            observer.date = midnight.astimezone(pytz.UTC)

            # Calculate sunrise
            sunrise_utc = observer.next_rising(ephem.Sun())
            sunrise_dt = ephem.Date(sunrise_utc).datetime()
            sunrise_local = pytz.UTC.localize(sunrise_dt).astimezone(tz)
            sunrise_time = sunrise_local.time()

            # Calculate sunset
            observer.date = midnight.astimezone(pytz.UTC)
            sunset_utc = observer.next_setting(ephem.Sun())
            sunset_dt = ephem.Date(sunset_utc).datetime()
            sunset_local = pytz.UTC.localize(sunset_dt).astimezone(tz)
            sunset_time = sunset_local.time()

            return {
                'sunrise': sunrise_time,
                'sunset': sunset_time
            }

        except Exception as e:
            print(f"Error calculating sun data for {location_name} on {target_date}: {e}")
            return {
                'sunrise': None,
                'sunset': None
            }

    def get_moon_data_for_days(self, location_name: str, start_date: date, days: int = 7):
        """
        Get moon data for multiple days
        Returns: list of dicts with date and moon data
        """
        results = []
        for i in range(days):
            target_date = start_date + timedelta(days=i)
            moon_data = self.get_moon_data(location_name, target_date)
            moon_data['date'] = target_date
            results.append(moon_data)

        return results
