from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, DateTime, ForeignKey, Enum as SAEnum, Text
from sqlalchemy.orm import Mapped, mapped_column
import enum

from app.database import Base


class NeedType(str, enum.Enum):
    rescue = "rescue"          # rescate atrapado
    medical = "medical"        # atención médica
    food = "food"              # alimentos / agua
    shelter = "shelter"        # albergue
    family = "family"          # búsqueda de familiar
    psychological = "psychological"  # apoyo psicológico
    structural = "structural"        # evaluación estructural de edificio
    pet = "pet"                      # búsqueda de mascota perdida
    pet_home = "pet_home"            # mascota busca hogar
    lost_all = "lost_all"            # lo perdió todo
    medicine = "medicine"            # necesita medicamentos
    other = "other"


class ReportStatus(str, enum.Enum):
    pending = "pending"        # sin atender
    in_progress = "in_progress"  # en proceso
    resolved = "resolved"      # resuelto


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    # Nombre de quien reporta (puede ser anónimo)
    reporter_name: Mapped[str] = mapped_column(String(120))
    reporter_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    need_type: Mapped[NeedType] = mapped_column(SAEnum(NeedType))
    description: Mapped[str] = mapped_column(Text)
    address: Mapped[str] = mapped_column(String(256))
    # Coordenadas GPS — Pereira centro: lat 4.8133, lng -75.6961
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    people_count: Mapped[int] = mapped_column(default=1)
    status: Mapped[ReportStatus] = mapped_column(SAEnum(ReportStatus), default=ReportStatus.pending)
    assigned_to: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    extra_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON con campos específicos por tipo
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
