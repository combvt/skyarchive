from sqlalchemy import String
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from datetime import datetime, timezone
from app.db.base import Base


class Ephemeris(Base):
    __tablename__ = "ephemerides"