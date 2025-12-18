from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.db.session import get_session
from app.services.auth import get_user_by_username, verify_password


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
    
    assert response.status_code == 201
    assert user is not None
    assert user.username == "Thisisatest"
    assert verify_password("testtest123", user.hashed_password) == True

def test_register_duplicate_username():
    app.dependency_overrides[get_session] = override_dependency

    
