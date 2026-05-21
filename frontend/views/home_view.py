"""Vista principal: muestra y permite editar las preferencias del usuario."""

from __future__ import annotations

import flet as ft


def home_view(page: ft.Page) -> ft.View:
    prefs = page.api.get_preferences()

    theme_dd = ft.Dropdown(
        label="Tema",
        value=prefs["theme"],
        options=[ft.dropdown.Option("light", "Claro"), ft.dropdown.Option("dark", "Oscuro")],
        width=320,
    )
    lang_dd = ft.Dropdown(
        label="Idioma",
        value=prefs["language"],
        options=[
            ft.dropdown.Option("es", "Español"),
            ft.dropdown.Option("en", "English"),
            ft.dropdown.Option("pt", "Português"),
        ],
        width=320,
    )
    notif_sw = ft.Switch(label="Notificaciones", value=prefs["notifications_enabled"])
    status = ft.Text("", color=ft.colors.GREEN_600)

    def save(_):
        try:
            page.api.update_preferences(
                theme=theme_dd.value,
                language=lang_dd.value,
                notifications_enabled=notif_sw.value,
            )
            # Aplicar el tema al instante
            page.theme_mode = ft.ThemeMode.DARK if theme_dd.value == "dark" else ft.ThemeMode.LIGHT
            status.value = "Preferencias guardadas"
            page.update()
        except Exception as e:
            status.value = f"Error: {e}"
            status.color = ft.colors.RED_400
            page.update()

    def logout(_):
        page.api.logout()
        page.go("/login")

    return ft.View(
        route="/",
        appbar=ft.AppBar(
            title=ft.Text("ALINA - IB2"),
            actions=[ft.IconButton(icon=ft.icons.LOGOUT, tooltip="Salir", on_click=logout)],
        ),
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Tus preferencias", size=22, weight=ft.FontWeight.BOLD),
                        ft.Container(height=10),
                        theme_dd,
                        lang_dd,
                        notif_sw,
                        ft.FilledButton("Guardar", on_click=save, width=320),
                        status,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=12,
                ),
                alignment=ft.alignment.center,
                expand=True,
                padding=40,
            )
        ],
    )
