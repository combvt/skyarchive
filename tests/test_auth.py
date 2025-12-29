from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.db.base import Base
from app.db.session import get_session
from app.services.auth import get_user_by_username, verify_password, create_user
import pytest


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


def test_register_success(override_get_session, db_session):

    response = client.post(
        "/auth/register", json={"username": "Thisisatest", "password": "testtest123"}
    )
    user = get_user_by_username("Thisisatest", db_session)

    assert response.status_code == 201
    assert user is not None
    assert user.username == "Thisisatest"
    assert verify_password("testtest123", user.hashed_password) == True


def test_register_duplicate_username(override_get_session, db_session):

    create_user("yohellothere", "justatest", db_session)

    response = client.post(
        "/auth/register", json={"username": "yohellothere", "password": "hihowareyou"}
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Username already exists"}


def test_login_successful(override_get_session, db_session):

    create_user("myuser", "mypassword", db_session)

    response = client.post(
        "/auth/login",
        data={
            "username": "myuser",
            "password": "mypassword",
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_invalid_credentials(override_get_session, db_session):

    create_user("hithere", "byethere", db_session)

    response = client.post(
        "auth/login",
        data={
            "username": "hiithere",
            "password": "byethere",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid credentials"}
