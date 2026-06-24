"""Schemas Pydantic — contratos de entrada/salida de la API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


# ─── Usuarios ───
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ─── Login / Token ───
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None


# ─── Preferencias ───
class PreferencesUpdate(BaseModel):
    device_name: str | None = None
    theme: str | None = None
    language: str | None = None
    notifications_enabled: bool | None = None


class PreferencesOut(BaseModel):
    device_name: str
    theme: str
    language: str
    notifications_enabled: bool

    model_config = ConfigDict(from_attributes=True)


# ─── Sesiones ───
class SessionCreate(BaseModel):
    """Lo que manda el ESP32 al terminar una sesión."""
    started_at: datetime
    duracion_min: float
    alertas_hapticas: int
    min_buena: float = 0.0   # minutos clasificados como buena postura
    min_mala: float = 0.0    # minutos clasificados como mala postura


class SessionOut(BaseModel):
    id: int
    started_at: datetime
    duracion_min: float
    alertas_hapticas: int
    score: float
    min_buena: float
    min_mala: float

    model_config = ConfigDict(from_attributes=True)


class ScoreSummary(BaseModel):
    """Resumen de score para mostrar en la pantalla principal."""
    score_promedio: float        # promedio de todas las sesiones
    score_ultima_sesion: float | None
    total_sesiones: int
    total_min_uso: float
    total_alertas: int = 0       # suma de alertas hápticas del período
    total_min_buena: float = 0.0  # minutos totales en buena postura
    total_min_mala: float = 0.0   # minutos totales en mala postura