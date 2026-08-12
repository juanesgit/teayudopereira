from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.report import Report
from app.models.user import User, UserRole
from app.schemas.report import ReportCreate, ReportUpdate, ReportOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/reports", tags=["Reportes de emergencia"])


@router.post("/", response_model=ReportOut, status_code=201)
async def create_report(data: ReportCreate, db: AsyncSession = Depends(get_db)):
    """Cualquier persona puede crear un reporte, sin necesidad de estar autenticada."""
    report = Report(**data.model_dump())
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


@router.get("/", response_model=List[ReportOut])
async def list_reports(
    status: Optional[str] = None,
    need_type: Optional[str] = None,
    assigned_to: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """Lista todos los reportes activos. Filtrable por estado, tipo y voluntario asignado."""
    query = select(Report)
    if status:
        query = query.where(Report.status == status)
    if need_type:
        query = query.where(Report.need_type == need_type)
    if assigned_to is not None:
        query = query.where(Report.assigned_to == assigned_to)
    query = query.order_by(Report.created_at.desc())
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return report


@router.patch("/{report_id}", response_model=ReportOut)
async def update_report(
    report_id: int,
    data: ReportUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Solo voluntarios y coordinadores pueden actualizar el estado de un reporte."""
    if current_user.role == UserRole.victim:
        raise HTTPException(status_code=403, detail="Sin permisos para actualizar reportes")

    result = await db.execute(select(Report).where(Report.id == report_id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(report, field, value)

    await db.commit()
    await db.refresh(report)
    return report
