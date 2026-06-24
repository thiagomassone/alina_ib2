"""Endpoints de sesiones de uso del dispositivo ALINA."""

from __future__ import annotations
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from ..database import get_db
from ..models import Session as SessionModel, User
from ..schemas import ScoreSummary, SessionCreate, SessionOut
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


@router.post("", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate,
    db: DBSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Registrar una sesión completada.

    Llamado por el ESP32 (vía WebSocket broker o directamente) o por la app
    al cerrar una sesión de monitoreo.
    """
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