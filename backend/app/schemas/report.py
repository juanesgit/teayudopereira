from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.report import NeedType, ReportStatus


class ReportCreate(BaseModel):
    reporter_name: str
    reporter_phone: Optional[str] = None
    need_type: NeedType
    description: str
    address: str
    lat: float
    lng: float
    people_count: int = 1
    photo_url: Optional[str] = None
    extra_data: Optional[str] = None


class ReportUpdate(BaseModel):
    status: Optional[ReportStatus] = None
    assigned_to: Optional[int] = None
    description: Optional[str] = None


class ReportOut(BaseModel):
    id: int
    reporter_name: str
    reporter_phone: Optional[str]
    need_type: NeedType
    description: str
    address: str
    lat: float
    lng: float
    people_count: int
    status: ReportStatus
    assigned_to: Optional[int]
    photo_url: Optional[str]
    extra_data: Optional[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
