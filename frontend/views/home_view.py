"""Vista principal de ALINA — shell con bottom navigation.

Tabs:
    0 - Resumen        (dashboard del día)
    1 - En vivo        (placeholder — requiere BLE/WebSocket)
    2 - Historial      (gráfico semanal + sesiones recientes)
    3 - Análisis       (placeholder)
    4 - Alertas        (placeholder)
    5 - Perfil         (info usuario, objetivos, preferencias, dispositivo)
"""

from __future__ import annotations

import flet as ft

import theme as t


# ─────────────────────────────────────────────────────────────────────────────
# Marca ALINA
# ─────────────────────────────────────────────────────────────────────────────

def _alina_logo_mark(size: int = 32) -> ft.Control:
    dot_sizes = [size * 0.28, size * 0.22, size * 0.19, size * 0.16]
    dots = ft.Column(
        [
            ft.Container(width=s, height=s, bgcolor=t.TEAL, border_radius=s)
            for s in dot_sizes
        ],
        spacing=max(1, int(size * 0.06)),
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
    )
    return ft.Stack(
        [
            ft.Icon(ft.icons.CHANGE_HISTORY, size=size, color=t.NAVY),
            ft.Container(
                content=dots,
                alignment=ft.alignment.center,
                width=size,
                height=size,
                padding=ft.padding.only(top=size * 0.25),
            ),
        ],
        width=size,
        height=size,
    )


def _alina_logo_lockup(mark_size: int = 22, text_size: int = 14) -> ft.Control:
    return ft.Row(
        [
            _alina_logo_mark(mark_size),
            ft.Text(
                "ALINA",
                size=text_size,
                weight=ft.FontWeight.W_700,
                color=t.NAVY,
            ),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _section_header(title: str, subtitle: str, action: ft.Control | None = None) -> ft.Control:
    right = action if action is not None else _alina_logo_lockup()
    return ft.Row(
        [
            ft.Column(
                [
                    ft.Text(title, size=22, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                    ft.Text(subtitle, size=13, color=t.TEXT_MUTED),
                ],
                spacing=2,
                expand=True,
            ),
            right,
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de UI reutilizables
# ─────────────────────────────────────────────────────────────────────────────

def _card(content: ft.Control, padding: int = 16) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=t.CARD,
        border_radius=14,
        padding=padding,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=8,
            color=t.SHADOW,
            offset=ft.Offset(0, 2),
        ),
    )


def _dot(color: str, size: int = 10) -> ft.Control:
    return ft.Container(width=size, height=size, bgcolor=color, border_radius=size)


def _pill(text: str, bgcolor: str, fgcolor: str = "#FFFFFF") -> ft.Control:
    return ft.Container(
        content=ft.Text(text, color=fgcolor, size=12, weight=ft.FontWeight.W_600),
        bgcolor=bgcolor,
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
    )


def _card_label(text: str) -> ft.Text:
    """Label de sección dentro de una tarjeta — negrita según el mockup."""
    return ft.Text(text, size=13, color=t.TEXT_DARK, weight=ft.FontWeight.W_700)


def _divider() -> ft.Container:
    return ft.Container(height=1, bgcolor=t.DIVIDER)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 0 — Resumen
# ─────────────────────────────────────────────────────────────────────────────

def _device_card() -> ft.Control:
    return _card(
        ft.Row(
            [
                ft.Container(
                    content=ft.Icon(ft.icons.SENSORS, color=t.NAVY, size=28),
                    width=52,
                    height=52,
                    bgcolor="#EEF2F7",
                    border_radius=12,
                    alignment=ft.alignment.center,
                ),
                ft.Column(
                    [
                        ft.Text(
                            "ALINA Dispositivo",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=t.TEXT_DARK,
                        ),
                        ft.Row(
                            [_dot(t.GOOD, 8), ft.Text("Conectado", size=12, color=t.TEXT_MUTED)],
                            spacing=6,
                        ),
                    ],
                    spacing=4,
                    expand=True,
                ),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.icons.BATTERY_FULL, color=t.GOOD, size=18),
                                ft.Text("92%", size=14, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                            ],
                            spacing=4,
                            alignment=ft.MainAxisAlignment.END,
                        ),
                        ft.Text("Batería", size=10, color=t.TEXT_MUTED),
                    ],
                    spacing=2,
                    horizontal_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            spacing=14,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
    )


def _score_card(score: int = 82) -> ft.Control:
    score = max(0, min(100, score))
    return _card(
        ft.Column(
            [
                _card_label("Puntuación postural"),
                ft.Container(height=4),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            str(score),
                                            size=44,
                                            weight=ft.FontWeight.W_700,
                                            color=t.TEXT_DARK,
                                        ),
                                        ft.Container(
                                            content=ft.Text("/100", size=15, color=t.TEXT_MUTED),
                                            padding=ft.padding.only(bottom=8),
                                        ),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.END,
                                    spacing=4,
                                ),
                                _pill("Buena", t.TEAL),
                            ],
                            spacing=10,
                            expand=True,
                        ),
                        ft.Stack(
                            [
                                ft.PieChart(
                                    sections=[
                                        ft.PieChartSection(score, color=t.TEAL, radius=14),
                                        ft.PieChartSection(100 - score, color=t.TEAL_SOFT, radius=14),
                                    ],
                                    sections_space=0,
                                    center_space_radius=38,
                                    width=110,
                                    height=110,
                                ),
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text(
                                                f"{score}%",
                                                size=18,
                                                weight=ft.FontWeight.W_700,
                                                color=t.NAVY,
                                            ),
                                            ft.Text(
                                                "Buena postura",
                                                size=9,
                                                color=t.TEXT_MUTED,
                                                text_align=ft.TextAlign.CENTER,
                                            ),
                                        ],
                                        spacing=0,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        alignment=ft.MainAxisAlignment.CENTER,
                                    ),
                                    width=110,
                                    height=110,
                                    alignment=ft.alignment.center,
                                ),
                            ],
                            width=110,
                            height=110,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
        )
    )


def _metric_card(title: str, value: str, subtitle: str) -> ft.Control:
    return _card(
        ft.Column(
            [
                _card_label(title),
                ft.Container(height=2),
                ft.Text(value, size=24, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                ft.Text(subtitle, size=11, color=t.TEXT_LIGHT),
            ],
            spacing=2,
        ),
        padding=14,
    )


def _legend_row(color: str, label: str, value: str) -> ft.Control:
    return ft.Row(
        [
            ft.Row([_dot(color), ft.Text(label, size=13, color=t.TEXT_DARK)], spacing=8),
            ft.Text(value, size=13, color=t.TEXT_MUTED, weight=ft.FontWeight.W_500),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def _daily_summary_card() -> ft.Control:
    return _card(
        ft.Column(
            [
                _card_label("Resumen diario"),
                ft.Container(height=6),
                _legend_row(t.GOOD, "Buena postura", "2h 05m"),
                _legend_row(t.NEUTRAL, "Postura activa", "30m"),
                _legend_row(t.BAD, "Mala postura", "20m"),
            ],
            spacing=10,
        )
    )


def _calibration_card() -> ft.Control:
    return _card(
        ft.Row(
            [
                ft.Column(
                    [
                        _card_label("Última calibración"),
                        ft.Text(
                            "Hoy, 08:15",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=t.TEXT_DARK,
                        ),
                        ft.Row(
                            [
                                ft.Icon(ft.icons.REFRESH, size=12, color=t.TEAL),
                                ft.Text("Calibración conectada", size=11, color=t.TEAL),
                            ],
                            spacing=4,
                        ),
                    ],
                    spacing=2,
                    expand=True,
                ),
                ft.Container(
                    content=ft.Icon(ft.icons.CHECK, color=t.CARD, size=16),
                    bgcolor=t.GOOD,
                    border_radius=14,
                    width=28,
                    height=28,
                    alignment=ft.alignment.center,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
    )


def _resumen_tab(page: ft.Page) -> ft.Control:
    username = getattr(page, "username", None) or "Alex"
    return ft.Column(
        [
            _section_header(f"Hola, {username}", "Resumen de hoy"),
            ft.Container(height=10),
            _device_card(),
            _score_card(score=82),
            ft.Row(
                [
                    ft.Container(content=_metric_card("Tiempo hoy", "2h 35m", "activos"), expand=True),
                    ft.Container(content=_metric_card("Alertas", "8", "hoy"), expand=True),
                ],
                spacing=12,
            ),
            _daily_summary_card(),
            _calibration_card(),
            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — Historial
# ─────────────────────────────────────────────────────────────────────────────

# Datos mockeados — se reemplazarán con datos reales del backend
_WEEKLY_DATA = [
    ("Lun", 72), ("Mar", 68), ("Mié", 75), ("Jue", 80), ("Sáb", 78), ("Dom", 82),
]

_RECENT_SESSIONS = [
    {"fecha": "Hoy, 14:30",   "duracion": "45 min", "score": 83},
    {"fecha": "Hoy, 08:15",   "duracion": "60 min", "score": 76},
    {"fecha": "Ayer, 18:20",  "duracion": "35 min", "score": 74},
]


def _score_badge(score: int) -> ft.Control:
    """Badge colorizado con el score de la sesión."""
    if score >= 80:
        color = t.GOOD
    elif score >= 65:
        color = t.NEUTRAL
    else:
        color = t.BAD
    return ft.Container(
        content=ft.Text(str(score), size=13, weight=ft.FontWeight.W_700, color=t.CARD),
        bgcolor=color,
        border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        width=38,
        alignment=ft.alignment.center,
    )


def _session_row(session: dict, last: bool = False) -> ft.Control:
    return ft.Column(
        [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(session["fecha"], size=13, weight=ft.FontWeight.W_500, color=t.TEXT_DARK),
                            ft.Text(session["duracion"], size=12, color=t.TEXT_MUTED),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    _score_badge(session["score"]),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ]
        + ([] if last else [ft.Container(height=2), _divider(), ft.Container(height=2)]),
        spacing=0,
    )


def _mini_bar_chart(data: list[tuple[str, int]]) -> ft.Control:
    """Gráfico de barras simple para el historial semanal."""
    max_val = max(v for _, v in data) if data else 100
    chart_height = 90

    bars = []
    for label, val in data:
        bar_h = int((val / max_val) * chart_height)
        bars.append(
            ft.Column(
                [
                    ft.Text(str(val), size=9, color=t.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                    ft.Container(
                        content=ft.Container(
                            bgcolor=t.TEAL,
                            border_radius=ft.border_radius.only(top_left=4, top_right=4),
                            height=bar_h,
                            width=28,
                        ),
                        height=chart_height,
                        alignment=ft.alignment.bottom_center,
                    ),
                    ft.Text(label, size=10, color=t.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            )
        )

    return ft.Row(
        bars,
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        vertical_alignment=ft.CrossAxisAlignment.END,
    )


def _period_chip(label: str, selected: bool) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            label,
            size=13,
            weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
            color=t.CARD if selected else t.TEXT_MUTED,
        ),
        bgcolor=t.TEAL if selected else t.CARD,
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=16, vertical=6),
        border=ft.border.all(1, t.TEAL if selected else t.DIVIDER),
    )


def _historial_tab(page: ft.Page) -> ft.Control:
    return ft.Column(
        [
            _section_header("Historial", "Seguimiento de tus sesiones"),
            ft.Container(height=10),

            # Selector de período
            _card(
                ft.Column(
                    [
                        ft.Row(
                            [
                                _period_chip("Semana", True),
                                _period_chip("Mes", False),
                                _period_chip("3 meses", False),
                                _period_chip("Año", False),
                            ],
                            spacing=8,
                        ),
                        ft.Container(height=10),

                        # Navegador de semana
                        ft.Row(
                            [
                                ft.Icon(ft.icons.CHEVRON_LEFT, color=t.TEXT_MUTED, size=20),
                                ft.Row(
                                    [
                                        ft.Icon(ft.icons.CALENDAR_TODAY_OUTLINED, size=14, color=t.TEXT_MUTED),
                                        ft.Text("6 – 12 mayo 2024", size=13, color=t.TEXT_DARK, weight=ft.FontWeight.W_500),
                                    ],
                                    spacing=6,
                                ),
                                ft.Icon(ft.icons.CHEVRON_RIGHT, color=t.TEXT_MUTED, size=20),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Container(height=12),

                        # Score semanal + delta
                        _card_label("Puntuación postural"),
                        ft.Container(height=4),
                        ft.Row(
                            [
                                ft.Row(
                                    [
                                        ft.Text("78", size=36, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                        ft.Container(
                                            content=ft.Text("/100", size=14, color=t.TEXT_MUTED),
                                            padding=ft.padding.only(bottom=6),
                                        ),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.END,
                                    spacing=4,
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Icon(ft.icons.ARROW_UPWARD, size=12, color=t.GOOD),
                                            ft.Text("4% vs. semana anterior", size=11, color=t.GOOD, weight=ft.FontWeight.W_500),
                                        ],
                                        spacing=2,
                                    ),
                                    bgcolor="#E6F9F8",
                                    border_radius=10,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                ),
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=12),

                        # Gráfico de barras semanal
                        _mini_bar_chart(_WEEKLY_DATA),
                    ],
                    spacing=0,
                )
            ),

            # Sesiones recientes
            _card(
                ft.Column(
                    [
                        _card_label("Sesiones recientes"),
                        ft.Container(height=8),
                    ]
                    + [
                        _session_row(s, last=(i == len(_RECENT_SESSIONS) - 1))
                        for i, s in enumerate(_RECENT_SESSIONS)
                    ],
                    spacing=0,
                )
            ),

            # Botón ver todas
            ft.Container(
                content=ft.Text(
                    "Ver todas las sesiones",
                    size=13,
                    color=t.TEAL,
                    weight=ft.FontWeight.W_600,
                    text_align=ft.TextAlign.CENTER,
                ),
                alignment=ft.alignment.center,
                padding=ft.padding.symmetric(vertical=4),
            ),

            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 5 — Perfil
# ─────────────────────────────────────────────────────────────────────────────

def _info_row(label: str, value: str, trailing: ft.Control | None = None) -> ft.Control:
    row_controls = [
        ft.Text(label, size=13, color=t.TEXT_MUTED, expand=True),
        ft.Text(value, size=13, color=t.TEXT_DARK, weight=ft.FontWeight.W_500),
    ]
    if trailing:
        row_controls.append(trailing)
    return ft.Row(row_controls, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def _perfil_tab(page: ft.Page) -> ft.Control:
    prefs = page.api.get_preferences()

    theme_dd = ft.Dropdown(
        label="Tema",
        value=prefs["theme"],
        options=[
            ft.dropdown.Option("light", "Claro"),
            ft.dropdown.Option("dark", "Oscuro"),
        ],
        border_color=t.DIVIDER,
        focused_border_color=t.TEAL,
    )
    lang_dd = ft.Dropdown(
        label="Idioma",
        value=prefs["language"],
        options=[
            ft.dropdown.Option("es", "Español"),
            ft.dropdown.Option("en", "English"),
            ft.dropdown.Option("pt", "Português"),
        ],
        border_color=t.DIVIDER,
        focused_border_color=t.TEAL,
    )
    notif_sw = ft.Switch(
        label="Notificaciones",
        value=prefs["notifications_enabled"],
        active_color=t.TEAL,
    )

    # Slider de intensidad háptica (mockeado por ahora)
    haptic_slider = ft.Slider(
        min=0,
        max=100,
        value=60,
        active_color=t.TEAL,
        inactive_color=t.TEAL_SOFT,
        expand=True,
    )

    status = ft.Text("", color=t.GOOD, size=12)

    def save(_):
        try:
            page.api.update_preferences(
                theme=theme_dd.value,
                language=lang_dd.value,
                notifications_enabled=notif_sw.value,
            )
            page.theme_mode = (
                ft.ThemeMode.DARK if theme_dd.value == "dark" else ft.ThemeMode.LIGHT
            )
            status.value = "Preferencias guardadas"
            status.color = t.GOOD
            page.update()
        except Exception as e:  # noqa: BLE001
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
                        spacing=2,
                        expand=True,
                    ),
                    ft.Container(
                        content=ft.Icon(ft.icons.SETTINGS_OUTLINED, color=t.TEXT_MUTED, size=22),
                        padding=4,
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            ft.Container(height=10),

            # Tarjeta de usuario
            _card(
                ft.Row(
                    [
                        # Avatar
                        ft.Container(
                            content=ft.Icon(ft.icons.PERSON, color=t.CARD, size=26),
                            width=52,
                            height=52,
                            bgcolor=t.TEAL,
                            border_radius=26,
                            alignment=ft.alignment.center,
                        ),
                        ft.Column(
                            [
                                ft.Text("Alex Martínez", size=15, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                ft.Text("alex@email.com", size=12, color=t.TEXT_MUTED),
                                ft.Container(height=4),
                                _pill("Nivel 4", t.TEAL),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.Icon(ft.icons.CHEVRON_RIGHT, color=t.TEXT_LIGHT, size=20),
                    ],
                    spacing=14,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=14,
            ),

            # Objetivos
            _card(
                ft.Column(
                    [
                        _card_label("Objetivos"),
                        ft.Container(height=8),
                        _info_row("Puntuación objetivo", "90/100"),
                        ft.Container(height=6),
                        _divider(),
                        ft.Container(height=6),
                        _info_row("Tiempo de objetivo por día", "3h 00m"),
                    ],
                    spacing=0,
                )
            ),

            # Preferencias
            _card(
                ft.Column(
                    [
                        _card_label("Preferencias"),
                        ft.Container(height=8),
                        _info_row("Sensibilidad", "Media"),
                        ft.Container(height=10),
                        _divider(),
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
                        _divider(),
                        ft.Container(height=6),
                        ft.Row(
                            [
                                ft.Text("Notificaciones", size=13, color=t.TEXT_DARK, expand=True),
                                notif_sw,
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=6),
                        _divider(),
                        ft.Container(height=6),
                        theme_dd,
                        lang_dd,
                        ft.Container(height=4),
                        ft.FilledButton(
                            "Guardar preferencias",
                            on_click=save,
                            style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD),
                        ),
                        status,
                    ],
                    spacing=0,
                )
            ),

            # Dispositivo
            _card(
                ft.Column(
                    [
                        _card_label("Dispositivo"),
                        ft.Container(height=8),
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Icon(ft.icons.SENSORS, color=t.NAVY, size=24),
                                    width=44,
                                    height=44,
                                    bgcolor="#EEF2F7",
                                    border_radius=10,
                                    alignment=ft.alignment.center,
                                ),
                                ft.Column(
                                    [
                                        ft.Text("ALINA Dispositivo", size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
                                        ft.Row(
                                            [_dot(t.GOOD, 8), ft.Text("Conectado", size=12, color=t.TEXT_MUTED)],
                                            spacing=6,
                                        ),
                                    ],
                                    spacing=3,
                                    expand=True,
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(ft.icons.BATTERY_FULL, color=t.GOOD, size=16),
                                        ft.Text("92%", size=13, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                    ],
                                    spacing=4,
                                ),
                                ft.Icon(ft.icons.CHEVRON_RIGHT, color=t.TEXT_LIGHT, size=18),
                            ],
                            spacing=12,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    ],
                    spacing=0,
                )
            ),

            # Cerrar sesión
            _card(
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Sesión", size=13, color=t.TEXT_MUTED),
                                ft.Text("Salir de la cuenta", size=14, color=t.TEXT_DARK, weight=ft.FontWeight.W_500),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        ft.OutlinedButton(
                            "Salir",
                            icon=ft.icons.LOGOUT,
                            on_click=logout,
                            style=ft.ButtonStyle(color=t.NAVY),
                        ),
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


# ─────────────────────────────────────────────────────────────────────────────
# Placeholder para tabs sin implementar
# ─────────────────────────────────────────────────────────────────────────────

def _placeholder_tab(label: str, icon) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(icon, color=t.TEAL_SOFT, size=72),
                ft.Container(height=8),
                ft.Text(label, size=18, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
                ft.Text("Próximamente", size=13, color=t.TEXT_MUTED),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        expand=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shell / entry point
# ─────────────────────────────────────────────────────────────────────────────

def home_view(page: ft.Page) -> ft.View:
    page.bgcolor = t.BG

    content = ft.Container(
        content=_resumen_tab(page),
        padding=ft.padding.only(left=16, right=16, top=20, bottom=0),
        expand=True,
    )

    def on_nav_change(e: ft.ControlEvent):
        idx = e.control.selected_index
        if idx == 0:
            content.content = _resumen_tab(page)
        elif idx == 1:
            content.content = _placeholder_tab("Postura en vivo", ft.icons.ACCESSIBILITY_NEW)
        elif idx == 2:
            content.content = _historial_tab(page)
        elif idx == 3:
            content.content = _placeholder_tab("Análisis", ft.icons.INSIGHTS)
        elif idx == 4:
            content.content = _placeholder_tab("Alertas", ft.icons.NOTIFICATIONS_NONE)
        elif idx == 5:
            content.content = _perfil_tab(page)
        page.update()

    nav = ft.NavigationBar(
        selected_index=0,
        bgcolor=t.CARD,
        indicator_color=t.TEAL_SOFT,
        on_change=on_nav_change,
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.icons.HOME_OUTLINED,
                selected_icon=ft.icons.HOME,
                label="Resumen",
            ),
            ft.NavigationBarDestination(
                icon=ft.icons.ACCESSIBILITY_NEW_OUTLINED,
                selected_icon=ft.icons.ACCESSIBILITY_NEW,
                label="En vivo",
            ),
            ft.NavigationBarDestination(icon=ft.icons.HISTORY, label="Historial"),
            ft.NavigationBarDestination(
                icon=ft.icons.INSIGHTS_OUTLINED,
                selected_icon=ft.icons.INSIGHTS,
                label="Análisis",
            ),
            ft.NavigationBarDestination(
                icon=ft.icons.NOTIFICATIONS_NONE,
                selected_icon=ft.icons.NOTIFICATIONS,
                label="Alertas",
            ),
            ft.NavigationBarDestination(
                icon=ft.icons.PERSON_OUTLINE,
                selected_icon=ft.icons.PERSON,
                label="Perfil",
            ),
        ],
    )

    return ft.View(
        route="/",
        bgcolor=t.BG,
        padding=0,
        navigation_bar=nav,
        controls=[content],
    )