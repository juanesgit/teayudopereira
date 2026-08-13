from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class UserCreate(BaseModel):
    full_name: str
    last_name: Optional[str] = None
    id_number: Optional[str] = None
    phone: str
    email: Optional[EmailStr] = None
    password: str
    role: UserRole = UserRole.victim
    skills: Optional[str] = None
    neighborhood: Optional[str] = None


class UserOut(BaseModel):
    id: int
    full_name: str
    last_name: Optional[str]
    id_number: Optional[str]
    phone: str
    email: Optional[str]
    role: UserRole
    skills: Optional[str]
    neighborhood: Optional[str]
    action_lat: Optional[float]
    action_lng: Optional[float]
    action_radius_km: Optional[float]
    sms_consent_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    action_lat: Optional[float] = None
    action_lng: Optional[float] = None
    action_radius_km: Optional[float] = None
    skills: Optional[str] = None
    neighborhood: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    phone: str
    password: str
