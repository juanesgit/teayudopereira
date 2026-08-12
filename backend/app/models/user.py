from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Float, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    victim = "victim"              # persona afectada
    volunteer = "volunteer"        # voluntario
    coordinator = "coordinator"    # coordinador / entidad
    admin = "admin"                # administrador del sistema


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    id_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), unique=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole, create_constraint=False), default=UserRole.victim)
    # Habilidades del voluntario (ej: "médico,logística,psicología")
    skills: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    # Barrio o zona en Pereira
    neighborhood: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    # Zona de acción del voluntario
    action_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    action_lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    action_radius_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
