from pathlib import Path
from pydantic_settings import BaseSettings

# Ruta absoluta al directorio del backend
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    SECRET_KEY: str = "cambia_esto_por_una_clave_segura"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    # Ruta absoluta para evitar errores de I/O con rutas relativas
    DATABASE_URL: str = f"sqlite+aiosqlite:///{BASE_DIR}/pereira_alerta.db"
    # Inalambria SMS — dejar vacío para deshabilitar
    INALAMBRIA_API_KEY: str = ""
    # Admin inicial — se crea automáticamente al arrancar si no existe
    ADMIN_PHONE: str = ""
    ADMIN_PASSWORD: str = ""
    ADMIN_NAME: str = "Administrador"
    # Redis — Pub/Sub para WebSocket multi-worker
    REDIS_URL: str = "redis://localhost:6379/0"
    # Web Push VAPID (generadas con cryptography)
    VAPID_PUBLIC_KEY: str = "BCPzvN3YgffxPj81-msoINbKefqCYaTKsVTZ1LZv7zL6reIVtlao6P1g2G28OvGK6kAYzuBv-TkKHphNBVN5zTU"
    VAPID_PRIVATE_KEY: str = "qiSlt8r-QBY295iq3SOdJY61KPhgDjNl5NMRccW6oYM"
    VAPID_CLAIMS_EMAIL: str = "admin@teayudopereira.co"

    class Config:
        env_file = ".env"


settings = Settings()
