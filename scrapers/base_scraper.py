from abc import ABC, abstractmethod
from models import ForecastData
from typing import List
from datetime import time
import requests
from bs4 import BeautifulSoup
import re

class BaseScraper(ABC):
    """Base class for all weather scrapers"""

    def __init__(self, source_name: str):
        self.source_name = source_name
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    @abstractmethod
    def scrape(self, location: str) -> List[ForecastData]:
        """
        Scrape weather forecast for the given location
        Returns list of ForecastData objects (typically 5-7 days)
        """
        pass

    def get_html(self, url: str) -> BeautifulSoup:
        """Fetch and parse HTML from URL"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def clean_temp(self, temp_str: str) -> float:
        """Clean and convert temperature string to float"""
        try:
            # Remove common characters and convert to float
            cleaned = temp_str.replace('°', '').replace('C', '').replace('°C', '').strip()
            return float(cleaned)
        except:
            return None

    def clean_wind_speed(self, wind_str: str) -> float:
        """Clean and convert wind speed string to float"""
        try:
            # Extract numbers from string
            numbers = re.findall(r'\d+\.?\d*', wind_str)
            if numbers:
                return float(numbers[0])
            return None
        except:
            return None

    def clean_cloud_cover(self, cloud_str: str) -> float:
        """Clean and convert cloud cover string to percentage (0-100)"""
        try:
            # Extract percentage from string
            numbers = re.findall(r'\d+\.?\d*', cloud_str)
            if numbers:
                return float(numbers[0])
            return None
        except:
            return None

    def clean_cloud_level(self, level_str: str) -> float:
        """Clean and convert cloud minimum level to meters"""
        try:
            # Extract numbers from string (could be in meters or feet)
            numbers = re.findall(r'\d+\.?\d*', level_str)
            if numbers:
                value = float(numbers[0])
                # If value is too large, it might be in feet - convert to meters
                if value > 10000:
                    value = value * 0.3048  # feet to meters
                return value
            return None
        except:
            return None

    def parse_time(self, time_str: str) -> time:
        """Parse time string to time object"""
        try:
            # Remove common characters
            cleaned = time_str.strip().upper()

            # Try common time formats
            for fmt in ['%H:%M', '%I:%M %p', '%H:%M:%S', '%I:%M:%S %p']:
                try:
                    parsed = __import__('datetime').datetime.strptime(cleaned, fmt).time()
                    return parsed
                except:
                    continue

            # Try to extract HH:MM pattern
            match = re.search(r'(\d{1,2}):(\d{2})', time_str)
            if match:
                hour, minute = int(match.group(1)), int(match.group(2))
                # Check for AM/PM
                if 'PM' in cleaned and hour < 12:
                    hour += 12
                elif 'AM' in cleaned and hour == 12:
                    hour = 0
                return time(hour, minute)

            return None
        except:
            return None

    def clean_moon_illumination(self, moon_str: str) -> float:
        """Clean and convert moon illumination to percentage (0-100)"""
        try:
            # Extract percentage from string
            numbers = re.findall(r'\d+\.?\d*', moon_str)
            if numbers:
                return float(numbers[0])
            return None
        except:
            return None
