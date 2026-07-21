"""Endpoints de registro, login y perfil de usuario."""

import base64

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Notification, User, UserPreferences, crear_notificacion
from ..notif_texts import notif_text, user_lang
from ..schemas import ChangePasswordRequest, Token, UserCreate, UserOut, UserProfileUpdate
from ..security import create_access_token, get_current_user, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    user = User(
        username=payload.email,   # username = email internamente
        email=payload.email,
        hashed_password=hash_password(payload.password),
        nombre=payload.nombre,
        apellido=payload.apellido,
    )
    user.preferences = UserPreferences()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # OAuth2PasswordRequestForm usa el campo "username" del form — acá llega el email
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )
    token = create_access_token({"sub": user.username})  # username == email
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Obtener datos del usuario autenticado."""
    return current_user


@router.patch("/me", response_model=UserOut)
def update_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Actualizar nombre, apellido, edad, sexo y/o email."""
    # Verificar que el nuevo email no esté en uso por otro usuario
    if payload.email and payload.email != current_user.email:
        exists = db.query(User).filter(
            User.email == payload.email,
            User.id != current_user.id,
        ).first()
        if exists:
            raise HTTPException(status_code=400, detail="Email ya registrado por otro usuario")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/foto", response_model=UserOut)
async def upload_foto(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Subir foto de perfil. Se guarda como base64."""
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Solo se aceptan imágenes JPG, PNG o WEBP")
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:  # 2 MB máx
        raise HTTPException(status_code=400, detail="La imagen no puede superar 2 MB")
    current_user.foto_b64 = f"data:{file.content_type};base64,{base64.b64encode(contents).decode()}"
    db.commit()
    db.refresh(current_user)
    return current_user


@router.patch("/me/change-password")
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cambiar contraseña. Requiere la contraseña actual para confirmar."""
    if not verify_password(payload.password_actual, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="La contraseña actual es incorrecta")
    if len(payload.password_nuevo) < 8:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 8 caracteres")
    current_user.hashed_password = hash_password(payload.password_nuevo)
    db.commit()
    # Notificación de seguridad (en el idioma del usuario)
    _ti, _ms = notif_text("password_changed", user_lang(db, current_user.id))
    crear_notificacion(
        db=db,
        user_id=current_user.id,
        tipo="password_changed",
        titulo=_ti,
        mensaje=_ms,
    )
    return {"ok": True}