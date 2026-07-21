"""Configuración central del backend.

Las variables sensibles se leen desde un archivo .env (no versionado).
Tener un .env.example en el repo con valores de ejemplo.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base de datos
    database_url: str = "sqlite:///./alina.db"

    # JWT
    secret_key: str = "cambiar-esta-clave-en-produccion"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 1 día

    # Endpoints de debug/demo (forzar la racha, etc.). Poner en False en producción.
    debug: bool = True

    # CORS (orígenes permitidos para el frontend Flet web)
    cors_origins: list[str] = [
        "http://localhost",
        "http://localhost:8550",  # Flet web por defecto
        "http://127.0.0.1:8550",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
