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


def _slice_substring_into_list(substring : str, index_list: list[int]) -> list[str]:
    new_list = []

    for index in range(len(index_list) - 1):
        first_slice = index_list[index]
        second_slice = index_list[index + 1]
        sliced_string = substring[first_slice:second_slice].strip()

        new_list.append(sliced_string)

    new_list.append(substring[second_slice:].strip())
    
    return new_list
            

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


def _parse_multi_match_results(column_headers: list[str], data_values: list[str]) -> list[dict]:
    parsed_list = []
    raise NotImplementedError




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
        if data.find("ID#") != -1:
            h_row_first_slice_i = data.find("ID#")        
        elif data.find("Record #") != -1:
            h_row_first_slice_i = data.find("Record #")
        
        h_row_second_slice_i = data.find("\n", h_row_first_slice_i)
        header_row = data[h_row_first_slice_i:h_row_second_slice_i]
        
        dashed_first_slice = data.find("-", h_row_second_slice_i)
        dashed_second_slice = data.find("\n", dashed_first_slice)

        dashed_row = data[dashed_first_slice:dashed_second_slice]
        
        dash_index_list = [0]
        for i in range(1, len(dashed_row)):
            if dashed_row[i] == "-" and dashed_row[i-1] == " ":
                dash_index_list.append(i)

        column_names_list = _slice_substring_into_list(header_row, dash_index_list)

        
        print(column_names_list)
        
        data_row_first_slice = dashed_second_slice + 1

        data_row_list = data[data_row_first_slice:].splitlines()
        parsed_data_list = []

        for row in data_row_list:
            if row.strip() == "":
                break
            parsed_row = _slice_substring_into_list(row, dash_index_list)
            parsed_data_list.append(parsed_row)

                


        
        # return data   
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
    

coords = "55,21.5,0.3"
object = search_object("mars", coords)
print(parse_horizons_ephemeris(object))