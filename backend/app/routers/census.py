from __future__ import annotations
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.census import CensusRecord
from app.models.user import User, UserRole
from app.services.auth import get_current_user

log = logging.getLogger(__name__)
router = APIRouter(prefix="/census", tags=["Census"])

ALLOWED_ROLES = (UserRole.admin, UserRole.coordinator, UserRole.volunteer)


def _require_census_access(user: User):
    if user.role not in ALLOWED_ROLES:
        raise HTTPException(403, "Sin permisos")


def _payload(r: CensusRecord, registered_by_name: str = None) -> dict:
    return {
        "id": r.id,
        "full_name": r.full_name,
        "document_number": r.document_number,
        "age": r.age,
        "gender": r.gender,
        "phone": r.phone,
        "whatsapp": r.whatsapp,
        "address": r.address,
        "neighborhood": r.neighborhood,
        "lat": r.lat,
        "lng": r.lng,
        "people_count": r.people_count,
        "children_count": r.children_count,
        "elderly_count": r.elderly_count,
        "needs": json.loads(r.needs) if r.needs else [],
        "vulnerable": json.loads(r.vulnerable) if r.vulnerable else [],
        "shelter_status": r.shelter_status,
        "notes": r.notes,
        "registered_by": r.registered_by,
        "registered_by_name": registered_by_name,
        "created_at": r.created_at.isoformat() + "Z",
        "updated_at": r.updated_at.isoformat() + "Z",
    }


@router.get("")
async def list_census(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_census_access(current_user)
    result = await db.execute(
        select(CensusRecord)
        .where(CensusRecord.is_active == True)  # noqa
        .order_by(CensusRecord.created_at.desc())
    )
    records = result.scalars().all()

    # Cargar nombres de registradores
    out = []
    for r in records:
        name = None
        if r.registered_by:
            u = (await db.execute(select(User).where(User.id == r.registered_by))).scalar_one_or_none()
            if u:
                name = f"{u.full_name}{' ' + u.last_name if u.last_name else ''}"
        out.append(_payload(r, name))
    return out


@router.post("")
async def create_census(
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_census_access(current_user)

    name = str(body.get("full_name", "")).strip()
    if not name:
        raise HTTPException(400, "El nombre es requerido")

    needs = body.get("needs", [])
    vulnerable = body.get("vulnerable", [])

    r = CensusRecord(
        full_name=name,
        document_number=body.get("document_number"),
        age=body.get("age"),
        gender=body.get("gender"),
        phone=body.get("phone"),
        whatsapp=body.get("whatsapp"),
        address=body.get("address"),
        neighborhood=body.get("neighborhood"),
        lat=body.get("lat"),
        lng=body.get("lng"),
        people_count=int(body.get("people_count", 1)),
        children_count=int(body.get("children_count", 0)),
        elderly_count=int(body.get("elderly_count", 0)),
        needs=json.dumps(needs) if needs else None,
        vulnerable=json.dumps(vulnerable) if vulnerable else None,
        shelter_status=body.get("shelter_status"),
        notes=body.get("notes"),
        registered_by=current_user.id,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return _payload(r, f"{current_user.full_name}{' ' + current_user.last_name if current_user.last_name else ''}")


@router.patch("/{record_id}")
async def update_census(
    record_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_census_access(current_user)

    r = (await db.execute(select(CensusRecord).where(CensusRecord.id == record_id))).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Registro no encontrado")

    allowed = {"full_name", "document_number", "age", "gender", "phone", "whatsapp",
               "address", "neighborhood", "lat", "lng", "people_count", "children_count",
               "elderly_count", "shelter_status", "notes"}
    vals: dict = {"updated_at": datetime.utcnow()}
    for k, v in body.items():
        if k in allowed:
            vals[k] = v

    if "needs" in body:
        vals["needs"] = json.dumps(body["needs"]) if body["needs"] else None
    if "vulnerable" in body:
        vals["vulnerable"] = json.dumps(body["vulnerable"]) if body["vulnerable"] else None

    await db.execute(update(CensusRecord).where(CensusRecord.id == record_id).values(**vals))
    await db.commit()
    return {"ok": True}


@router.delete("/{record_id}")
async def delete_census(
    record_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_census_access(current_user)
    await db.execute(
        update(CensusRecord)
        .where(CensusRecord.id == record_id)
        .values(is_active=False, updated_at=datetime.utcnow())
    )
    await db.commit()
    return {"ok": True}
