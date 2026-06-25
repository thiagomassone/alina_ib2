"""Endpoints de estado y configuración del dispositivo ALINA."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..models import DeviceStatus, User
from ..schemas import DeviceStatusOut, DeviceStatusUpdate
from ..security import get_current_user

router = APIRouter(prefix="/device", tags=["device"])


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
    """Estado actual del dispositivo — nombre, batería, última calibración."""
    return _get_or_create(db, current_user)


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
    - Recibir heartbeat del ESP32 (actualiza battery_pct)
    """
    ds = _get_or_create(db, current_user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(ds, field, value)
    db.commit()
    db.refresh(ds)
    return ds