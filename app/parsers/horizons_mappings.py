multi_match_mapping_table = {
        "Record #": "object_id",
        "ID#": "object_id",
        "Name": "object_name",
        ">MATCH NAME<": "object_name",
        "Epoch-yr": "epoch_year",
        "Designation": "designation",
        "Primary Desig": "designation",
        ">MATCH DESIG<": "designation",
        "IAU/aliases/other": "aliases",
    }


single_match_mapping_table = {
    "Date__(UT)__HR:MN": "date",
    "Azi____(a-app)___Elev": ("azimuth_deg", "altitude_deg"),
    "APmag": "apparent_magnitude",
    "S-brt": "surface_brightness",
    "Illu%": "illumination_percent",
    "Ang-diam": "angular_diameter_arcsec",
    "r": "sun_distance_au",
    "delta": "earth_distance_au",
    "S-T-O": "solar_elong_deg",
    "Cnst": "constellation",
}