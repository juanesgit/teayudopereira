from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base


class DangerLevel(str, enum.Enum):
    low = "low"          # precaución
    medium = "medium"    # peligro moderado
    high = "high"        # peligro alto
    critical = "critical"  # zona roja — evacuación inmediata


class DangerZone(Base):
    __tablename__ = "danger_zones"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str] = mapped_column(Text)
    danger_level: Mapped[DangerLevel] = mapped_column(SAEnum(DangerLevel))
    # Centro de la zona
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    # Radio en metros para dibujar el círculo en el mapa
    radius_meters: Mapped[int] = mapped_column(default=200)
    photo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
