"""Cliente HTTP que habla con el backend FastAPI.

Mantener todas las llamadas a la API en este módulo para que las vistas
queden limpias y sea fácil mockear en tests.
"""

from __future__ import annotations

import httpx


class ApiClient:
    def __init__(self, base_url: str = "http://localhost:8000") -> None:
        self.base_url = base_url.rstrip("/")
        self._token: str | None = None

    # ─── Auth ───
    def register(self, username: str, email: str, password: str) -> dict:
        r = httpx.post(
            f"{self.base_url}/auth/register",
            json={"username": username, "email": email, "password": password},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def login(self, username: str, password: str) -> str:
        # OAuth2PasswordRequestForm espera form-encoded, no JSON.
        r = httpx.post(
            f"{self.base_url}/auth/login",
            data={"username": username, "password": password},
            timeout=10,
        )
        r.raise_for_status()
        self._token = r.json()["access_token"]
        return self._token

    def logout(self) -> None:
        self._token = None

    @property
    def is_authenticated(self) -> bool:
        return self._token is not None

    def _auth_headers(self) -> dict:
        if not self._token:
            raise RuntimeError("No hay sesión iniciada")
        return {"Authorization": f"Bearer {self._token}"}

    # ─── Preferencias ───
    def get_preferences(self) -> dict:
        r = httpx.get(
            f"{self.base_url}/preferences/me", headers=self._auth_headers(), timeout=10
        )
        r.raise_for_status()
        return r.json()

    def save_device_name(self, name: str) -> dict:
        """Guardar el nombre del dispositivo en la cuenta del usuario."""
        return self.update_preferences(device_name=name)

    def update_preferences(self, **fields) -> dict:
        r = httpx.patch(
            f"{self.base_url}/preferences/me",
            json=fields,
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    # ─── Sesiones ───
    def create_session(self, started_at: str, duracion_min: float, alertas_hapticas: int) -> dict:
        """Registrar una sesión completada. Llamar al terminar el monitoreo.

        Args:
            started_at: ISO 8601, ej. "2024-05-10T14:30:00"
            duracion_min: duración real en minutos
            alertas_hapticas: cantidad de veces que vibró para corregir postura
        """
        r = httpx.post(
            f"{self.base_url}/sessions",
            json={
                "started_at": started_at,
                "duracion_min": duracion_min,
                "alertas_hapticas": alertas_hapticas,
            },
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def get_today_summary(self) -> dict:
        """Resumen de sesiones de hoy (tiempo activo, score del día)."""
        r = httpx.get(
            f"{self.base_url}/sessions/today",
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def get_sessions(self, limit: int = 50) -> list[dict]:
        """Últimas N sesiones del usuario (para el tab Historial)."""
        r = httpx.get(
            f"{self.base_url}/sessions",
            params={"limit": limit},
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def get_score_summary(self) -> dict:
        """Score promedio + última sesión (para el tab Resumen).

        Devuelve:
            score_promedio: float (0–100)
            score_ultima_sesion: float | None
            total_sesiones: int
            total_min_uso: float
        """
        r = httpx.get(
            f"{self.base_url}/sessions/score",
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def delete_session(self, session_id: int) -> None:
        """Borrar una sesión por ID."""
        r = httpx.delete(
            f"{self.base_url}/sessions/{session_id}",
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()