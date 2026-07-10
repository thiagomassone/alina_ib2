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
    def register(self, nombre: str, apellido: str, email: str, password: str) -> dict:
        r = httpx.post(
            f"{self.base_url}/auth/register",
            json={"nombre": nombre, "apellido": apellido, "email": email, "password": password},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def login(self, email: str, password: str) -> str:
        # OAuth2PasswordRequestForm espera form-encoded; mandamos email en el campo "username"
        r = httpx.post(
            f"{self.base_url}/auth/login",
            data={"username": email, "password": password},
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

    # ─── Perfil ───
    def get_me(self) -> dict:
        r = httpx.get(f"{self.base_url}/auth/me", headers=self._auth_headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def update_profile(self, **fields) -> dict:
        r = httpx.patch(
            f"{self.base_url}/auth/me",
            json={k: v for k, v in fields.items() if v is not None},
            headers=self._auth_headers(), timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def upload_foto(self, file_bytes: bytes, content_type: str) -> dict:
        r = httpx.post(
            f"{self.base_url}/auth/me/foto",
            files={"file": ("foto", file_bytes, content_type)},
            headers=self._auth_headers(), timeout=30,
        )
        r.raise_for_status()
        return r.json()

    def change_password(self, password_actual: str, password_nuevo: str) -> dict:
        r = httpx.patch(
            f"{self.base_url}/auth/me/change-password",
            json={"password_actual": password_actual, "password_nuevo": password_nuevo},
            headers=self._auth_headers(), timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def get_preferences(self) -> dict:
        r = httpx.get(
            f"{self.base_url}/preferences/me", headers=self._auth_headers(), timeout=10
        )
        r.raise_for_status()
        return r.json()
    
    # ─── Dispositivo ───
    def get_device_status(self) -> dict:
        """Estado actual del dispositivo (nombre, batería, calibración, intensidad)."""
        r = httpx.get(f"{self.base_url}/device", headers=self._auth_headers(), timeout=10)
        r.raise_for_status()
        return r.json()

    def update_device_status(self, **fields) -> dict:
        """Actualizar campos del dispositivo (device_name, haptic_intensity, last_calibration_at, battery_pct)."""
        r = httpx.patch(
            f"{self.base_url}/device",
            json={k: v for k, v in fields.items() if v is not None},
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def save_device_name(self, name: str) -> dict:
        return self.update_device_status(device_name=name)

    def save_calibration_timestamp(self, iso_timestamp: str) -> dict:
        return self.update_device_status(last_calibration_at=iso_timestamp)

    def save_haptic_intensity(self, intensity: int) -> dict:
        return self.update_device_status(haptic_intensity=intensity)

    def update_battery(self, pct: int) -> dict:
        """Llamado cuando el ESP32 manda el nivel de batería."""
        return self.update_device_status(battery_pct=pct)

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
    def create_session(
        self,
        started_at: str,
        duracion_min: float,
        alertas_hapticas: int,
        min_buena: float = 0.0,
        min_mala: float = 0.0,
    ) -> dict:
        """Registrar una sesión completada. Llamar al terminar el monitoreo.

        Args:
            started_at: ISO 8601, ej. "2024-05-10T14:30:00"
            duracion_min: duración real en minutos
            alertas_hapticas: cantidad de veces que vibró para corregir postura
            min_buena: minutos en buena postura
            min_mala: minutos en mala postura
        """
        r = httpx.post(
            f"{self.base_url}/sessions",
            json={
                "started_at": started_at,
                "duracion_min": duracion_min,
                "alertas_hapticas": alertas_hapticas,
                "min_buena": min_buena,
                "min_mala": min_mala,
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

    # ─── Notificaciones ───
    def get_notifications(self, limit: int = 50, solo_no_leidas: bool = False) -> list[dict]:
        r = httpx.get(
            f"{self.base_url}/notifications",
            params={"limit": limit, "solo_no_leidas": solo_no_leidas},
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def get_unread_count(self) -> int:
        r = httpx.get(
            f"{self.base_url}/notifications/unread_count",
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()["count"]

    def mark_notification_read(self, notification_id: int) -> None:
        r = httpx.patch(
            f"{self.base_url}/notifications/{notification_id}/read",
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()

    def mark_all_notifications_read(self) -> None:
        r = httpx.patch(
            f"{self.base_url}/notifications/read_all",
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()