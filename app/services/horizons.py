import httpx
from datetime import datetime, timedelta, timezone
from geopy.geocoders import Nominatim
from app.exceptions import InvalidLocationError, ObjectNotFoundError
from app.exceptions import EphemerisDataMissing, UpstreamServiceError
from ..parsers.horizons_mappings import multi_match_mapping_table as mapping_table

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


def _parse_multi_match_results(column_list: list[str], data_rows_list: list[str]) -> list[dict]:
    parsed_list = []
    
    for row in data_rows_list:
        raw_dict = {}
        zipped_output = zip(column_list, row)

        for key, value in zipped_output:
            raw_dict[key] = value

        parsed_list.append(raw_dict)

    return parsed_list


def _map_multi_match_results(data_list: list[dict]) -> list[dict]:
    mapped_list = []
    
    for data in data_list:
        new_dict = {}
        for key, value in data.items():
            if key in mapping_table and mapping_table[key] not in new_dict:
                new_dict[mapping_table[key]] = value

        mapped_list.append(new_dict)

    return mapped_list






def parse_horizons_ephemeris(raw_data: dict) -> dict | list[dict]:
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

        raw_dashed_first_slice = data.find(" ", h_row_second_slice_i)
        raw_dashed_second_slice = data.find("\n", raw_dashed_first_slice)
        raw_dashed_row = data[raw_dashed_first_slice:raw_dashed_second_slice]
        first_dash_index = raw_dashed_row.find("-")
        offset_index = len(raw_dashed_row[:first_dash_index])

        dashed_first_slice = data.find("-", h_row_second_slice_i)
        dashed_second_slice = data.find("\n", dashed_first_slice)
        dashed_row = data[dashed_first_slice:dashed_second_slice]

        dash_index_list = [0]
        for i in range(1, len(dashed_row)):
            if dashed_row[i] == "-" and dashed_row[i-1] != "-":
                dash_index_list.append(i)

        column_names_list = _slice_substring_into_list(header_row, dash_index_list)

        data_row_first_slice = dashed_second_slice + 1

        data_row_list = data[data_row_first_slice:].splitlines()

        parsed_data_list = []
        
        for row in data_row_list:
            if row.strip() == "":
                break
            offset_row = row[offset_index:]

            parsed_row = _slice_substring_into_list(offset_row, dash_index_list)
            parsed_data_list.append(parsed_row)
   
        output_list = _parse_multi_match_results(column_names_list, parsed_data_list)
        mapped_list = _map_multi_match_results(output_list)

        return mapped_list 
    elif data.find("$$SOE") != -1 and end_index != -1:
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

        h_row_first_slice = data.find("Date__(UT)")
        h_row_second_slice = data.find("\n", h_row_first_slice)
        raw_header_string = data[h_row_first_slice:h_row_second_slice].replace("/r", "")
        header_tokens = raw_header_string.split()
        print(header_tokens)
        print()
        

        data_string = data[start_index:end_index].strip()

        clean_data = data_string.splitlines()[0].split()
        data_list = []
        for data in clean_data:
            if data in DROP_TOKENS:
                continue
            data_list.append(data)
        
        print(data_list)
        print()
        output_data = _parse_single_match_ephemeris(header_tokens, data_list)
        data_dict.update(output_data)

        return data_dict
    else:
        raise UpstreamServiceError
    

coords = "31.543,-67.324,0.3"
object = search_object("27:", coords)
print(parse_horizons_ephemeris(object))