"""Vista principal de ALINA — shell con bottom navigation.

Esta vista es la "concha" (shell) que contiene el AppBar con el logo,
el área de contenido y el bottom navigation. El tab activo se intercambia
dentro del contenedor central; no se cambia de ruta para evitar perder
el estado del `ApiClient`.

Tabs:
    0 - Resumen        (dashboard del día, con tarjeta del dispositivo arriba)
    1 - Postura en vivo (placeholder)
    2 - Historial      (placeholder)
    3 - Análisis       (placeholder)
    4 - Alertas        (placeholder)
    5 - Perfil         (preferencias del usuario, antes era home_view)

Toda la paleta vive en theme.py; este archivo solo arma layouts.
"""

from __future__ import annotations

import flet as ft

import theme as t


# ─────────────────────────────────────────────────────────────────────────────
# Marca ALINA
# ─────────────────────────────────────────────────────────────────────────────

def _alina_logo_mark(size: int = 32) -> ft.Control:
    """Reproduce la marca: triángulo navy + 4 puntos teal descendientes.

    No es un SVG fiel al logo; es una aproximación con primitivas de Flet.
    Sirve hasta que el equipo aporte el SVG/PNG oficial a `assets/`.
    """
    # Tamaños de los 4 puntos, escalados a partir del tamaño total
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
    """Lockup compacto: marca + palabra 'ALINA'. Va en la esquina del header."""
    return ft.Row(
        [
            _alina_logo_mark(mark_size),
            ft.Text(
                "ALINA",
                size=text_size,
                weight=ft.FontWeight.W_700,
                color=t.NAVY,
                # Leve espaciado entre letras para que se sienta como marca
                # (Flet 0.24 no expone letter_spacing en Text; queda implícito)
            ),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def _section_header(title: str, subtitle: str) -> ft.Control:
    """Header de tab: saludo/título a la izquierda + lockup ALINA a la derecha."""
    return ft.Row(
        [
            ft.Column(
                [
                    ft.Text(
                        title,
                        size=22,
                        weight=ft.FontWeight.W_700,
                        color=t.TEXT_DARK,
                    ),
                    ft.Text(subtitle, size=13, color=t.TEXT_MUTED),
                ],
                spacing=2,
                expand=True,
            ),
            _alina_logo_lockup(),
        ],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de UI (tarjetas reutilizables)
# ─────────────────────────────────────────────────────────────────────────────

def _card(content: ft.Control, padding: int = 16) -> ft.Container:
    """Envoltura blanca con esquinas redondeadas y sombra sutil."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Tarjetas del tab Resumen
# ─────────────────────────────────────────────────────────────────────────────

def _device_card() -> ft.Control:
    """Tarjeta del dispositivo ALINA — movida desde el tab Perfil al Resumen.

    Por ahora con datos mockeados; cuando integremos BLE con el ESP32
    estos valores van a venir del estado en memoria de la app, no del backend.
    """
    return _card(
        ft.Row(
            [
                # "Foto" del dispositivo (placeholder hasta tener un PNG real)
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
    """Tarjeta principal con la puntuación postural del día + donut."""
    score = max(0, min(100, score))
    return _card(
        ft.Column(
            [
                ft.Text(
                    "Puntuación postural",
                    size=13,
                    color=t.TEXT_MUTED,
                    weight=ft.FontWeight.W_500,
                ),
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
                        # Donut + texto centrado superpuesto
                        ft.Stack(
                            [
                                ft.PieChart(
                                    sections=[
                                        ft.PieChartSection(score, color=t.TEAL, radius=14),
                                        ft.PieChartSection(
                                            100 - score, color=t.TEAL_SOFT, radius=14
                                        ),
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
                ft.Text(title, size=12, color=t.TEXT_MUTED, weight=ft.FontWeight.W_500),
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
                ft.Text(
                    "Resumen diario",
                    size=13,
                    color=t.TEXT_MUTED,
                    weight=ft.FontWeight.W_500,
                ),
                ft.Container(height=6),
                _legend_row(t.GOOD, "Buena postura", "2h 05m"),
                _legend_row(t.NEUTRAL, "Postura neutra", "30m"),
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
                        ft.Text("Última calibración", size=12, color=t.TEXT_MUTED),
                        ft.Text(
                            "Hoy, 08:15",
                            size=14,
                            weight=ft.FontWeight.W_600,
                            color=t.TEXT_DARK,
                        ),
                        ft.Text("Calibración correcta", size=11, color=t.GOOD),
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


# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────

def _resumen_tab(page: ft.Page) -> ft.Control:
    """Tab 0 — Dashboard del día."""
    # El saludo personalizado idealmente saldría de page.api.get_me(); por ahora
    # lo dejamos genérico para que la entrega no dependa de ese endpoint.
    username = getattr(page, "username", None) or "Alex"
    return ft.Column(
        [
            _section_header(f"Hola, {username}", "Resumen de hoy"),
            ft.Container(height=10),
            _device_card(),
            _score_card(score=82),
            ft.Row(
                [
                    ft.Container(
                        content=_metric_card("Tiempo hoy", "2h 35m", "activos"),
                        expand=True,
                    ),
                    ft.Container(
                        content=_metric_card("Alertas", "8", "hoy"),
                        expand=True,
                    ),
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


def _placeholder_tab(label: str, icon) -> ft.Control:
    """Pantallas que todavía no construimos — placeholder visual coherente."""
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


def _perfil_tab(page: ft.Page) -> ft.Control:
    """Tab 5 — Perfil / Configuración (lo que antes era home_view)."""
    prefs = page.api.get_preferences()

    theme_dd = ft.Dropdown(
        label="Tema",
        value=prefs["theme"],
        options=[
            ft.dropdown.Option("light", "Claro"),
            ft.dropdown.Option("dark", "Oscuro"),
        ],
    )
    lang_dd = ft.Dropdown(
        label="Idioma",
        value=prefs["language"],
        options=[
            ft.dropdown.Option("es", "Español"),
            ft.dropdown.Option("en", "English"),
            ft.dropdown.Option("pt", "Português"),
        ],
    )
    notif_sw = ft.Switch(
        label="Notificaciones",
        value=prefs["notifications_enabled"],
        active_color=t.TEAL,
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
            _section_header("Perfil", "Configuración de la cuenta y de la experiencia"),
            ft.Container(height=10),
            _card(
                ft.Column(
                    [
                        ft.Text(
                            "Preferencias",
                            size=13,
                            color=t.TEXT_MUTED,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Container(height=6),
                        theme_dd,
                        lang_dd,
                        notif_sw,
                        ft.Container(height=4),
                        ft.FilledButton(
                            "Guardar",
                            on_click=save,
                            style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD),
                        ),
                        status,
                    ],
                    spacing=10,
                )
            ),
            _card(
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text("Sesión", size=13, color=t.TEXT_MUTED),
                                ft.Text(
                                    "Salir de la cuenta",
                                    size=14,
                                    color=t.TEXT_DARK,
                                    weight=ft.FontWeight.W_500,
                                ),
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
# Shell / entry point
# ─────────────────────────────────────────────────────────────────────────────

def home_view(page: ft.Page) -> ft.View:
    """Vista raíz autenticada — shell con bottom navigation.

    Mantenemos UNA sola ruta '/' y cambiamos el contenido del Container
    central según el tab elegido. Esto preserva el estado del cliente
    (token, etc.) sin tener que rehidratar en cada navegación.
    """
    page.bgcolor = t.BG

    # Container central donde se monta el tab activo.
    # Padding superior ~20 para reemplazar la separación visual que daba el AppBar.
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
            content.content = _placeholder_tab("Historial", ft.icons.HISTORY)
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

    # Nota: NO seteamos `appbar` a propósito. El logo ALINA vive ahora en
    # el header de cada tab (helper _section_header), junto al título. Eso
    # libera espacio vertical para las tarjetas del Resumen.
    return ft.View(
        route="/",
        bgcolor=t.BG,
        padding=0,
        navigation_bar=nav,
        controls=[content],
    )
