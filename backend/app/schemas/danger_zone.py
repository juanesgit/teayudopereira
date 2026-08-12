from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.danger_zone import DangerLevel


class DangerZoneCreate(BaseModel):
    name: str
    description: str
    danger_level: DangerLevel
    lat: float
    lng: float
    radius_meters: int = 200
    photo_url: Optional[str] = None


class DangerZoneUpdate(BaseModel):
    description: Optional[str] = None
    danger_level: Optional[DangerLevel] = None
    radius_meters: Optional[int] = None
    is_active: Optional[bool] = None


class DangerZoneOut(BaseModel):
    id: int
    name: str
    description: str
    danger_level: DangerLevel
    lat: float
    lng: float
    radius_meters: int
    photo_url: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
