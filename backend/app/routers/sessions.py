"""Endpoints de sesiones de uso del dispositivo ALINA."""

from __future__ import annotations
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from ..config import settings
from ..database import get_db
from ..models import Session as SessionModel, User, crear_notificacion
from ..schemas import RachaOut, ScoreSummary, SessionCreate, SessionOut
from ..security import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])

# Factor de penalización: cada alerta por minuto resta esta cantidad al score.
# Ajustar empíricamente una vez que el dispositivo esté calibrado.
_PENALTY_FACTOR = 10.0


def _calc_score(alertas: int, duracion_min: float) -> float:
    """Calcula el score de una sesión (0–100)."""
    if duracion_min <= 0:
        return 100.0
    rate = alertas / duracion_min          # alertas por minuto
    return max(0.0, round(100.0 - rate * _PENALTY_FACTOR, 1))



# Umbral de score bajo para generar notificación
_SCORE_BAJO = 65.0


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    score = _calc_score(payload.alertas_hapticas, payload.duracion_min)
    session = SessionModel(
        user_id=current_user.id,
        started_at=payload.started_at,
        duracion_min=payload.duracion_min,
        alertas_hapticas=payload.alertas_hapticas,
        score=score,
        min_buena=payload.min_buena,
        min_mala=payload.min_mala,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # ── Notificaciones por evento de esta sesión ─────────────────────────────
    mins = int(payload.duracion_min)
    dur_str = f"{mins // 60}h {mins % 60:02d}m" if mins >= 60 else f"{mins} min"
    cuando = payload.started_at.strftime('%d/%m a las %H:%M')

    # ¿Nuevo récord de score? (contra el mejor de las sesiones anteriores)
    mejor_previo = (
        db.query(func.max(SessionModel.score))
        .filter(SessionModel.user_id == current_user.id, SessionModel.id != session.id)
        .scalar()
    )
    record_score = mejor_previo is not None and score > mejor_previo

    # ¿Nueva racha récord? (comparar el récord con y sin el día de hoy)
    dias = _dias_con_sesion(db, current_user.id)
    record_racha_nuevo = _racha_record(dias)
    record_racha_previo = _racha_record(dias - {date.today()})
    record_racha = record_racha_nuevo > record_racha_previo and record_racha_previo > 0

    if score < _SCORE_BAJO:
        crear_notificacion(
            db=db, user_id=current_user.id, tipo="session_score_low",
            titulo="Sesión con postura baja",
            mensaje=f"Tu sesión del {cuando} ({dur_str}) tuvo un score de {int(score)}/100. "
                    f"Intentá mantener la espalda más erguida.",
        )
    elif score >= 85 and not record_score:
        crear_notificacion(
            db=db, user_id=current_user.id, tipo="buena_sesion",
            titulo="¡Gran sesión!",
            mensaje=f"Tu sesión del {cuando} ({dur_str}) cerró con {int(score)}/100. ¡Seguí así!",
        )

    if record_score:
        crear_notificacion(
            db=db, user_id=current_user.id, tipo="nuevo_record",
            titulo="¡Nuevo récord de score!",
            mensaje=f"Superaste tu mejor marca con {int(score)}/100 en tu sesión del {cuando}.",
        )

    if record_racha:
        crear_notificacion(
            db=db, user_id=current_user.id, tipo="nuevo_record",
            titulo="¡Nueva racha récord!",
            mensaje=f"Llegaste a {record_racha_nuevo} días seguidos usando ALINA. ¡Tu mejor racha!",
        )

    return session


@router.get("", response_model=list[SessionOut])
def list_sessions(
    limit: int = 50,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Últimas N sesiones del usuario (para el tab Historial)."""
    return (
        db.query(SessionModel)
        .filter(SessionModel.user_id == current_user.id)
        .order_by(SessionModel.started_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/score", response_model=ScoreSummary)
def get_score_summary(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Score promedio + última sesión para el tab Resumen."""
    rows = (
        db.query(SessionModel)
        .filter(SessionModel.user_id == current_user.id)
        .order_by(SessionModel.started_at.desc())
        .all()
    )

    if not rows:
        return ScoreSummary(
            score_promedio=0.0,
            score_ultima_sesion=None,
            total_sesiones=0,
            total_min_uso=0.0,
        )

    promedio = round(sum(r.score for r in rows) / len(rows), 1)
    total_min = round(sum(r.duracion_min for r in rows), 1)

    total_alertas = sum(r.alertas_hapticas for r in rows)
    total_min_buena = round(sum(r.min_buena for r in rows), 1)
    total_min_mala = round(sum(r.min_mala for r in rows), 1)
    return ScoreSummary(
        score_promedio=promedio,
        score_ultima_sesion=rows[0].score,
        total_sesiones=len(rows),
        total_min_uso=total_min,
        total_alertas=total_alertas,
        total_min_buena=total_min_buena,
        total_min_mala=total_min_mala,
    )



@router.get("/today", response_model=ScoreSummary)
def get_today_summary(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resumen de las sesiones de HOY — para la tarjeta Tiempo hoy del Resumen."""
    today = date.today()
    rows = (
        db.query(SessionModel)
        .filter(
            SessionModel.user_id == current_user.id,
            SessionModel.started_at >= datetime(today.year, today.month, today.day),
        )
        .order_by(SessionModel.started_at.desc())
        .all()
    )

    if not rows:
        return ScoreSummary(
            score_promedio=0.0,
            score_ultima_sesion=None,
            total_sesiones=0,
            total_min_uso=0.0,
        )

    promedio = round(sum(r.score for r in rows) / len(rows), 1)
    total_min = round(sum(r.duracion_min for r in rows), 1)

    total_alertas = sum(r.alertas_hapticas for r in rows)
    total_min_buena = round(sum(r.min_buena for r in rows), 1)
    total_min_mala = round(sum(r.min_mala for r in rows), 1)
    return ScoreSummary(
        score_promedio=promedio,
        score_ultima_sesion=rows[0].score,
        total_sesiones=len(rows),
        total_min_uso=total_min,
        total_alertas=total_alertas,
        total_min_buena=total_min_buena,
        total_min_mala=total_min_mala,
    )

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Borrar una sesión (por si el usuario quiere limpiar un registro erróneo)."""
    session = db.query(SessionModel).filter(
        SessionModel.id == session_id,
        SessionModel.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    db.delete(session)
    db.commit()

# ─────────────────────────────────────────────────────────────────────────────
# Racha de uso
# ─────────────────────────────────────────────────────────────────────────────
# Override en memoria para forzar la racha durante la demo de la presentación.
# Solo activo con settings.debug. No toca la base de datos y se resetea al
# reiniciar uvicorn.
_racha_override: dict[int, int] = {}


def _dias_con_sesion(db: DBSession, user_id: int) -> set[date]:
    """Conjunto de fechas (una por día) en las que el usuario tuvo >=1 sesión."""
    rows = (
        db.query(func.date(SessionModel.started_at))
        .filter(SessionModel.user_id == user_id)
        .distinct()
        .all()
    )
    dias: set[date] = set()
    for (d,) in rows:
        if d is None:
            continue
        if isinstance(d, str):
            d = date.fromisoformat(d)
        elif isinstance(d, datetime):
            d = d.date()
        dias.add(d)
    return dias


def _calcular_racha(dias: set[date], hoy: date | None = None) -> tuple[int, bool]:
    """Días consecutivos con sesión, contando hacia atrás desde hoy.

    Si hoy todavía no hay sesión pero ayer sí, la racha sigue viva (se ancla en
    ayer) hasta que termine el día. Devuelve (racha_actual, activa_hoy).
    """
    if not dias:
        return 0, False
    hoy = hoy or date.today()
    activa_hoy = hoy in dias
    ancla = hoy if activa_hoy else hoy - timedelta(days=1)
    if ancla not in dias:
        return 0, activa_hoy
    n, d = 0, ancla
    while d in dias:
        n += 1
        d -= timedelta(days=1)
    return n, activa_hoy


def _racha_record(dias: set[date]) -> int:
    """Racha más larga histórica."""
    if not dias:
        return 0
    ordenados = sorted(dias)
    mejor = actual = 1
    for prev, cur in zip(ordenados, ordenados[1:]):
        actual = actual + 1 if (cur - prev).days == 1 else 1
        mejor = max(mejor, actual)
    return mejor


@router.get("/racha", response_model=RachaOut)
def get_racha(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Racha de uso del usuario (para el badge del Resumen)."""
    dias = _dias_con_sesion(db, current_user.id)
    actual, activa_hoy = _calcular_racha(dias)
    record = _racha_record(dias)
    if settings.debug and current_user.id in _racha_override:
        actual = _racha_override[current_user.id]
        activa_hoy = True
        record = max(record, actual)
    return RachaOut(racha_actual=actual, racha_record=record, activa_hoy=activa_hoy)


def _require_debug() -> None:
    if not settings.debug:
        raise HTTPException(status_code=404, detail="No disponible")


@router.post("/debug/racha/set", response_model=RachaOut)
def debug_set_racha(
    dias: int,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEMO] Forzar la racha a un valor exacto. Solo con settings.debug."""
    _require_debug()
    _racha_override[current_user.id] = max(0, dias)
    return get_racha(db=db, current_user=current_user)


@router.post("/debug/racha/sumar", response_model=RachaOut)
def debug_sumar_racha(
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """[DEMO] Sumar 1 a la racha (dispara la animación en la app). Solo con settings.debug."""
    _require_debug()
    if current_user.id in _racha_override:
        base = _racha_override[current_user.id]
    else:
        base, _ = _calcular_racha(_dias_con_sesion(db, current_user.id))
    _racha_override[current_user.id] = base + 1
    return get_racha(db=db, current_user=current_user)


@router.delete("/debug/racha", status_code=status.HTTP_204_NO_CONTENT)
def debug_reset_racha(
    current_user: User = Depends(get_current_user),
):
    """[DEMO] Limpiar el override y volver a la racha real. Solo con settings.debug."""
    _require_debug()
    _racha_override.pop(current_user.id, None)