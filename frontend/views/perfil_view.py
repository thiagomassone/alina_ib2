"""Tab 5 — Perfil: info usuario, objetivos, preferencias, dispositivo."""

from __future__ import annotations
import flet as ft
import theme as t
from .components import card, card_label, dot, pill, divider


def _info_row(label: str, value: str) -> ft.Control:
    return ft.Row(
        [
            ft.Text(label, size=13, color=t.TEXT_MUTED, expand=True),
            ft.Text(value, size=13, color=t.TEXT_DARK, weight=ft.FontWeight.W_500),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def perfil_view(page: ft.Page) -> ft.Control:
    prefs = page.api.get_preferences()

    theme_dd = ft.Dropdown(
        label="Tema",
        value=prefs["theme"],
        options=[ft.dropdown.Option("light", "Claro"), ft.dropdown.Option("dark", "Oscuro")],
        border_color=t.DIVIDER, focused_border_color=t.TEAL,
    )
    lang_dd = ft.Dropdown(
        label="Idioma",
        value=prefs["language"],
        options=[
            ft.dropdown.Option("es", "Español"),
            ft.dropdown.Option("en", "English"),
            ft.dropdown.Option("pt", "Português"),
        ],
        border_color=t.DIVIDER, focused_border_color=t.TEAL,
    )
    notif_sw = ft.Switch(label="Notificaciones", value=prefs["notifications_enabled"], active_color=t.TEAL)
    haptic_slider = ft.Slider(min=0, max=100, value=60, active_color=t.TEAL, inactive_color=t.TEAL_SOFT, expand=True)
    status = ft.Text("", color=t.GOOD, size=12)

    def save(_):
        try:
            page.api.update_preferences(theme=theme_dd.value, language=lang_dd.value, notifications_enabled=notif_sw.value)
            page.theme_mode = ft.ThemeMode.DARK if theme_dd.value == "dark" else ft.ThemeMode.LIGHT
            status.value = "Preferencias guardadas"
            status.color = t.GOOD
            page.update()
        except Exception as e:
            status.value = f"Error: {e}"
            status.color = t.BAD
            page.update()

    def logout(_):
        page.api.logout()
        page.go("/login")

    return ft.Column(
        [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("Perfil", size=22, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                            ft.Text("Tu cuenta", size=13, color=t.TEXT_MUTED),
                        ],
                        spacing=2, expand=True,
                    ),
                    ft.Container(content=ft.Icon(ft.icons.SETTINGS_OUTLINED, color=t.TEXT_MUTED, size=22), padding=4),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=10),
            card(
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Icon(ft.icons.PERSON, color=t.CARD, size=26),
                            width=52, height=52, bgcolor=t.TEAL, border_radius=26, alignment=ft.alignment.center,
                        ),
                        ft.Column(
                            [
                                ft.Text("Alex Martínez", size=15, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                ft.Text("alex@email.com", size=12, color=t.TEXT_MUTED),
                                ft.Container(height=4),
                                pill("Nivel 4", t.TEAL),
                            ],
                            spacing=2, expand=True,
                        ),
                        ft.Icon(ft.icons.CHEVRON_RIGHT, color=t.TEXT_LIGHT, size=20),
                    ],
                    spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=14,
            ),
            card(
                ft.Column(
                    [
                        card_label("Objetivos"),
                        ft.Container(height=8),
                        _info_row("Puntuación objetivo", "90/100"),
                        ft.Container(height=6),
                        divider(),
                        ft.Container(height=6),
                        _info_row("Tiempo de objetivo por día", "3h 00m"),
                    ],
                    spacing=0,
                )
            ),
            card(
                ft.Column(
                    [
                        card_label("Preferencias"),
                        ft.Container(height=8),
                        _info_row("Sensibilidad", "Media"),
                        ft.Container(height=10),
                        divider(),
                        ft.Container(height=10),
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Icon(ft.icons.VOLUME_DOWN_OUTLINED, size=16, color=t.TEXT_MUTED),
                                        haptic_slider,
                                        ft.Icon(ft.icons.VOLUME_UP_OUTLINED, size=16, color=t.TEXT_MUTED),
                                    ],
                                    spacing=8,
                                ),
                                ft.Text("Intensidad háptica", size=11, color=t.TEXT_MUTED),
                            ],
                            spacing=2,
                        ),
                        ft.Container(height=6),
                        divider(),
                        ft.Container(height=6),
                        ft.Row(
                            [ft.Text("Notificaciones", size=13, color=t.TEXT_DARK, expand=True), notif_sw],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=6),
                        divider(),
                        ft.Container(height=6),
                        theme_dd,
                        lang_dd,
                        ft.Container(height=4),
                        ft.FilledButton("Guardar preferencias", on_click=save, style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD)),
                        status,
                    ],
                    spacing=0,
                )
            ),
            card(
                ft.Column(
                    [
                        card_label("Dispositivo"),
                        ft.Container(height=8),
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Icon(ft.icons.SENSORS, color=t.NAVY, size=24),
                                    width=44, height=44, bgcolor="#EEF2F7", border_radius=10, alignment=ft.alignment.center,
                                ),
                                ft.Column(
                                    [
                                        ft.Text("ALINA Dispositivo", size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
                                        ft.Row([dot(t.GOOD, 8), ft.Text("Conectado", size=12, color=t.TEXT_MUTED)], spacing=6),
                                    ],
                                    spacing=3, expand=True,
                                ),
                                ft.Row(
                                    [ft.Icon(ft.icons.BATTERY_FULL, color=t.GOOD, size=16), ft.Text("92%", size=13, weight=ft.FontWeight.W_700, color=t.TEXT_DARK)],
                                    spacing=4,
                                ),
                                ft.Icon(ft.icons.CHEVRON_RIGHT, color=t.TEXT_LIGHT, size=18),
                            ],
                            spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=0,
                )
            ),
            card(
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Sesión", size=13, color=t.TEXT_MUTED),
                                ft.Text("Salir de la cuenta", size=14, color=t.TEXT_DARK, weight=ft.FontWeight.W_500),
                            ],
                            spacing=2, expand=True,
                        ),
                        ft.OutlinedButton("Salir", icon=ft.icons.LOGOUT, on_click=logout, style=ft.ButtonStyle(color=t.NAVY)),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            ),
            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )