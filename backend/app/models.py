"""Modelos ORM de SQLAlchemy."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    preferences: Mapped["UserPreferences"] = relationship(
        "UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserPreferences(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    # Ejemplos de preferencias — extender según necesidad
    theme: Mapped[str] = mapped_column(String(16), default="light")  # light / dark
    language: Mapped[str] = mapped_column(String(8), default="es")
    notifications_enabled: Mapped[bool] = mapped_column(default=True)
    extra_json: Mapped[str] = mapped_column(Text, default="{}")

    user: Mapped[User] = relationship("User", back_populates="preferences")



class DeviceStatus(Base):
    """Estado y configuración del dispositivo ALINA asociado al usuario.

    Se actualiza:
    - device_name / haptic_intensity: cuando el usuario aplica cambios desde la app
    - last_calibration_at: cuando se completa una calibración
    - battery_pct: con cada heartbeat del ESP32 (vía WebSocket/BLE)
    """

    __tablename__ = "device_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    device_name: Mapped[str] = mapped_column(String(64), default="ALINA Dispositivo")
    haptic_intensity: Mapped[int] = mapped_column(Integer, default=60)   # 0–100
    last_calibration_at: Mapped[str | None] = mapped_column(String(32), default=None, nullable=True)
    battery_pct: Mapped[int | None] = mapped_column(Integer, default=None, nullable=True)
    calibrated: Mapped[bool] = mapped_column(default=False)  # True después de calibrar, False al apagar/terminar sesión

    user: Mapped["User"] = relationship("User", back_populates="device_status")

class Session(Base):
    """Sesión de uso del dispositivo ALINA.

    Cada vez que el usuario activa el monitoreo y lo detiene, se crea
    una fila acá. El score se calcula en el endpoint y se almacena
    ya listo para no recalcular en cada consulta.

    score = max(0, 100 - (alertas_hapticas / duracion_min) * 10)
    El factor 10 es ajustable empíricamente.
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    duracion_min: Mapped[float] = mapped_column()          # duración real en minutos
    alertas_hapticas: Mapped[int] = mapped_column(Integer) # veces que vibró para corregir
    score: Mapped[float] = mapped_column()                 # 0–100, calculado al cerrar
    min_buena: Mapped[float] = mapped_column(default=0.0)  # minutos en buena postura
    min_mala: Mapped[float] = mapped_column(default=0.0)   # minutos en mala postura

    user: Mapped["User"] = relationship("User", back_populates="sessions")


# Agregar relación inversa en User
User.sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
User.device_status = relationship("DeviceStatus", back_populates="user", uselist=False, cascade="all, delete-orphan")