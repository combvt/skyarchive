from app.main import app
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.session import get_session
from app.services.auth import validate_access_token, create_user
import pytest
from app.services.horizons import search_object, parse_horizons_ephemeris

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
    user = create_user("testing","fortest", db_session)
    return {
        "username": user.username,
        "password": "fortest"
    }

@pytest.fixture
def auth_header(test_user, override_get_session):
    user = test_user
    response = client.post("/auth/login", data={
        "username": user["username"],
        "password": user["password"]
    })
    token = response.json()["access_token"]

    assert response.status_code == 200

    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def mock_search_object(monkeypatch):
    def fake_search_object(object_name: str | int, coords: str):
        return {"source": "fake", "result": "Ephemeris data for x object \n\n 2025-Dec-25 15:58 21.2 36.4 213231"}
    monkeypatch.setattr("app.api.horizons.search_object", fake_search_object)


def test_horizons_search_requires_auth(override_get_session):
    
    response = client.get(url="/horizons/search", headers={
        "Authorization": "Bearer thisisnotatoken213132"
    },
    params={
        "query": "mars",
        "location": "prague"
    })

    assert response.status_code == 401
    assert response.json() == {"detail": "Could not validate credentials"}

def test_horizons_search_returns_single_ephemeris(override_get_session, auth_header, monkeypatch, mock_search_object):
    
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
            "constellation": "Sgr"
        }
    
    monkeypatch.setattr("app.api.horizons.parse_horizons_ephemeris", fake_parse_horizons_ephemeris)

    response = client.get("/horizons/search", params={
        "query": 499,
        "location": "london"
    },
    headers=auth_header)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert data["object_name"] == "Mars"
    assert data["date"] == "2025-Dec-29 15:54"
    assert data["azimuth_deg"] == 239.356858
    assert data["illumination_percent"] == 99.97094
    assert data["constellation"] == "Sgr"


def test_horizons_search_multi_match_response(override_get_session, mock_search_object, auth_header, monkeypatch):
    
#TODO  add test for each of the exceptions raised in the endpoint
# ObjectNotFoundError, EphemerisDataMissing, UpstreamServiceError,
# InvalidLocationError and assert accordingly
#TODO maybe add fixture to stub search_object if its being called
# in every test.
#TODO add test for multi-match response, assert list type,
#list length, items, None fields don't exist.
#TODO add test for single match parser, assert token count ==
# len(data), correct slicing (give it a real string)