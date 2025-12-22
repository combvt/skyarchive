import httpx
from datetime import datetime, timedelta, timezone
from geopy.geocoders import Nominatim
from app.exceptions import InvalidLocationError
HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"

geolocator = Nominatim(user_agent="SkyArchive")


def get_coords(city_name: str) -> str:
    location = geolocator.geocode(city_name)

    if not location:
        raise InvalidLocationError("Invalid location")
    
    coords = f"{location.longitude},{location.latitude},700" # pyright: ignore[reportAttributeAccessIssue]

    return coords


def search_object(object_name: str | int, coords: str) -> str:

    params = {
        "format": "json",
        "COMMAND":object_name,
        "MAKE_EPHEM": "YES",
        "EPHEM_TYPE": "OBSERVER",
        "CENTER": "coord@399",
        "COORD_TYPE": "GEODETIC",
        "SITE_COORD": f"'{coords}'",
        "OBJ_DATA": "YES",
        "START_TIME": f"'{datetime.now(timezone.utc).strftime(r"%Y-%b-%d %H:%M")}'",
        "STOP_TIME": f"'{(datetime.now(timezone.utc) + timedelta(minutes=1)).strftime(r"%Y-%b-%d %H:%M")}'",
        "STEP_SIZE": "1m",
        "TIME_TYPE": "UT",
        "CAL_FORMAT": "CAL",
    }

    response = httpx.get(url=HORIZONS_URL, params=params)
    response.raise_for_status()

    data = response.json()

    return data


