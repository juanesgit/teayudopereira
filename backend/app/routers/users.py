from __future__ import annotations
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserOut, UserUpdate
from app.services.auth import get_current_user

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
async def update_me(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.get("/volunteers", response_model=List[UserOut])
async def list_volunteers(
    skill: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista voluntarios disponibles. Filtrable por habilidad."""
    query = select(User).where(User.role == UserRole.volunteer, User.is_active == True)  # noqa: E712
    result = await db.execute(query)
    volunteers = result.scalars().all()

    if skill:
        volunteers = [v for v in volunteers if v.skills and skill.lower() in v.skills.lower()]

    return volunteers
