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
        ]
        for sql in migrations:
            try:
                await conn.execute(__import__('sqlalchemy').text(sql))
            except Exception:
                pass  # columna ya existe — ignorar
