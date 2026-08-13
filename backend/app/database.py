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
        from app.models import user, report, aid_point, danger_zone, chat, guest_session, push_subscription  # noqa: F401
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
            "ALTER TABLE danger_zones ADD COLUMN address VARCHAR(300)",
            "ALTER TABLE users ADD COLUMN sms_consent_at DATETIME",
            "ALTER TABLE users ADD COLUMN reset_otp VARCHAR(6)",
            "ALTER TABLE users ADD COLUMN reset_otp_expires DATETIME",
            "ALTER TABLE chat_messages ADD COLUMN channel VARCHAR(60) NOT NULL DEFAULT 'group'",
            "ALTER TABLE chat_messages ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 0",
        ]
        for sql in migrations:
            try:
                await conn.execute(__import__('sqlalchemy').text(sql))
            except Exception:
                pass  # columna ya existe — ignorar

    # Migración: eliminar CHECK constraint del rol para soportar 'admin'
    await _migrate_role_column()
    # Migración: eliminar CHECK constraint de aid_type para soportar 'veterinary'
    await _migrate_aid_type_column()

    # Crear admin inicial si está configurado y no existe
    await _seed_admin()


async def _migrate_role_column():
    """
    SQLite no soporta ALTER COLUMN. Para eliminar el CHECK constraint
    del enum de roles, recreamos la tabla con una copia sin constraint.
    Solo se ejecuta si la tabla tiene el constraint antiguo.
    """
    import aiosqlite
    from app.config import settings
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    try:
        async with aiosqlite.connect(db_path) as db:
            # Verificar si el constraint existe leyendo el CREATE TABLE
            async with db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='users'"
            ) as cur:
                row = await cur.fetchone()
            if not row:
                return
            schema = row[0] or ""
            # Si ya no tiene el CHECK con la lista vieja, no hacer nada
            if "CHECK" not in schema or "admin" in schema:
                return
            # Recrear tabla sin CHECK constraint
            import logging
            logging.getLogger(__name__).info("Migrando tabla users: eliminando CHECK constraint de role")
            await db.executescript("""
                PRAGMA foreign_keys=OFF;
                CREATE TABLE IF NOT EXISTS users_new (
                    id INTEGER PRIMARY KEY,
                    full_name VARCHAR(120) NOT NULL,
                    last_name VARCHAR(120),
                    id_number VARCHAR(30),
                    phone VARCHAR(20) UNIQUE NOT NULL,
                    email VARCHAR(120) UNIQUE,
                    hashed_password VARCHAR(256) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'victim',
                    skills VARCHAR(256),
                    neighborhood VARCHAR(100),
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    action_lat FLOAT,
                    action_lng FLOAT,
                    action_radius_km FLOAT,
                    sms_consent_at DATETIME,
                    created_at DATETIME NOT NULL
                );
                INSERT INTO users_new SELECT
                    id, full_name, last_name, id_number, phone, email,
                    hashed_password, role, skills, neighborhood, is_active,
                    action_lat, action_lng, action_radius_km, NULL, created_at
                FROM users;
                DROP TABLE users;
                ALTER TABLE users_new RENAME TO users;
                PRAGMA foreign_keys=ON;
            """)
            await db.commit()
            logging.getLogger(__name__).info("Migración de tabla users completada")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Error en migración role column: %s", e)


async def _migrate_aid_type_column():
    """Elimina el CHECK constraint de aid_type en aid_points para soportar 'veterinary'."""
    import aiosqlite
    from app.config import settings
    db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    try:
        async with aiosqlite.connect(db_path) as db:
            async with db.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='aid_points'"
            ) as cur:
                row = await cur.fetchone()
            if not row:
                return
            schema = row[0] or ""
            if "veterinary" in schema or "CHECK" not in schema:
                return  # ya migrado o sin constraint
            import logging
            logging.getLogger(__name__).info("Migrando aid_points: eliminando CHECK constraint de aid_type")
            await db.executescript("""
                PRAGMA foreign_keys=OFF;
                CREATE TABLE IF NOT EXISTS aid_points_new (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(150) NOT NULL,
                    aid_type VARCHAR(20) NOT NULL,
                    description TEXT,
                    address VARCHAR(256) NOT NULL,
                    lat FLOAT NOT NULL,
                    lng FLOAT NOT NULL,
                    contact_phone VARCHAR(20),
                    capacity INTEGER,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    created_by INTEGER REFERENCES users(id),
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                );
                INSERT INTO aid_points_new SELECT * FROM aid_points;
                DROP TABLE aid_points;
                ALTER TABLE aid_points_new RENAME TO aid_points;
                PRAGMA foreign_keys=ON;
            """)
            await db.commit()
            logging.getLogger(__name__).info("Migración aid_points completada")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("Error en migración aid_type: %s", e)


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
