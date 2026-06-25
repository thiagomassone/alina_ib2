"""Entry point del backend FastAPI.

Correr en desarrollo desde la carpeta backend/:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

Docs interactivas: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .routers import auth, device, preferences, sessions


# Crea las tablas al arrancar (en producción usar Alembic para migraciones).
Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="ALINA - IB2 API",
    description="Backend de la aplicación ALINA: login, preferencias y datos del usuario.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(preferences.router)
app.include_router(device.router)
app.include_router(sessions.router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}