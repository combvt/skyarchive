import httpx
from datetime import datetime, timedelta, timezone
from geopy.geocoders import Nominatim
from app.exceptions import InvalidLocationError, ObjectNotFoundError
from app.exceptions import EphemerisDataMissing, UpstreamServiceError

HORIZONS_URL = "https://ssd.jpl.nasa.gov/api/horizons.api"
DEFAULT_ELEVATION_KM = 0.3

geolocator = Nominatim(user_agent="SkyArchive")


def get_coords(city_name: str, elevation: float | None = DEFAULT_ELEVATION_KM) -> str:
    location = geolocator.geocode(city_name)

    if not location:
        raise InvalidLocationError("Invalid location")
    
    coords = f"{location.longitude},{location.latitude},{elevation}" # pyright: ignore[reportAttributeAccessIssue]

    return coords


def search_object(object_name: str | int, coords: str) -> dict:

    params = {
        "format": "json",
        "COMMAND":f"'{object_name}'",
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


def parse_horizons_ephemeris(raw_data: dict) -> dict:
    data_dict = {}
    data_dict["source"] = raw_data.get("signature", {}).get("source", "Unknown source")


    data = raw_data["result"]
    start_index = data.find("$$SOE") + 5
    end_index = data.find("$$EOE")

    name_start_index = data.find("Target body name:")
    name_end_index = data.find(r"{source:")



    if data.find("No matches found.") != -1:
        raise ObjectNotFoundError
    elif data.find("Number of matches =") != -1 or data.find("Matching small-bodies:") != -1:
        return data
    elif start_index != -1 and end_index != -1:
        name_id_string = data[name_start_index:name_end_index].strip()
        first_slice_index = name_id_string.find("(")
        second_slice_index = name_id_string.find(")")
        object_name = name_id_string[len("Target body name:"):first_slice_index].strip()
        object_id = name_id_string[first_slice_index + 1:second_slice_index].strip()
        
        data_dict["object_name"] = object_name
        data_dict["object_id"] = object_id

        sliced_string = data[start_index:end_index].strip()

        clean_data = sliced_string.splitlines()[0].replace("*m", "")
        parsed_string = clean_data.replace("/T", "").replace("/L", "").split()

        i = 0
        data_dict["date"] = f"{parsed_string[i]} {parsed_string[i + 1]}"
        i += 16
        data_dict["azimuth_deg"] = parsed_string[i]
        i += 1
        data_dict["altitude_deg"] = parsed_string[i]
        i += 11
        data_dict["apparent_magnitude"] = parsed_string[i]
        i += 1
        data_dict["surface_brightness"] = parsed_string[i]
        i += 1
        data_dict["illumination_percent"] = parsed_string[i]
        i += 3
        data_dict["angular_diameter_arcsec"] = parsed_string[i]
        i += 11
        data_dict["sun_distance_au"] = parsed_string[i]
        i += 2
        data_dict["earth_distance_au"] = parsed_string[i]
        i += 6
        data_dict["solar_elong_deg"] = parsed_string[i]
        i += 7
        data_dict["constellation"] = parsed_string[i]

        for key, value in data_dict.items():
            if value == "n.a.":
                data_dict[key] = None

        return data_dict
    else:
        raise UpstreamServiceError
    

coords = "45.5,21.5,0.3"
object = search_object(-31, coords)
print(parse_horizons_ephemeris(object))