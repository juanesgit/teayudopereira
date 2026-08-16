from __future__ import annotations
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Date, Boolean, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MedicationStock(Base):
    """Inventario de medicamentos disponibles (donaciones/stock)."""
    __tablename__ = "medication_stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)          # ej: "Metformina 500mg"
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="unidades")  # tabletas, ampollas, frascos…
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    storage_location: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    aid_point_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("aid_points.id", ondelete="SET NULL"), nullable=True)
    donated_by: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class MedicationDelivery(Base):
    """Registro de entrega de medicamentos a un solicitante."""
    __tablename__ = "medication_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    report_id: Mapped[int] = mapped_column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("medication_stock.id", ondelete="SET NULL"), nullable=True)
    medication_name: Mapped[str] = mapped_column(String(200), nullable=False)   # nombre libre o del stock
    quantity_delivered: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="unidades")
    delivered_to: Mapped[str] = mapped_column(String(150), nullable=False)      # nombre del paciente
    delivered_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    delivery_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
