"""Entry point del frontend Flet.

Correr como app de escritorio:
    flet run main.py

Correr como web (mismo código, ideal para PC y móvil vía navegador):
    flet run --web main.py

A futuro, empaquetar como app móvil:
    flet build apk     # Android
    flet build ipa     # iOS
"""

from __future__ import annotations

import flet as ft

from api_client import ApiClient
from views.home_view import home_view
from views.login_view import login_view, register_view


API_BASE_URL = "http://localhost:8000"


def main(page: ft.Page):
    page.title = "ALINA - IB2"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=ft.colors.INDIGO)

    # Cliente API compartido a través de la sesión
    page.api = ApiClient(API_BASE_URL)

    def route_change(_):
        page.views.clear()

        # Ruta inicial / protegida
        if page.route in ("/", "/home"):
            if not page.api.is_authenticated:
                page.go("/login")
                return
            page.views.append(home_view(page))
        elif page.route == "/register":
            page.views.append(register_view(page))
        else:  # /login y cualquier otra
            page.views.append(login_view(page, on_success=lambda: page.go("/")))

        page.update()

    def view_pop(_):
        page.views.pop()
        page.go(page.views[-1].route if page.views else "/login")

    def rebuild_home():
        """Reconstruye la app (para que un cambio de tema repinte todo)."""
        page.views.clear()
        page.views.append(home_view(page))
        page.update()
    page.rebuild_home = rebuild_home

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/login")


if __name__ == "__main__":
    ft.app(target=main)
