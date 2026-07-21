"""Endpoints de estado y configuración del dispositivo ALINA."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from ..config import settings
from ..database import get_db
from ..models import DeviceStatus, User
from ..schemas import DeviceStatusOut, DeviceStatusUpdate
from ..security import get_current_user

router = APIRouter(prefix="/device", tags=["device"])

# Override de demo en memoria (batería / calibrado / conexión) para presentar la
# app sin el ESP. Solo activo con settings.debug. Se resetea al reiniciar uvicorn.
_demo_estado: dict[int, dict] = {}


def _get_or_create(db: DBSession, user: User) -> DeviceStatus:
    """Obtener o crear el DeviceStatus del usuario."""
    ds = db.query(DeviceStatus).filter(DeviceStatus.user_id == user.id).first()
    if not ds:
        ds = DeviceStatus(user_id=user.id)
        db.add(ds)
        db.commit()
        db.refresh(ds)
    return ds


@router.get("", response_model=DeviceStatusOut)
def get_device_status(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Estado actual del dispositivo — nombre, batería, calibración, conexión."""
    ds = _get_or_create(db, current_user)
    ov = _demo_estado.get(current_user.id) if settings.debug else None
    if ov:
        db.expunge(ds)  # detach: el override NO se persiste en la base
        if "battery" in ov:
            ds.battery_pct = ov["battery"]
        if "calibrated" in ov:
            ds.calibrated = ov["calibrated"]
    ds.connected = (ov or {}).get("connected")
    return ds


@router.patch("", response_model=DeviceStatusOut)
def update_device_status(
    payload: DeviceStatusUpdate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar configuración o estado del dispositivo.

    Llamado desde la app al:
    - Cambiar nombre o intensidad háptica (botón Aplicar)
    - Completar calibración (guarda last_calibration_at)
    - Recibir el estado del ESP32 (actualiza battery_pct)
    """
    ds = _get_or_create(db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ds, field, value)
    db.commit()
    db.refresh(ds)
    ds.connected = None
    return ds


# ─────────────────────────────────────────────────────────────────────────────
# DEMO — inyectar estado del dispositivo por terminal (sin ESP). Solo con debug.
# ─────────────────────────────────────────────────────────────────────────────
def _require_debug() -> None:
    if not settings.debug:
        raise HTTPException(status_code=404, detail="No disponible")


@router.post("/debug/estado", response_model=DeviceStatusOut)
def debug_set_estado(
    battery: int | None = None,
    calibrated: bool | None = None,
    connected: bool | None = None,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEMO] Inyecta batería / calibrado / conexión del dispositivo.

    Ej: POST /device/debug/estado?battery=85&connected=true&calibrated=true
    La app lo levanta en su refresh (~3s). Solo con settings.debug.
    """
    _require_debug()
    ov = _demo_estado.setdefault(current_user.id, {})
    if battery is not None:
        ov["battery"] = max(0, min(100, battery))
    if calibrated is not None:
        ov["calibrated"] = calibrated
    if connected is not None:
        ov["connected"] = connected
    return get_device_status(db=db, current_user=current_user)


@router.delete("/debug/estado", status_code=status.HTTP_204_NO_CONTENT)
def debug_clear_estado(
    current_user: User = Depends(get_current_user),
):
    """[DEMO] Limpia el override y vuelve al estado real."""
    _require_debug()
    _demo_estado.pop(current_user.id, None)