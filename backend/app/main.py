import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException

logging.basicConfig(level=logging.INFO)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pathlib import Path
import uuid, shutil

from app.config import settings
from app.database import init_db
from app.routers import auth, reports, aid_points, danger_zones, users, admin, chat, dm, guest_chat, push, geocode, medication, census
from app.services.broadcaster import group_broadcaster, room_broadcaster

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def _migrate_delivery_table():
    """Migración: report_id nullable + nuevas columnas en medication_deliveries."""
    import sqlite3, os, logging
    log = logging.getLogger(__name__)
    # Derivar path desde DATABASE_URL configurado (soporta teayudopereira.db u otro nombre)
    db_url = settings.DATABASE_URL  # e.g. sqlite+aiosqlite:////root/.../teayudopereira.db
    db_path = db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    if not db_path.startswith("/"):
        # Path relativo — resolver desde directorio del backend
        db_path = str(Path(__file__).resolve().parent.parent / db_path)
    log.info("_migrate_delivery_table: usando DB → %s", db_path)
    if not os.path.exists(db_path):
        log.info("_migrate_delivery_table: DB no existe aún, se omite.")
        return
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(medication_deliveries)")
        rows = cur.fetchall()
        if not rows:
            conn.close()
            return
        cols = {r[1]: r for r in rows}
        log.info("_migrate_delivery_table: columnas existentes → %s", list(cols.keys()))

        # Agregar columnas nuevas si faltan
        new_cols = [
            ("delivery_type",     "TEXT NOT NULL DEFAULT 'solicitude'"),
            ("recipient_id",      "TEXT"),
            ("recipient_phone",   "TEXT"),
            ("recipient_address", "TEXT"),
            ("delivery_group_id", "TEXT"),
            ("is_cancelled",      "INTEGER NOT NULL DEFAULT 0"),
            ("cancelled_at",      "DATETIME"),
        ]
        for col, defn in new_cols:
            if col not in cols:
                log.info("_migrate_delivery_table: agregando columna %s", col)
                cur.execute(f"ALTER TABLE medication_deliveries ADD COLUMN {col} {defn}")
                cols[col] = True  # marcar como presente

        # Recrear tabla si report_id sigue siendo NOT NULL
        cur.execute("PRAGMA table_info(medication_deliveries)")
        info = {r[1]: r for r in cur.fetchall()}
        if info.get("report_id", (None,)*4)[3]:  # notnull=1
            log.info("_migrate_delivery_table: report_id es NOT NULL — recreando tabla...")
            cur.execute("PRAGMA foreign_keys=OFF")
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS med_del_new (
                    id INTEGER PRIMARY KEY,
                    report_id INTEGER REFERENCES reports(id) ON DELETE SET NULL,
                    delivery_type TEXT NOT NULL DEFAULT 'solicitude',
                    delivery_group_id TEXT,
                    stock_id INTEGER REFERENCES medication_stock(id) ON DELETE SET NULL,
                    medication_name VARCHAR(200) NOT NULL,
                    quantity_delivered INTEGER NOT NULL DEFAULT 1,
                    unit VARCHAR(40) NOT NULL DEFAULT 'unidades',
                    delivered_to VARCHAR(150) NOT NULL,
                    recipient_id TEXT,
                    recipient_phone TEXT,
                    recipient_address TEXT,
                    delivered_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    delivery_notes TEXT,
                    delivered_at DATETIME NOT NULL,
                    created_at DATETIME NOT NULL
                );
                INSERT OR IGNORE INTO med_del_new
                    (id,report_id,delivery_type,stock_id,medication_name,quantity_delivered,
                     unit,delivered_to,recipient_id,recipient_phone,recipient_address,
                     delivered_by,delivery_notes,delivered_at,created_at)
                SELECT id,report_id,COALESCE(delivery_type,'solicitude'),stock_id,
                       medication_name,quantity_delivered,unit,delivered_to,
                       COALESCE(recipient_id,NULL),recipient_phone,recipient_address,
                       delivered_by,delivery_notes,delivered_at,created_at
                FROM medication_deliveries;
                DROP TABLE medication_deliveries;
                ALTER TABLE med_del_new RENAME TO medication_deliveries;
            """)
            cur.execute("PRAGMA foreign_keys=ON")
            log.info("_migrate_delivery_table: tabla recreada correctamente.")
        else:
            log.info("_migrate_delivery_table: report_id ya es nullable — no se requiere recreación.")

        conn.commit()
        conn.close()
        log.info("_migrate_delivery_table: migración completada.")
    except Exception as exc:
        logging.getLogger(__name__).error("_migrate_delivery_table ERROR: %s", exc, exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _migrate_delivery_table()
    await init_db()
    await group_broadcaster.setup(settings.REDIS_URL)
    await room_broadcaster.setup(settings.REDIS_URL)
    yield
    await group_broadcaster.teardown()
    await room_broadcaster.teardown()


app = FastAPI(
    title="Te Ayudo Pereira",
    description="Sistema de coordinación de ayuda humanitaria para Pereira",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(reports.router)
app.include_router(aid_points.router)
app.include_router(danger_zones.router)
app.include_router(users.router)
app.include_router(admin.router)
app.include_router(chat.router)
app.include_router(dm.router)
app.include_router(guest_chat.router)
app.include_router(push.router)
app.include_router(geocode.router)
app.include_router(medication.router)
app.include_router(census.router)


@app.get("/health")
async def health():
    return {"status": "ok", "sistema": "Te Ayudo Pereira"}


ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

@app.post("/upload")
async def upload_photo(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(400, "Solo se permiten imágenes JPG, PNG o WEBP")
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "jpg"
    filename = f"{uuid.uuid4()}.{ext}"
    dest = UPLOAD_DIR / filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"url": f"/static/uploads/{filename}"}


# Sirve el frontend desde /static
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def frontend():
    return FileResponse(
        STATIC_DIR / "index.html",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        }
    )


@app.get("/sw.js")
async def service_worker():
    """Service Worker en la raíz para que tenga scope /"""
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Service-Worker-Allowed": "/",
        }
    )


@app.get("/manifest.json")
async def manifest():
    return FileResponse(
        STATIC_DIR / "manifest.json",
        media_type="application/manifest+json",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    icon = STATIC_DIR / "icons" / "icon-192.png"
    if icon.exists():
        return FileResponse(icon, media_type="image/png",
                            headers={"Cache-Control": "public, max-age=604800"})
    return Response(status_code=204)
