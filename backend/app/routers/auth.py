import random
import string
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut, Token, LoginRequest
from app.services.auth import hash_password, verify_password, create_access_token, get_current_user
from app.services import sms

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/register", response_model=Token, status_code=201)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Verificar si el teléfono ya existe
    result = await db.execute(select(User).where(User.phone == data.phone))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="El teléfono ya está registrado")

    user = User(
        full_name=data.full_name,
        phone=data.phone,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=data.role,
        skills=data.skills,
        neighborhood=data.neighborhood,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(user.id)
    return Token(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=Token)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == data.phone))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Teléfono o contraseña incorrectos")

    token = create_access_token(user.id)
    return Token(access_token=token, user=UserOut.model_validate(user))


class ForgotPasswordRequest(BaseModel):
    phone: str

class ResetPasswordRequest(BaseModel):
    phone: str
    otp: str
    new_password: str


@router.post("/forgot-password")
async def forgot_password(
    data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Genera OTP de 6 dígitos y lo envía por SMS. Expira en 10 minutos."""
    phone = data.phone.replace(" ", "").strip()
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    # Respuesta genérica siempre — no revelar si el número existe
    if not user or not user.is_active:
        return {"ok": True, "msg": "Si el número está registrado, recibirás un código SMS."}

    otp = "".join(random.choices(string.digits, k=6))
    user.reset_otp = otp
    user.reset_otp_expires = datetime.utcnow() + timedelta(minutes=10)
    await db.commit()

    mensaje = (
        f"[Te Ayudo Pereira] Tu codigo de verificacion es: {otp}. "
        f"Valido por 10 minutos. No lo compartas con nadie."
    )
    background_tasks.add_task(sms.send_sms, [phone], mensaje)

    return {"ok": True, "msg": "Si el número está registrado, recibirás un código SMS."}


@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Valida OTP y actualiza la contraseña."""
    phone = data.phone.replace(" ", "").strip()
    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()

    if not user or not user.reset_otp or not user.reset_otp_expires:
        raise HTTPException(status_code=400, detail="Código inválido o expirado")

    if datetime.utcnow() > user.reset_otp_expires:
        user.reset_otp = None
        user.reset_otp_expires = None
        await db.commit()
        raise HTTPException(status_code=400, detail="El código expiró. Solicita uno nuevo.")

    if user.reset_otp != data.otp.strip():
        raise HTTPException(status_code=400, detail="Código incorrecto")

    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    user.hashed_password = hash_password(data.new_password)
    user.reset_otp = None
    user.reset_otp_expires = None
    await db.commit()

    return {"ok": True, "msg": "Contraseña actualizada correctamente"}


@router.post("/sms-consent", response_model=UserOut)
async def accept_sms_consent(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra el consentimiento explícito del usuario para recibir SMS."""
    current_user.sms_consent_at = datetime.utcnow()
    await db.commit()
    await db.refresh(current_user)
    return UserOut.model_validate(current_user)
