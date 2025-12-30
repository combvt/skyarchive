from app.main import app
from app.services.horizons import parse_horizons_ephemeris
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.session import get_session
from app.services.auth import create_user
import pytest
from app.exceptions import ObjectNotFoundError, EphemerisDataMissing
from app.exceptions import InvalidLocationError, UpstreamServiceError

client = TestClient(app)

fake_engine = create_engine(
    "sqlite:///:memory:", connect_args={"check_same_thread": False}
)

Base.metadata.create_all(bind=fake_engine)


@pytest.fixture
def override_get_session(db_session):
    def override_dependency():
        return db_session

    app.dependency_overrides[get_session] = override_dependency
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    connection = fake_engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()
    yield session
    session.close()
    transaction.rollback()
    transaction.close()


@pytest.fixture
def test_user(db_session):
    user = create_user("testing", "fortest", db_session)
    return {"username": user.username, "password": "fortest"}


@pytest.fixture
def auth_header(test_user, override_get_session):
    user = test_user
    response = client.post(
        "/auth/login", data={"username": user["username"], "password": user["password"]}
    )
    token = response.json()["access_token"]

    assert response.status_code == 200

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def mock_search_object(monkeypatch):
    def fake_search_object(object_name: str | int, coords: str):
        return {
            "source": "fake",
            "result": "Ephemeris data for x object \n\n 2025-Dec-25 15:58 21.2 36.4 213231",
        }

    monkeypatch.setattr("app.api.horizons.search_object", fake_search_object)


@pytest.fixture
def mock_get_coords(monkeypatch):
    def fake_get_coords(location: str, elevation: str | None = None):
        return "21.6,55,0.3"

    monkeypatch.setattr("app.api.horizons.get_coords", fake_get_coords)


def test_horizons_search_requires_auth(override_get_session):

    response = client.get(
        url="/horizons/search",
        headers={"Authorization": "Bearer thisisnotatoken213132"},
        params={"query": "mars", "location": "prague"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}


def test_horizons_search_returns_single_ephemeris(
    override_get_session, auth_header, monkeypatch, mock_search_object, mock_get_coords
):

    def fake_parse_horizons_ephemeris(raw_data: dict):
        return {
            "object_name": "Mars",
            "object_id": "499",
            "date": "2025-Dec-29 15:54",
            "azimuth_deg": 239.356858,
            "altitude_deg": -5.935073,
            "apparent_magnitude": 1.075,
            "surface_brightness": 3.757,
            "illumination_percent": 99.97094,
            "angular_diameter_arcsec": 3.882006,
            "sun_distance_au": 1.431151111878,
            "earth_distance_au": 2.41248972367116,
            "solar_elong_deg": 1.9588,
            "constellation": "Sgr",
        }

    monkeypatch.setattr(
        "app.api.horizons.parse_horizons_ephemeris", fake_parse_horizons_ephemeris
    )

    response = client.get(
        "/horizons/search",
        params={"query": 499, "location": "london"},
        headers=auth_header,
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["object_name"] == "Mars"
    assert data["date"] == "2025-Dec-29 15:54"
    assert data["azimuth_deg"] == 239.356858
    assert data["illumination_percent"] == 99.97094
    assert data["constellation"] == "Sgr"


def test_horizons_search_multi_match_response(
    override_get_session, mock_search_object, mock_get_coords, auth_header, monkeypatch
):
    def fake_parse_horizons_ephemeris(raw_data: dict):
        return [
            {
                "object_name": "Mars Barycenter",
                "object_id": "4",
                "designation": None,
                "aliases": None,
            },
            {
                "object_name": "Mars",
                "object_id": "499",
                "designation": None,
                "aliases": None,
            },
            {
                "object_name": "Mars Orbiter Mission (spacecraft)",
                "object_id": "-3",
                "designation": "2013-060A",
                "aliases": "MOM Mangalyaan",
            },
        ]

    monkeypatch.setattr(
        "app.api.horizons.parse_horizons_ephemeris", fake_parse_horizons_ephemeris
    )

    response = client.get(
        "/horizons/search",
        params={
            "query": "mars",
            "location": "Honolulu",
        },
        headers=auth_header,
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert isinstance(data[1], dict)
    assert len(data) == 3
    assert "designation" not in data[0]
    assert data[1]["object_name"] == "Mars"
    assert "aliases" in data[2]


def test_horizons_search_object_not_found_returns_404(
    override_get_session, auth_header, monkeypatch, mock_search_object, mock_get_coords
):
    def fake_parse_horizons_ephemeris(raw_data: dict):
        raise ObjectNotFoundError

    monkeypatch.setattr(
        "app.api.horizons.parse_horizons_ephemeris", fake_parse_horizons_ephemeris
    )

    response = client.get(
        "/horizons/search",
        params={
            "query": "mars",
            "location": "Honolulu",
        },
        headers=auth_header,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Object not found"}


def test_horizons_search_ephemeris_data_missing_returns_404(
    override_get_session, auth_header, monkeypatch, mock_search_object, mock_get_coords
):
    def fake_parse_horizons_ephemeris(raw_data: dict):
        raise EphemerisDataMissing

    monkeypatch.setattr(
        "app.api.horizons.parse_horizons_ephemeris", fake_parse_horizons_ephemeris
    )

    response = client.get(
        "/horizons/search",
        params={
            "query": "mars",
            "location": "Honolulu",
        },
        headers=auth_header,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "No ephemeris data available for this object"}


def test_horizons_search_upstream_service_error_returns_503(
    override_get_session, auth_header, monkeypatch, mock_search_object, mock_get_coords
):
    def fake_parse_horizons_ephemeris(raw_data: dict):
        raise UpstreamServiceError

    monkeypatch.setattr(
        "app.api.horizons.parse_horizons_ephemeris", fake_parse_horizons_ephemeris
    )

    response = client.get(
        "/horizons/search",
        params={
            "query": "mars",
            "location": "Honolulu",
        },
        headers=auth_header,
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Upstream Horizons service error"}


def test_horizons_search_invalid_location_returns_400(
    override_get_session, auth_header, monkeypatch
):
    def fake_get_coords(location: str, elevation: str | None = None):
        raise InvalidLocationError

    monkeypatch.setattr("app.api.horizons.get_coords", fake_get_coords)

    response = client.get(
        "/horizons/search",
        params={
            "query": "mars",
            "location": "Honolulu",
        },
        headers=auth_header,
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid location"}


def test_single_match_ephemeris_parser():
    raw_data = {
        "result": """
        Target body name: Mars (499) \n
        Date__(UT)__HR:MN     R.A._____(ICRF)_____DEC  R.A.__(a-apparent)__DEC  dRA*cosD d(DEC)/dt  Azi____(a-app)___Elev  dAZ*cosE d(ELV)/dt  X_(sat-primary)_Y SatPANG  L_Ap_Sid_Time  a-mass mag_ex    APmag   S-brt      Illu%  Def_illu   ang-sep/v  Ang-diam  ObsSub-LON ObsSub-LAT  SunSub-LON SunSub-LAT  SN.ang   SN.dist    NP.ang   NP.dist  hEcl-Lon hEcl-Lat                r        rdot             delta      deldot  1-way_down_LT       VmagSn      VmagOb     S-O-T /r     S-T-O   T-O-M/MN_Illu%     O-P-T    PsAng   PsAMV      PlAng  Cnst        TDB-UT     ObsEcLon    ObsEcLat  N.Pole-RA  N.Pole-DC      GlxLon     GlxLat  L_Ap_SOL_Time  399_ins_LT  RA_3sigma DEC_3sigma  SMAA_3sig SMIA_3sig    Theta Area_3sig  POS_3sigma  RNG_3sigma RNGRT_3sig   DOP_S_3sig  DOP_X_3sig  RT_delay_3sig  Tru_Anom  L_Ap_Hour_Ang       phi  PAB-LON  PAB-LAT  App_Lon_Sun  RA_(ICRF-a-apparnt)_DEC  I_dRA*cosD I_d(DEC)/dt  Sky_motion  Sky_mot_PA  RelVel-ANG  Lun_Sky_Brt  sky_SNR   UT1-UTC\n $$SOE
        2025-Dec-24 13:35 *m  18 29 09.23 -24 06 38.9  18 30 43.42 -24 05 40.2  113.8230  5.400805  241.884725   4.515307    360.13   -738.84  14604.74 -2481.00 100.552  23 28 20.4496  10.858  2.758    1.091   3.770   99.94014    0.0023  14775.52/*  3.876377  115.612958  -5.463741  112.879016  -6.152040  278.76      0.09   22.9663    -1.918  279.4003  -1.4137   1.436626158701  -1.8934692  2.41599313076047  -0.7162227    20.09320217   25.5498277  55.4687733    4.1043 /T    2.8096    46.3/ 18.1776  173.0861   98.926 268.300   -0.50850   Sgr     69.183708  277.0089569  -0.8429883  317.65322   52.87035    8.955257  -6.161004  17 15 17.9731    0.000354       n.a.       n.a.       n.a.      n.a.     n.a.      n.a.        n.a.        n.a.       n.a.         n.a.        n.a.           n.a.  303.3081   04 57 37.027    2.8040 278.0227  -1.1270  194.4077072  18 29 07.72 -24 06 40.1    113.8375    5.086793   1.8991841   87.283401   -0.745567         n.a.     n.a.   0.07730
        $$EOE
    """
    }

    data = parse_horizons_ephemeris(raw_data)
    assert isinstance(data, dict)
    assert data["object_name"] == "Mars"
    assert data["object_id"] == "499"
    assert data["date"] == "2025-Dec-24 13:35"
    assert data["azimuth_deg"] == "241.884725"
    assert data["constellation"] == "Sgr"
    assert data["angular_diameter_arcsec"] == "3.876377"
    assert "*m" not in data


