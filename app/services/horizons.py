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


def _parse_single_match_ephemeris(ephemeris_data: str) -> dict:
    output_dict = {}

    i = 0
    output_dict["date"] = f"{ephemeris_data[i]} {ephemeris_data[i + 1]}"
    i += 17
    output_dict["azimuth_deg"] = ephemeris_data[i]
    i += 1
    output_dict["altitude_deg"] = ephemeris_data[i]
    i += 11
    output_dict["apparent_magnitude"] = ephemeris_data[i]
    i += 1
    output_dict["surface_brightness"] = ephemeris_data[i]
    i += 1
    output_dict["illumination_percent"] = ephemeris_data[i]
    i += 3
    output_dict["angular_diameter_arcsec"] = ephemeris_data[i]
    i += 11
    output_dict["sun_distance_au"] = ephemeris_data[i]
    i += 2
    output_dict["earth_distance_au"] = ephemeris_data[i]
    i += 6
    output_dict["solar_elong_deg"] = ephemeris_data[i]
    i += 7
    output_dict["constellation"] = ephemeris_data[i]

    for key, value in output_dict.items():
        if value == "n.a.":
            output_dict[key] = None

    return output_dict


def parse_horizons_ephemeris(raw_data: dict) -> dict:
    data_dict = {}
    data_dict["source"] = raw_data.get("signature", {}).get("source", "Unknown source")


    data = raw_data["result"]
    start_index = data.find("$$SOE") + 5
    end_index = data.find("$$EOE")

    name_start_index = data.find("Target body name:")
    name_end_index = data.find(r"{source:")



    if data.find("No matches found.") != -1 or data.find("No such record") != -1:
        raise ObjectNotFoundError
    elif data.find("No ephemeris for target") != -1:
        raise EphemerisDataMissing
    elif data.find("Number of matches =") != -1 or data.find("Matching small-bodies:") != -1:
        return data
    elif start_index != -1 and end_index != -1:
        raw_name_id_string = data[name_start_index:name_end_index].strip()
        name_id_string = raw_name_id_string.split(":")[1]

        if name_id_string.find("(spacecraft)") != -1:
            first_slice_index = name_id_string.find(")")
            object_name = name_id_string[:first_slice_index + 1].strip()
            second_slice_index = name_id_string.find(")", len(object_name) + 1)
            object_id = name_id_string[first_slice_index + 3:second_slice_index]
        else:
            first_slice_index = name_id_string.find("(")
            second_slice_index = name_id_string.find(")")
            object_name = name_id_string[:first_slice_index].strip()
            object_id = name_id_string[first_slice_index + 1:second_slice_index].strip()

        data_dict["object_name"] = object_name
        data_dict["object_id"] = object_id

        sliced_string = data[start_index:end_index].strip()

        clean_data = sliced_string.splitlines()[0].replace("*m", "")
        parsed_string = clean_data.replace("/T", "").replace("/L", "").split()

        output_data = _parse_single_match_ephemeris(parsed_string)
        data_dict.update(output_data)

        return data_dict
    else:
        raise UpstreamServiceError
    

coords = "45.5,21.5,0.3"
object = search_object(-92, coords)
print(parse_horizons_ephemeris(object))