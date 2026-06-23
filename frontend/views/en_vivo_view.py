"""Tab 1 — En vivo: visualización en tiempo real (placeholder hasta integrar WebSocket/BLE)."""

from __future__ import annotations
import flet as ft
from .components import placeholder_view


def en_vivo_view(page: ft.Page) -> ft.Control:
    return placeholder_view("Postura en vivo", ft.icons.ACCESSIBILITY_NEW)