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
    theme: str | None = None
    language: str | None = None
    notifications_enabled: bool | None = None


class PreferencesOut(BaseModel):
    theme: str
    language: str
    notifications_enabled: bool

    model_config = ConfigDict(from_attributes=True)
