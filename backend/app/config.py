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

    class Config:
        env_file = ".env"


settings = Settings()
