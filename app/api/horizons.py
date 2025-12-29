from fastapi import APIRouter, status, Depends, HTTPException
from app.services.horizons import get_coords, search_object, parse_horizons_ephemeris
from app.exceptions import InvalidLocationError, ObjectNotFoundError
from app.exceptions import EphemerisDataMissing, UpstreamServiceError
from app.schemas.horizons import HorizonsEphemerisResponse, HorizonsMatchObject
from app.services.auth import get_current_user
from app.models.auth import User

horizons_router = APIRouter(prefix="/horizons")

@horizons_router.get("/search", status_code=200)
def fetch_object(query: str | int, location: str, elevation: float | None = None, current_user: User = Depends(get_current_user)):
    try:
        coords = get_coords(location, elevation)
    except InvalidLocationError:
        raise HTTPException(400, detail="Invalid location")
    
    output = search_object(object_name=query, coords=coords)

    try:
        data = parse_horizons_ephemeris(output)
    except ObjectNotFoundError:
        raise HTTPException(404, detail="Object not found")
    except EphemerisDataMissing:
        raise HTTPException(404, detail="No ephemeris data available for this object")
    except UpstreamServiceError:
        raise HTTPException(503, detail="Upstream Horizons service error")

    if isinstance(data, list):
        output_list = []

        for item in data:
            new_item = HorizonsMatchObject(**item).model_dump(exclude_none=True)
            output_list.append(new_item)
        
        return output_list
    elif isinstance(data, dict):
        return HorizonsEphemerisResponse(**data)
    else:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail="Unexpected Horizons response")

