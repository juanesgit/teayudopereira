from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.aid_point import AidType


class AidPointCreate(BaseModel):
    name: str
    aid_type: AidType
    description: Optional[str] = None
    address: str
    lat: float
    lng: float
    contact_phone: Optional[str] = None
    capacity: Optional[int] = None


class AidPointUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None
    contact_phone: Optional[str] = None


class AidPointOut(BaseModel):
    id: int
    name: str
    aid_type: AidType
    description: Optional[str]
    address: str
    lat: float
    lng: float
    contact_phone: Optional[str]
    capacity: Optional[int]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
