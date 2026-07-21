"""Endpoints de notificaciones del sistema ALINA.

El GET de la lista (y el unread_count) corren un "sync" que:
  - Purga las notificaciones vencidas (TTL = 3 días).
  - Genera/borra las notificaciones de ESTADO (no evento):
      * calibration_pending : si el dispositivo está sin calibrar.
      * racha_en_riesgo     : racha activa, sin sesión hoy y ya son >=20:00.
      * resumen_semanal     : los lunes, 1 por semana.
Las de EVENTO (score bajo, buena sesión, nuevo récord) se crean en sessions.py,
y la de dispositivo desconectado la dispara la app vía POST /device-disconnected.
"""

from __future__ import annotations

from datetime import datetime, timedelta, date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..config import settings
from ..models import (
    DeviceStatus,
    Notification,
    Session as SessionModel,
    User,
    crear_notificacion,
)
from ..schemas import NotificationOut
from ..security import get_current_user
from .sessions import _calcular_racha, _dias_con_sesion, _racha_record

router = APIRouter(prefix="/notifications", tags=["notifications"])

_TTL_DIAS = 3                       # tiempo de vida de una notificación
_DESCONEXION_DEBOUNCE_MIN = 10      # no repetir "desconectado" dentro de esta ventana


# ── Helpers de generación ─────────────────────────────────────────────────────
def _purgar_vencidas(db: DBSession, user_id: int) -> None:
    limite = datetime.utcnow() - timedelta(days=_TTL_DIAS)
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.created_at < limite,
    ).delete(synchronize_session=False)


def _existe(db: DBSession, user_id: int, tipo: str, desde: datetime | None = None) -> bool:
    q = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.tipo == tipo,
    )
    if desde is not None:
        q = q.filter(Notification.created_at >= desde)
    return q.first() is not None


def _borrar_tipo(db: DBSession, user_id: int, tipo: str) -> None:
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.tipo == tipo,
    ).delete(synchronize_session=False)


def _texto_resumen_semanal(db: DBSession, user_id: int) -> str | None:
    hoy = date.today()
    rows = db.query(SessionModel).filter(SessionModel.user_id == user_id).all()

    def prom(inicio: date, fin: date) -> float | None:
        ss = [float(s.score) for s in rows if inicio <= s.started_at.date() <= fin]
        return (sum(ss) / len(ss)) if ss else None

    act = prom(hoy - timedelta(days=6), hoy)
    prev = prom(hoy - timedelta(days=13), hoy - timedelta(days=7))
    if act is None:
        return None
    if prev is None or prev == 0:
        return f"Esta semana tu score promedio fue {act:.0f}/100. ¡Seguí sumando sesiones!"
    delta = (act - prev) / prev * 100
    if delta >= 0:
        return f"Esta semana mejoraste un {delta:.0f}% (score promedio {act:.0f}/100). ¡Buen trabajo!"
    return f"Esta semana tu score bajó un {abs(delta):.0f}% ({act:.0f}/100). La próxima repuntás."


def _sync_estado(db: DBSession, user_id: int) -> None:
    """Purga vencidas y genera/borra las notificaciones de estado."""
    _purgar_vencidas(db, user_id)
    ahora = datetime.utcnow()

    # Calibración: si el dispositivo está sin calibrar, avisar; si calibra, borrar.
    ds = db.query(DeviceStatus).filter(DeviceStatus.user_id == user_id).first()
    if ds is not None:
        if not ds.calibrated:
            if not _existe(db, user_id, "calibration_pending"):
                crear_notificacion(
                    db, user_id, "calibration_pending",
                    "Dispositivo sin calibrar",
                    "Tu ALINA no está calibrado. Calibralo antes de tu próxima sesión "
                    "para que las alertas sean precisas.",
                )
        else:
            _borrar_tipo(db, user_id, "calibration_pending")

    # Racha en riesgo: racha activa, sin sesión hoy y ya son >=20:00 (1 cada 16h).
    dias = _dias_con_sesion(db, user_id)
    actual, _ = _calcular_racha(dias)
    if actual > 0 and date.today() not in dias and datetime.now().hour >= 20:
        if not _existe(db, user_id, "racha_en_riesgo", desde=ahora - timedelta(hours=16)):
            crear_notificacion(
                db, user_id, "racha_en_riesgo",
                "Tu racha está en riesgo",
                f"Todavía no usaste ALINA hoy. Hacé una sesión para no cortar "
                f"tu racha de {actual} días.",
            )

    # Resumen semanal: los lunes, 1 por semana.
    if date.today().weekday() == 0:
        if not _existe(db, user_id, "resumen_semanal", desde=ahora - timedelta(days=6)):
            msg = _texto_resumen_semanal(db, user_id)
            if msg:
                crear_notificacion(db, user_id, "resumen_semanal", "Tu resumen de la semana", msg)

    db.commit()


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("", response_model=list[NotificationOut])
def list_notifications(
    limit: int = 50,
    solo_no_leidas: bool = False,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _sync_estado(db, current_user.id)
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if solo_no_leidas:
        q = q.filter(Notification.leida == False)
    return q.order_by(Notification.created_at.desc()).limit(limit).all()


@router.get("/unread_count")
def unread_count(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _sync_estado(db, current_user.id)
    count = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id, Notification.leida == False)
        .count()
    )
    return {"count": count}


@router.patch("/read_all")
def mark_all_read(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marca todo como visto (se llama al abrir el tab Alertas → limpia el badge)."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.leida == False,
    ).update({"leida": True})
    db.commit()
    return {"ok": True}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification(
    notification_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Borrado manual (swipe → borrar)."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    db.delete(notif)
    db.commit()


@router.post("/device-disconnected", status_code=status.HTTP_201_CREATED)
def notify_device_disconnected(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """La app avisa cuando el ESP se desconecta. Con debounce para no spamear."""
    desde = datetime.utcnow() - timedelta(minutes=_DESCONEXION_DEBOUNCE_MIN)
    if _existe(db, current_user.id, "device_disconnected", desde=desde):
        return {"ok": True, "creada": False}
    crear_notificacion(
        db, current_user.id, "device_disconnected",
        "Dispositivo desconectado",
        "Se perdió la conexión con tu ALINA. Revisá que esté encendido y en rango.",
    )
    return {"ok": True, "creada": True}


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints de DEMO — solo con settings.debug. Para emular notificaciones en la
# presentación sin esperar las condiciones reales (hora, día, score, etc.).
# ─────────────────────────────────────────────────────────────────────────────
def _require_debug() -> None:
    if not settings.debug:
        raise HTTPException(status_code=404, detail="No disponible")


@router.post("/debug/crear", response_model=NotificationOut)
def debug_crear(
    tipo: str = "session_score_low",
    titulo: str = "Notificación de prueba",
    mensaje: str = "Mensaje de ejemplo para la demo.",
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEMO] Crea una notificación con el tipo/título/mensaje que le pases."""
    _require_debug()
    return crear_notificacion(db, current_user.id, tipo, titulo, mensaje)


# Un ejemplo realista de cada tipo, para poblar la lista de una.
_DEMO_SEED = [
    ("session_score_low", "Sesión con postura baja",
     "Tu sesión del 21/07 a las 09:00 (30 min) tuvo un score de 58/100. Intentá mantener la espalda más erguida."),
    ("buena_sesion", "¡Gran sesión!",
     "Tu sesión del 21/07 a las 11:00 (30 min) cerró con 92/100. ¡Seguí así!"),
    ("nuevo_record", "¡Nuevo récord de score!",
     "Superaste tu mejor marca con 96/100 en tu sesión del 21/07 a las 18:20."),
    ("racha_en_riesgo", "Tu racha está en riesgo",
     "Todavía no usaste ALINA hoy. Hacé una sesión para no cortar tu racha de 7 días."),
    ("resumen_semanal", "Tu resumen de la semana",
     "Esta semana mejoraste un 12% (score promedio 84/100). ¡Buen trabajo!"),
    ("device_disconnected", "Dispositivo desconectado",
     "Se perdió la conexión con tu ALINA. Revisá que esté encendido y en rango."),
    ("calibration_pending", "Dispositivo sin calibrar",
     "Tu ALINA no está calibrado. Calibralo antes de tu próxima sesión para que las alertas sean precisas."),
]


@router.post("/debug/seed")
def debug_seed(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEMO] Crea un ejemplo de cada tipo de notificación (para screenshot)."""
    _require_debug()
    for tipo, titulo, mensaje in _DEMO_SEED:
        crear_notificacion(db, current_user.id, tipo, titulo, mensaje)
    return {"ok": True, "creadas": len(_DEMO_SEED)}