"""Endpoints para leer y actualizar preferencias del usuario logueado."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserPreferences
from ..schemas import PreferencesOut, PreferencesUpdate
from ..security import get_current_user


router = APIRouter(prefix="/preferences", tags=["preferences"])


@router.get("/me", response_model=PreferencesOut)
def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = current_user.preferences
    if prefs is None:
        prefs = UserPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


@router.patch("/me", response_model=PreferencesOut)
def update_my_preferences(
    payload: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    prefs = current_user.preferences or UserPreferences(user_id=current_user.id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    db.add(prefs)
    db.commit()
    db.refresh(prefs)
    return prefs
