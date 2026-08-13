from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pathlib import Path
import uuid, shutil

from app.database import init_db
from app.routers import auth, reports, aid_points, danger_zones, users, admin

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


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
