"""Conexión a la base de datos SQLite vía SQLAlchemy."""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


engine = create_engine(
    settings.database_url,
    # check_same_thread sólo es necesario para SQLite
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Clase base para todos los modelos."""


def get_db():
    """Dependencia de FastAPI: abre y cierra una sesión por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
