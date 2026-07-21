"""Schemas Pydantic — contratos de entrada/salida de la API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


# ─── Usuarios ───
class UserCreate(BaseModel):
    nombre: str
    apellido: str
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    nombre: str | None = None
    apellido: str | None = None
    edad: int | None = None
    sexo: str | None = None
    foto_b64: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    edad: int | None = None
    sexo: str | None = None
    email: EmailStr | None = None


class ChangePasswordRequest(BaseModel):
    password_actual: str
    password_nuevo: str


# ─── Login / Token ───
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None


# ─── Preferencias ───
class PreferencesUpdate(BaseModel):
    theme: str | None = None
    language: str | None = None
    notifications_enabled: bool | None = None


class PreferencesOut(BaseModel):
    theme: str
    language: str
    notifications_enabled: bool

    model_config = ConfigDict(from_attributes=True)




# ─── Dispositivo ───
class DeviceStatusUpdate(BaseModel):
    device_name: str | None = None
    haptic_intensity: int | None = None
    last_calibration_at: str | None = None
    battery_pct: int | None = None
    calibrated: bool | None = None


class DeviceStatusOut(BaseModel):
    device_name: str
    haptic_intensity: int
    last_calibration_at: str | None
    battery_pct: int | None
    calibrated: bool
    connected: bool | None = None   # solo para inyección de demo (no es columna)

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


# ─── Notificaciones ───
class NotificationOut(BaseModel):
    id: int
    tipo: str
    titulo: str
    mensaje: str
    leida: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# ─── Racha ───
class RachaOut(BaseModel):
    """Racha de uso para el badge del Resumen."""
    racha_actual: int      # días consecutivos hasta hoy (o ayer, si hoy aún no hay sesión)
    racha_record: int      # racha más larga histórica
    activa_hoy: bool       # True si hoy ya hubo al menos una sesión