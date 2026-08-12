from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        from app.models import user, report, aid_point, danger_zone  # noqa: F401
        await conn.run_sync(Base.metadata.create_all)
        # Migraciones manuales — agrega columnas nuevas sin borrar datos
        migrations = [
            "ALTER TABLE reports ADD COLUMN photo_url VARCHAR(512)",
            "ALTER TABLE reports ADD COLUMN extra_data TEXT",
            "ALTER TABLE users ADD COLUMN action_lat FLOAT",
            "ALTER TABLE users ADD COLUMN action_lng FLOAT",
            "ALTER TABLE users ADD COLUMN action_radius_km FLOAT",
            "ALTER TABLE users ADD COLUMN last_name VARCHAR(120)",
            "ALTER TABLE users ADD COLUMN id_number VARCHAR(30)",
            "ALTER TABLE danger_zones ADD COLUMN photo_url VARCHAR(512)",
        ]
        for sql in migrations:
            try:
                await conn.execute(__import__('sqlalchemy').text(sql))
            except Exception:
                pass  # columna ya existe — ignorar

    # Crear admin inicial si está configurado y no existe
    await _seed_admin()


async def _seed_admin():
    from app.config import settings
    from app.models.user import User, UserRole
    from sqlalchemy import select
    import bcrypt

    if not settings.ADMIN_PHONE or not settings.ADMIN_PASSWORD:
        return

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.phone == settings.ADMIN_PHONE)
        )
        if result.scalar_one_or_none():
            return  # ya existe

        hashed = bcrypt.hashpw(settings.ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        admin = User(
            full_name=settings.ADMIN_NAME,
            phone=settings.ADMIN_PHONE,
            hashed_password=hashed,
            role=UserRole.admin,
            is_active=True,
        )
        session.add(admin)
        await session.commit()
        import logging
        logging.getLogger(__name__).info("Admin creado: %s", settings.ADMIN_PHONE)
