from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.aid_point import AidPoint
from app.models.user import User, UserRole
from app.schemas.aid_point import AidPointCreate, AidPointUpdate, AidPointOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/aid-points", tags=["Puntos de ayuda"])


@router.post("/", response_model=AidPointOut, status_code=201)
async def create_aid_point(
    data: AidPointCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Solo voluntarios y coordinadores pueden registrar puntos de ayuda."""
    if current_user.role == UserRole.victim:
        raise HTTPException(status_code=403, detail="Sin permisos para registrar puntos de ayuda")

    aid_point = AidPoint(**data.model_dump(), created_by=current_user.id)
    db.add(aid_point)
    await db.commit()
    await db.refresh(aid_point)
    return aid_point


@router.get("/", response_model=List[AidPointOut])
async def list_aid_points(
    aid_type: Optional[str] = None,
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    query = select(AidPoint)
    if active_only:
        query = query.where(AidPoint.is_active == True)  # noqa: E712
    if aid_type:
        query = query.where(AidPoint.aid_type == aid_type)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/{aid_id}", response_model=AidPointOut)
async def update_aid_point(
    aid_id: int,
    data: AidPointUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.victim:
        raise HTTPException(status_code=403, detail="Sin permisos")

    result = await db.execute(select(AidPoint).where(AidPoint.id == aid_id))
    aid = result.scalar_one_or_none()
    if not aid:
        raise HTTPException(status_code=404, detail="Punto de ayuda no encontrado")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(aid, field, value)

    await db.commit()
    await db.refresh(aid)
    return aid
