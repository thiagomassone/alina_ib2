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
