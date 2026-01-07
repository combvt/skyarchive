from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, relationship, mapped_column
from datetime import datetime, timezone
from app.db.base import Base
from app.models.auth import User

class Ephemeris(Base):
    __tablename__ = "ephemerides"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    object_name: Mapped[str] = mapped_column(nullable=False)
    object_id: Mapped[str] = mapped_column(nullable=False)
    azimuth_deg: Mapped[float] = mapped_column()
    altitude_deg: Mapped[float] = mapped_column()
    apparent_magnitude: Mapped[float] = mapped_column()
    surface_brightness: Mapped[float] = mapped_column()
    illumination_percent: Mapped[float] = mapped_column()
    angular_diameter_arcsec: Mapped[float] = mapped_column()
    sun_distance_au: Mapped[float] = mapped_column()
    earth_distance_au: Mapped[float] = mapped_column()
    solar_elong_deg: Mapped[float] = mapped_column()
    constellation: Mapped[str] = mapped_column()
    date: Mapped[str] = mapped_column(nullable=False)
    coords: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), nullable=False)

    user: Mapped[User] = relationship(back_populates="ephemerides")

    