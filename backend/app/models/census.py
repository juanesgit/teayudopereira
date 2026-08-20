from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class CensusRecord(Base):
    """Registro de censo de víctimas/afectados por emergencia."""
    __tablename__ = "census_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # ── Datos personales ──────────────────────────────────────────────────
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    document_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # masculino/femenino/otro

    # ── Contacto ──────────────────────────────────────────────────────────
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # ── Ubicación ────────────────────────────────────────────────────────
    address: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    neighborhood: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    lng: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # ── Grupo familiar ────────────────────────────────────────────────────
    people_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    children_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    adults_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    elderly_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # ── Necesidades y condición ───────────────────────────────────────────
    needs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)        # JSON list: food,water,shelter,medical,medicine
    vulnerable: Mapped[Optional[str]] = mapped_column(Text, nullable=True)   # JSON list: pregnant,disability,chronic_illness
    shelter_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)  # home/evacuated/shelter/street

    # ── Notas ─────────────────────────────────────────────────────────────
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # ── Estado de atención ────────────────────────────────────────────────
    is_attended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    attended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # ── Meta ──────────────────────────────────────────────────────────────
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    registered_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
