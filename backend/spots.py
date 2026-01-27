"""
Israeli Kite Surfing Spots Database
Complete list of kite spots with coordinates, optimal conditions, and metadata
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class Region(Enum):
    NORTH = "north"           # Northern Mediterranean coast
    CENTRAL = "central"       # Central Mediterranean coast
    SOUTH = "south"           # Southern Mediterranean coast
    EILAT = "eilat"           # Red Sea
    KINNERET = "kinneret"     # Sea of Galilee


class Difficulty(Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ALL_LEVELS = "all_levels"


class WindDirection(Enum):
    N = "N"
    NE = "NE"
    E = "E"
    SE = "SE"
    S = "S"
    SW = "SW"
    W = "W"
    NW = "NW"


@dataclass
class KiteSpot:
    id: str
    name: str
    name_he: str                    # Hebrew name
    region: Region
    latitude: float
    longitude: float
    optimal_wind_directions: List[WindDirection]
    difficulty: Difficulty
    description: str
    water_type: str                 # "waves", "flat", "mixed"
    best_months: List[int]          # 1-12
    hazards: Optional[str] = None
    facilities: Optional[str] = None


# Complete list of Israeli kite spots
KITE_SPOTS: List[KiteSpot] = [
    # ============ NORTHERN COAST ============
    KiteSpot(
        id="betzet",
        name="Betzet Beach",
        name_he="חוף בצת",
        region=Region.NORTH,
        latitude=33.0825,
        longitude=35.1025,
        optimal_wind_directions=[WindDirection.NW, WindDirection.N],
        difficulty=Difficulty.INTERMEDIATE,
        description="Northernmost kite spot in Israel. Strongest winds during north wind season, starts early morning. Less crowded.",
        water_type="waves",
        best_months=[10, 11, 12, 1, 2, 3, 4],
        hazards="Rocky areas",
        facilities="Parking"
    ),
    KiteSpot(
        id="achziv",
        name="Achziv Beach",
        name_he="חוף אכזיב",
        region=Region.NORTH,
        latitude=33.0489,
        longitude=35.1017,
        optimal_wind_directions=[WindDirection.NW, WindDirection.W],
        difficulty=Difficulty.INTERMEDIATE,
        description="Beautiful beach near Nahariya with good wave conditions.",
        water_type="waves",
        best_months=[10, 11, 12, 1, 2, 3, 4],
        hazards="Rocks, currents",
        facilities="National park facilities"
    ),
    KiteSpot(
        id="acre",
        name="Acre Fortress Beach",
        name_he="חוף המבצר עכו",
        region=Region.NORTH,
        latitude=32.9280,
        longitude=35.0670,
        optimal_wind_directions=[WindDirection.NW, WindDirection.W],
        difficulty=Difficulty.BEGINNER,
        description="Popular spot with long sandy beach. Wind arrives early and strong. Good for beginners.",
        water_type="mixed",
        best_months=[10, 11, 12, 1, 2, 3, 4],
        hazards="Crowded on good days",
        facilities="Restaurants, parking, restrooms"
    ),
    KiteSpot(
        id="kiryat_yam",
        name="Kiryat Yam",
        name_he="קרית ים",
        region=Region.NORTH,
        latitude=32.8475,
        longitude=35.0650,
        optimal_wind_directions=[WindDirection.NW, WindDirection.W],
        difficulty=Difficulty.ALL_LEVELS,
        description="Most kite days per year in Mediterranean Israel! Operates year-round. Home to Surf Cycle club.",
        water_type="mixed",
        best_months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        hazards="Crowded",
        facilities="Surf club, parking, showers"
    ),
    KiteSpot(
        id="bat_galim",
        name="Bat Galim",
        name_he="בת גלים",
        region=Region.NORTH,
        latitude=32.8280,
        longitude=34.9710,
        optimal_wind_directions=[WindDirection.NW, WindDirection.W],
        difficulty=Difficulty.ADVANCED,
        description="Queen of kite waves in Israel! Biggest waves on the coast. NOT for beginners - dangerous conditions.",
        water_type="waves",
        best_months=[10, 11, 12, 1, 2, 3],
        hazards="Big waves, rocks, strong currents. Advanced only!",
        facilities="Cable car area, restaurants"
    ),
    KiteSpot(
        id="dado",
        name="Dado Beach",
        name_he="חוף דדו",
        region=Region.NORTH,
        latitude=32.8100,
        longitude=34.9680,
        optimal_wind_directions=[WindDirection.NW, WindDirection.W],
        difficulty=Difficulty.INTERMEDIATE,
        description="Popular Haifa beach with promenade, restaurants and good conditions.",
        water_type="mixed",
        best_months=[10, 11, 12, 1, 2, 3, 4],
        hazards="Swimmers in summer",
        facilities="Full beach facilities, promenade"
    ),

    # ============ CENTRAL COAST ============
    KiteSpot(
        id="sdot_yam",
        name="Sdot Yam",
        name_he="שדות ים",
        region=Region.CENTRAL,
        latitude=32.4950,
        longitude=34.8900,
        optimal_wind_directions=[WindDirection.N, WindDirection.NW],
        difficulty=Difficulty.ALL_LEVELS,
        description="Near Caesarea. Northern part has lagoon-like flat water protected by rocks. Great for flat water lovers.",
        water_type="flat",
        best_months=[10, 11, 12, 1, 2, 3, 4],
        hazards="Rocks in water",
        facilities="Parking"
    ),
    KiteSpot(
        id="beit_yanai",
        name="Beit Yanai",
        name_he="בית ינאי",
        region=Region.CENTRAL,
        latitude=32.4025,
        longitude=34.8575,
        optimal_wind_directions=[WindDirection.NW, WindDirection.W],
        difficulty=Difficulty.BEGINNER,
        description="Most popular kite spot in Israel! First official kite beach. ~700m rideable sandy beach. Perfect for beginners.",
        water_type="mixed",
        best_months=[9, 10, 11, 12, 1, 2, 3, 4, 5],
        hazards="Crowded, pier to the south",
        facilities="Parking, restrooms, kite schools"
    ),
    KiteSpot(
        id="poleg",
        name="Poleg Beach",
        name_he="חוף פולג",
        region=Region.CENTRAL,
        latitude=32.2780,
        longitude=34.8380,
        optimal_wind_directions=[WindDirection.NW, WindDirection.W],
        difficulty=Difficulty.ALL_LEVELS,
        description="River mouth beach in Netanya. Many kite schools operate here.",
        water_type="mixed",
        best_months=[9, 10, 11, 12, 1, 2, 3, 4, 5],
        hazards="River current",
        facilities="Kite schools, parking"
    ),
    KiteSpot(
        id="herzliya",
        name="Herzliya Marina",
        name_he="מרינה הרצליה",
        region=Region.CENTRAL,
        latitude=32.1620,
        longitude=34.7920,
        optimal_wind_directions=[WindDirection.W, WindDirection.NW],
        difficulty=Difficulty.BEGINNER,
        description="Flat water conditions near the marina. Steady winds. Good for beginners and freestyle.",
        water_type="flat",
        best_months=[9, 10, 11, 12, 1, 2, 3, 4, 5],
        hazards="Boat traffic near marina",
        facilities="Full marina facilities, restaurants, rentals"
    ),
    KiteSpot(
        id="tel_baruch",
        name="Tel Baruch",
        name_he="תל ברוך",
        region=Region.CENTRAL,
        latitude=32.1150,
        longitude=34.7750,
        optimal_wind_directions=[WindDirection.W, WindDirection.NW],
        difficulty=Difficulty.INTERMEDIATE,
        description="North Tel Aviv beach. Mix of conditions.",
        water_type="mixed",
        best_months=[9, 10, 11, 12, 1, 2, 3, 4, 5],
        hazards="Swimmers, crowded",
        facilities="Beach facilities"
    ),
    KiteSpot(
        id="geula",
        name="Geula Beach",
        name_he="חוף גאולה",
        region=Region.CENTRAL,
        latitude=32.0650,
        longitude=34.7630,
        optimal_wind_directions=[WindDirection.W, WindDirection.NW, WindDirection.SW],
        difficulty=Difficulty.ADVANCED,
        description="Official Tel Aviv kite beach. Crowded, many obstacles. Advanced riders only - no room for mistakes!",
        water_type="waves",
        best_months=[10, 11, 12, 1, 2, 3],
        hazards="Obstacles, buildings nearby, very crowded, road close to beach",
        facilities="Urban beach facilities"
    ),
    KiteSpot(
        id="hilton",
        name="Hilton Beach",
        name_he="חוף הילטון",
        region=Region.CENTRAL,
        latitude=32.0870,
        longitude=34.7680,
        optimal_wind_directions=[WindDirection.W, WindDirection.NW],
        difficulty=Difficulty.INTERMEDIATE,
        description="Tel Aviv beach near Israel Surf Club. Water sports hub.",
        water_type="mixed",
        best_months=[9, 10, 11, 12, 1, 2, 3, 4, 5],
        hazards="Swimmers, crowded",
        facilities="Surf club, restaurants, rentals"
    ),
    KiteSpot(
        id="dolfinarium",
        name="Dolfinarium",
        name_he="דולפינריום",
        region=Region.CENTRAL,
        latitude=32.0580,
        longitude=34.7600,
        optimal_wind_directions=[WindDirection.W, WindDirection.SW],
        difficulty=Difficulty.INTERMEDIATE,
        description="South Tel Aviv spot. Good in westerly and southwesterly winds.",
        water_type="waves",
        best_months=[10, 11, 12, 1, 2, 3],
        hazards="Obstacles",
        facilities="Beach facilities"
    ),

    # ============ SOUTHERN COAST ============
    KiteSpot(
        id="bat_yam",
        name="Bat Yam",
        name_he="בת ים",
        region=Region.SOUTH,
        latitude=32.0170,
        longitude=34.7450,
        optimal_wind_directions=[WindDirection.W, WindDirection.SW],
        difficulty=Difficulty.INTERMEDIATE,
        description="South of Tel Aviv. Good waves in winter storms.",
        water_type="waves",
        best_months=[10, 11, 12, 1, 2, 3],
        hazards="Rocks in some areas",
        facilities="Beach facilities"
    ),
    KiteSpot(
        id="ashdod",
        name="Ashdod",
        name_he="אשדוד",
        region=Region.SOUTH,
        latitude=31.8040,
        longitude=34.6350,
        optimal_wind_directions=[WindDirection.W, WindDirection.SW],
        difficulty=Difficulty.INTERMEDIATE,
        description="Up-and-coming spot. Many beach breaks, marina break, river mouth in winter.",
        water_type="waves",
        best_months=[10, 11, 12, 1, 2, 3],
        hazards="Port area restricted",
        facilities="Beach facilities"
    ),
    KiteSpot(
        id="ashkelon_goote",
        name="Ashkelon Goote Beach",
        name_he="חוף גוטה אשקלון",
        region=Region.SOUTH,
        latitude=31.6750,
        longitude=34.5550,
        optimal_wind_directions=[WindDirection.W, WindDirection.SW],
        difficulty=Difficulty.INTERMEDIATE,
        description="Best surf spot in Ashkelon. Bigger waves than northern beaches. Marina creates interesting conditions.",
        water_type="waves",
        best_months=[10, 11, 12, 1, 2, 3],
        hazards="Marina jetties",
        facilities="Beach facilities, marina"
    ),
    KiteSpot(
        id="ashkelon_delilah",
        name="Ashkelon Delilah Beach",
        name_he="חוף דלילה אשקלון",
        region=Region.SOUTH,
        latitude=31.6680,
        longitude=34.5520,
        optimal_wind_directions=[WindDirection.W, WindDirection.SW],
        difficulty=Difficulty.INTERMEDIATE,
        description="Popular Ashkelon beach named after biblical story. Good waves.",
        water_type="waves",
        best_months=[10, 11, 12, 1, 2, 3],
        hazards="Crowded in summer",
        facilities="Full beach facilities"
    ),

    # ============ EILAT (RED SEA) ============
    KiteSpot(
        id="eilat",
        name="Eilat Reef Raf",
        name_he="ריף רף אילת",
        region=Region.EILAT,
        latitude=29.5020,
        longitude=34.9170,
        optimal_wind_directions=[WindDirection.N],
        difficulty=Difficulty.ALL_LEVELS,
        description="Official Eilat kite beach at south beach near Orchidea hotel. 80% wind days per year! Steady 20 knots, flat water. Best in Israel for consistent conditions.",
        water_type="flat",
        best_months=[4, 5, 6, 7, 8, 9],
        hazards="Small launch area, coral reef nearby, crowded",
        facilities="Surf center, rentals, rescue services"
    ),

    # ============ KINNERET (SEA OF GALILEE) ============
    KiteSpot(
        id="kinneret_diamond",
        name="Diamond Bay (Kinneret)",
        name_he="מפרץ הדיאמונד כנרת",
        region=Region.KINNERET,
        latitude=32.8350,
        longitude=35.6450,
        optimal_wind_directions=[WindDirection.W, WindDirection.NW],
        difficulty=Difficulty.ALL_LEVELS,
        description="Unique diamond-shaped bay at Tza'alon beach near Kursi. Thermal summer winds. Flat fresh water. Works almost any westerly/northerly wind direction.",
        water_type="flat",
        best_months=[5, 6, 7, 8, 9],
        hazards="Thermal winds can be gusty",
        facilities="Beach facilities, parking"
    ),
]


def get_all_spots() -> List[KiteSpot]:
    """Return all kite spots"""
    return KITE_SPOTS


def get_spot_by_id(spot_id: str) -> Optional[KiteSpot]:
    """Get a specific spot by ID"""
    for spot in KITE_SPOTS:
        if spot.id == spot_id:
            return spot
    return None


def get_spots_by_region(region: Region) -> List[KiteSpot]:
    """Get all spots in a specific region"""
    return [spot for spot in KITE_SPOTS if spot.region == region]


def get_spots_for_beginners() -> List[KiteSpot]:
    """Get spots suitable for beginners"""
    return [spot for spot in KITE_SPOTS
            if spot.difficulty in [Difficulty.BEGINNER, Difficulty.ALL_LEVELS]]


# Spot coordinates for weather API queries
def get_spot_coordinates() -> List[dict]:
    """Get list of spot IDs with their coordinates for weather fetching"""
    return [
        {
            "id": spot.id,
            "name": spot.name,
            "lat": spot.latitude,
            "lon": spot.longitude
        }
        for spot in KITE_SPOTS
    ]
