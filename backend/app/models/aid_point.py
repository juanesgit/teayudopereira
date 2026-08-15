from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Boolean, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base


class AidType(str, enum.Enum):
    shelter = "shelter"          # albergue
    food = "food"                # alimentación
    medical = "medical"          # centro médico / brigada
    water = "water"              # agua potable
    supplies = "supplies"        # ropa, colchonetas, kit de aseo
    information = "information"  # punto de información
    veterinary = "veterinary"    # centro veterinario
    nursing_home = "nursing_home"  # ancianato / hogar de adulto mayor


class AidPoint(Base):
    __tablename__ = "aid_points"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150))
    aid_type: Mapped[AidType] = mapped_column(SAEnum(AidType, create_constraint=False))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    address: Mapped[str] = mapped_column(String(256))
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    capacity: Mapped[Optional[int]] = mapped_column(nullable=True)   # cupos disponibles
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
