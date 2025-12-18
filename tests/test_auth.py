from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.session import get_session
from app.services.auth import get_user_by_username, verify_password, create_user
from app.services.auth import create_access_token
import json

client = TestClient(app)

fake_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

connection = fake_engine.connect()


SessionLocal = sessionmaker(bind=connection)

Base.metadata.create_all(bind=connection)


def override_dependency():
    return SessionLocal()


def test_register_success():
    app.dependency_overrides[get_session] = override_dependency

    response = client.post("/auth/register",
                json={
                    "username": "Thisisatest",
                    "password": "testtest123"
                }
    )
    user = get_user_by_username("Thisisatest", override_dependency())
    try:
        assert response.status_code == 201
        assert user is not None
        assert user.username == "Thisisatest"
        assert verify_password("testtest123", user.hashed_password) == True
    finally:
        app.dependency_overrides.clear()


def test_register_duplicate_username():
    app.dependency_overrides[get_session] = override_dependency

    create_user("yohellothere", "justatest", override_dependency())


    response = client.post(
                "/auth/register",
                json={
                    "username": "yohellothere",
                    "password": "hihowareyou"
                }
    )
    try:
        assert response.status_code == 409
        assert response.json() == {"detail": "Username already exists"}
    finally:
        app.dependency_overrides.clear()


def test_login_successful():
    app.dependency_overrides[get_session] = override_dependency

    create_user("myuser", "mypassword", override_dependency())

    response = client.post(
                "auth/login",
                json={
                    "username": "myuser",
                    "password": "mypassword",
                }
    )

    try:
        assert response.status_code == 200
        assert "access_token" in response.json()
    finally:
        app.dependency_overrides.clear()


def test_login_invalid_credentials():
    app.dependency_overrides[get_session] = override_dependency

    create_user("hithere", "byethere", override_dependency())

    response = client.post(
                "auth/login",
                json={
                    "username": "hiithere",
                    "password": "byethere",
                }
    )

    try:
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid credentials"}
    finally:
        app.dependency_overrides.clear()