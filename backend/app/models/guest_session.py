from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class GuestSession(Base):
    __tablename__ = "guest_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    guest_token: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    guest_name: Mapped[str] = mapped_column(String(120), nullable=False)
    room: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    report_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("reports.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    # Estado de la conversación: pending | active | resolved
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", server_default="pending")
    # Número de contacto compartido por el ciudadano (extraído del chat)
    phone_number: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
