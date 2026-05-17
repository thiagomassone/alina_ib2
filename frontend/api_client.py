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

    def update_preferences(self, **fields) -> dict:
        r = httpx.patch(
            f"{self.base_url}/preferences/me",
            json=fields,
            headers=self._auth_headers(),
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
