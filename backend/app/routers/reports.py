from __future__ import annotations
import asyncio
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.database import get_db
from app.models.report import Report
from app.models.user import User, UserRole
from app.schemas.report import ReportCreate, ReportUpdate, ReportOut
from app.services.auth import get_current_user
from app.services import sms

router = APIRouter(prefix="/reports", tags=["Reportes de emergencia"])


async def _notify_volunteers_new_report(report: Report, db: AsyncSession) -> None:
    """Envía SMS a todos los voluntarios/coordinadores activos con teléfono registrado."""
    try:
        result = await db.execute(
            select(User).where(
                User.role.in_([UserRole.volunteer, UserRole.coordinator]),
                User.is_active == True,  # noqa: E712
                User.phone != None,  # noqa: E711
            )
        )
        volunteers = result.scalars().all()
        phones = [v.phone for v in volunteers if v.phone]
        if not phones:
            return
        address = report.address or f"({report.lat:.4f}, {report.lng:.4f})"
        message = sms.msg_nuevo_reporte(report.need_type.value, address, report.id)
        await sms.send_sms(phones, message)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Error notificando voluntarios: %s", exc)


async def _notify_assigned_volunteer(report: Report, volunteer_id: int, db: AsyncSession) -> None:
    """Notifica al voluntario asignado y, si hay teléfono en el reporte, incluye el contacto."""
    try:
        result = await db.execute(select(User).where(User.id == volunteer_id))
        volunteer = result.scalar_one_or_none()
        if not volunteer or not volunteer.phone:
            return
        contact_name = report.contact_name or "la persona afectada"
        contact_phone = report.contact_phone or "sin teléfono"
        message = sms.msg_asignado(volunteer.full_name, report.id, contact_name, contact_phone)
        await sms.send_sms([volunteer.phone], message)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Error notificando voluntario asignado: %s", exc)


@router.post("/", response_model=ReportOut, status_code=201)
async def create_report(
    data: ReportCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Cualquier persona puede crear un reporte, sin necesidad de estar autenticada."""
    report = Report(**data.model_dump())
    db.add(report)
    await db.commit()
    await db.refresh(report)
    # Notificar voluntarios en background (no bloquea la respuesta)
    background_tasks.add_task(_notify_volunteers_new_report, report, db)
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
    background_tasks: BackgroundTasks,
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

    prev_assigned = report.assigned_to
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(report, field, value)

    await db.commit()
    await db.refresh(report)

    # Si se acaba de asignar un voluntario, notificarle por SMS
    if data.assigned_to and data.assigned_to != prev_assigned:
        background_tasks.add_task(_notify_assigned_volunteer, report, data.assigned_to, db)

    return report
