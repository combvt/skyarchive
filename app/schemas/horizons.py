from pydantic import BaseModel



class HorizonsEphemerisResponse(BaseModel):
    object_name: str
    object_id: str
    date: str
    azimuth_deg: float | None = None
    altitude_deg: float | None = None
    apparent_magnitude: float | None = None
    surface_brightness: float | None = None
    illumination_percent: float | None = None
    angular_diameter_arcsec: float | None = None
    sun_distance_au: float | None = None
    earth_distance_au: float | None = None
    solar_elong_deg: float | None = None
    constellation: str | None = None


class HorizonsMatchObject(BaseModel):
    object_name: str
    object_id: str
    epoch_year: int | None = None
    designation: str | None = None
    aliases: str | None = None
