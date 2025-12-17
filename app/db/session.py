from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import DB_URL
from app.db.base import Base


engine = create_engine(DB_URL, echo=True)

Base.metadata.create_all(engine)

SessionLocal = sessionmaker(engine)

def get_session():
    return SessionLocal()