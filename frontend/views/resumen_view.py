"""Tab 0 — Resumen: dashboard del día."""

from __future__ import annotations
import flet as ft
import theme as t
from .components import card, card_label, dot, pill, divider, section_header


# ─── Panel de dispositivo (BottomSheet) ──────────────────────────────────────

def _build_device_sheet(page: ft.Page, device_name_text: ft.Text, card_name_text: ft.Text) -> ft.BottomSheet:
    """
    device_name_text : ft.Text del encabezado del sheet (modo display)
    card_name_text   : ft.Text de la tarjeta del Resumen — se actualiza al guardar
    """

    # ── Nombre inline ─────────────────────────────────────────────────────────
    name_field = ft.TextField(
        value=device_name_text.value,
        border_color=t.TEAL,
        focused_border_color=t.TEAL,
        text_style=ft.TextStyle(color=t.TEXT_DARK, size=16, weight=ft.FontWeight.W_700),
        content_padding=ft.padding.symmetric(horizontal=8, vertical=4),
        border_radius=6,
        visible=False,
        expand=True,
        on_submit=None,
    )
    edit_btn = ft.IconButton(
        icon=ft.icons.EDIT_OUTLINED,
        icon_color=t.TEXT_MUTED,
        icon_size=16,
        tooltip="Editar nombre",
        style=ft.ButtonStyle(padding=4),
    )
    confirm_btn = ft.IconButton(
        icon=ft.icons.CHECK_CIRCLE,
        icon_color=t.TEAL,
        icon_size=18,
        tooltip="Guardar",
        visible=False,
        style=ft.ButtonStyle(padding=4),
    )

    def start_edit(_):
        name_field.value = device_name_text.value
        device_name_text.visible = False
        name_field.visible = True
        edit_btn.visible = False
        confirm_btn.visible = True
        page.update()

    def finish_edit(_=None):
        new_name = (name_field.value or "").strip() or device_name_text.value
        # Actualizar display en el sheet
        device_name_text.value = new_name
        device_name_text.visible = True
        name_field.visible = False
        edit_btn.visible = True
        confirm_btn.visible = False
        # Actualizar tarjeta en el Resumen
        card_name_text.value = new_name
        # Persistir en page y en el backend
        page.device_name = new_name  # type: ignore[attr-defined]
        try:
            page.api.save_device_name(new_name)
        except Exception:
            pass  # Si el backend no está disponible, queda en memoria
        page.update()

    edit_btn.on_click = start_edit
    confirm_btn.on_click = finish_edit
    name_field.on_submit = finish_edit

    # ── Slider de vibración ───────────────────────────────────────────────────
    haptic_slider = ft.Slider(
        min=0, max=100, value=60,
        active_color=t.TEAL,
        inactive_color=t.TEAL_SOFT,
        expand=True,
    )

    status_text  = ft.Text("Conectado", size=13, color=t.GOOD, weight=ft.FontWeight.W_500)
    battery_text = ft.Text("92%", size=13, color=t.TEXT_DARK, weight=ft.FontWeight.W_700)

    def apply_intensity(_):
        # TODO: enviar por WebSocket/BLE → ESP32 guarda en SD
        # payload = {"haptic_intensity": haptic_slider.value}
        page.snack_bar = ft.SnackBar(
            ft.Text(f"Intensidad {int(haptic_slider.value)}% enviada al dispositivo", color=t.CARD),
            bgcolor=t.TEAL,
        )
        page.snack_bar.open = True
        page.update()

    def calibrate(_):
        # TODO: enviar comando de calibración por WebSocket/BLE
        page.snack_bar = ft.SnackBar(ft.Text("Iniciando calibración…", color=t.CARD), bgcolor=t.TEAL)
        page.snack_bar.open = True
        page.update()

    def toggle_power(_):
        # TODO: enviar comando de encendido/apagado por WebSocket/BLE
        page.snack_bar = ft.SnackBar(ft.Text("Comando enviado al dispositivo", color=t.CARD), bgcolor=t.NAVY)
        page.snack_bar.open = True
        page.update()

    sheet = ft.BottomSheet(
        enable_drag=True,
        show_drag_handle=True,
        bgcolor=t.CARD,
        content=ft.Container(
            padding=ft.padding.only(left=20, right=20, bottom=32, top=4),
            content=ft.Column(
                [
                    # ── Encabezado ────────────────────────────────────────────
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(ft.icons.SENSORS, color=t.NAVY, size=26),
                                width=48, height=48, bgcolor="#EEF2F7",
                                border_radius=12, alignment=ft.alignment.center,
                            ),
                            ft.Column(
                                [
                                    ft.Row(
                                        [device_name_text, name_field, edit_btn, confirm_btn],
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        spacing=2,
                                    ),
                                    ft.Row([dot(t.GOOD, 8), status_text], spacing=6),
                                ],
                                spacing=2, expand=True,
                            ),
                            ft.Row(
                                [ft.Icon(ft.icons.BATTERY_FULL, color=t.GOOD, size=18), battery_text],
                                spacing=4,
                            ),
                        ],
                        spacing=12,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),

                    divider(),

                    # ── Vibración ─────────────────────────────────────────────
                    ft.Text("Intensidad de vibración", size=12, color=t.TEXT_MUTED, weight=ft.FontWeight.W_600),
                    ft.Row(
                        [
                            ft.Text("−", size=20, color=t.TEXT_MUTED, weight=ft.FontWeight.W_300),
                            haptic_slider,
                            ft.Text("+", size=20, color=t.TEXT_MUTED, weight=ft.FontWeight.W_300),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.FilledButton(
                        "Aplicar intensidad",
                        icon=ft.icons.VIBRATION,
                        on_click=apply_intensity,
                        style=ft.ButtonStyle(bgcolor=t.NAVY, color=t.CARD),
                        width=float("inf"),
                    ),

                    divider(),

                    # ── Controles del equipo ───────────────────────────────────
                    ft.Text("Controles", size=12, color=t.TEXT_MUTED, weight=ft.FontWeight.W_600),
                    ft.FilledButton(
                        "Calibrar equipo",
                        icon=ft.icons.TUNE,
                        on_click=calibrate,
                        style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD),
                        width=float("inf"),
                    ),
                    ft.Container(height=2),
                    ft.OutlinedButton(
                        content=ft.Row(
                            [
                                ft.Icon(ft.icons.POWER_SETTINGS_NEW, color=t.BAD, size=18),
                                ft.Text("Apagar dispositivo", size=14, color=t.BAD, weight=ft.FontWeight.W_500),
                            ],
                            spacing=8,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        on_click=toggle_power,
                        style=ft.ButtonStyle(
                            side=ft.BorderSide(1, t.BAD),
                            shape=ft.RoundedRectangleBorder(radius=8),
                        ),
                        width=float("inf"),
                    ),
                ],
                spacing=14,
                scroll=ft.ScrollMode.AUTO,
            ),
        ),
    )
    return sheet


# ─── Tarjetas del Resumen ─────────────────────────────────────────────────────

def _device_card(on_tap, name_text: ft.Text) -> ft.Control:
    return ft.GestureDetector(
        on_tap=on_tap,
        content=card(
            ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(ft.icons.SENSORS, color=t.NAVY, size=28),
                        width=52, height=52, bgcolor="#EEF2F7",
                        border_radius=12, alignment=ft.alignment.center,
                    ),
                    ft.Column(
                        [
                            name_text,
                            ft.Row([dot(t.GOOD, 8), ft.Text("Conectado", size=12, color=t.TEXT_MUTED)], spacing=6),
                        ],
                        spacing=4, expand=True,
                    ),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(ft.icons.BATTERY_FULL, color=t.GOOD, size=18),
                                    ft.Text("92%", size=14, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                ],
                                spacing=4, alignment=ft.MainAxisAlignment.END,
                            ),
                            ft.Text("Batería", size=10, color=t.TEXT_MUTED),
                        ],
                        spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END,
                    ),
                    ft.Icon(ft.icons.CHEVRON_RIGHT, color=t.TEXT_LIGHT, size=18),
                ],
                spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=14,
        ),
    )


def _score_card(score: int | None) -> ft.Control:
    if score is None:
        return card(
            ft.Column(
                [
                    card_label("Puntuación postural"),
                    ft.Container(height=8),
                    ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text("—", size=44, weight=ft.FontWeight.W_700, color=t.TEXT_LIGHT),
                                    ft.Container(height=4),
                                    ft.Text("Completá tu primera sesión", size=12, color=t.TEXT_MUTED),
                                ],
                                spacing=2, expand=True,
                            ),
                            ft.Container(
                                content=ft.Icon(ft.icons.QUERY_STATS, color=t.TEAL_SOFT, size=48),
                                width=80, alignment=ft.alignment.center,
                            ),
                        ],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                ],
            )
        )
    else:
        score = max(0, min(100, score))
        label = "Buena" if score >= 70 else ("Regular" if score >= 40 else "A mejorar")
        label_color = t.GOOD if score >= 70 else (t.NEUTRAL if score >= 40 else t.BAD)
        return card(
        ft.Column(
            [
                card_label("Puntuación postural"),
                ft.Container(height=4),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(str(score), size=44, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                        ft.Container(
                                            content=ft.Text("/100", size=15, color=t.TEXT_MUTED),
                                            padding=ft.padding.only(bottom=8),
                                        ),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.END,
                                    spacing=4,
                                ),
                                pill(label, label_color),
                            ],
                            spacing=10, expand=True,
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
                                    width=110, height=110,
                                ),
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text(f"{score}%", size=18, weight=ft.FontWeight.W_700, color=t.NAVY),
                                            ft.Text("Tu puntuación\ngeneral", size=9, color=t.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                                        ],
                                        spacing=0,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        alignment=ft.MainAxisAlignment.CENTER,
                                    ),
                                    width=110, height=110,
                                    alignment=ft.alignment.center,
                                ),
                            ],
                            width=110, height=110,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
        )
    )


def _metric_card(title: str, value: str, subtitle: str) -> ft.Control:
    return card(
        ft.Column(
            [
                card_label(title),
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
            ft.Row([dot(color), ft.Text(label, size=13, color=t.TEXT_DARK)], spacing=8),
            ft.Text(value, size=13, color=t.TEXT_MUTED, weight=ft.FontWeight.W_500),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def _fmt_min(m: float) -> str:
    m = int(m)
    return f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m}m"


def _daily_summary_card(min_buena: float, min_mala: float) -> ft.Control:
    return card(
        ft.Column(
            [
                card_label("Resumen diario"),
                ft.Container(height=6),
                _legend_row(t.GOOD, "Buena postura", _fmt_min(min_buena)),
                _legend_row(t.BAD,  "Mala postura",  _fmt_min(min_mala)),
            ],
            spacing=10,
        )
    )


def _calibration_card() -> ft.Control:
    return card(
        ft.Row(
            [
                ft.Column(
                    [
                        card_label("Última calibración"),
                        ft.Text("Hoy, 08:15", size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
                        ft.Row(
                            [
                                ft.Icon(ft.icons.REFRESH, size=12, color=t.TEAL),
                                ft.Text("Calibración conectada", size=11, color=t.TEAL),
                            ],
                            spacing=4,
                        ),
                    ],
                    spacing=2, expand=True,
                ),
                ft.Container(
                    content=ft.Icon(ft.icons.CHECK, color=t.CARD, size=16),
                    bgcolor=t.GOOD, border_radius=14,
                    width=28, height=28, alignment=ft.alignment.center,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
    )


# ─── Entry point ─────────────────────────────────────────────────────────────

def resumen_view(page: ft.Page) -> ft.Control:
    # Score global (promedio de todas las sesiones)
    try:
        summary = page.api.get_score_summary()
        score = int(summary["score_promedio"]) if summary["total_sesiones"] > 0 else None
    except Exception:
        score = None

    # Tiempo activo y alertas de HOY
    try:
        today = page.api.get_today_summary()
        total_min = today["total_min_uso"]
        horas = int(total_min // 60)
        mins = int(total_min % 60)
        tiempo_str = f"{horas}h {mins:02d}m" if horas > 0 else (f"{mins}m" if mins > 0 else "0m")
        alertas_hoy = today.get("total_alertas", 0)
        min_buena = today.get("total_min_buena", 0.0)
        min_mala  = today.get("total_min_mala", 0.0)
    except Exception:
        tiempo_str, alertas_hoy, min_buena, min_mala = "—", 0, 0.0, 0.0

    username = getattr(page, "username", None) or "Alex"
    # Cargar nombre del dispositivo desde el backend
    try:
        prefs = page.api.get_preferences()
        initial_name = prefs.get("device_name", "ALINA Dispositivo")
    except Exception:
        initial_name = getattr(page, "device_name", "ALINA Dispositivo")

    # Instancias compartidas entre tarjeta y sheet para sincronizar el nombre
    card_name_text = ft.Text(initial_name, size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK)
    sheet_name_text = ft.Text(initial_name, size=16, weight=ft.FontWeight.W_700, color=t.TEXT_DARK)

    device_sheet = _build_device_sheet(page, sheet_name_text, card_name_text)
    page.overlay.append(device_sheet)

    def open_device_sheet(_):
        device_sheet.open = True
        page.update()

    return ft.Column(
        [
            section_header(f"Hola, {username}", "Resumen de hoy"),
            ft.Container(height=10),
            _device_card(on_tap=open_device_sheet, name_text=card_name_text),
            _score_card(score=score),
            ft.Row(
                [
                    ft.Container(content=_metric_card("Tiempo hoy", tiempo_str, "activos"), expand=True),
                    ft.Container(content=_metric_card("Alertas", str(alertas_hoy), "hoy"), expand=True),
                ],
                spacing=12,
            ),
            _daily_summary_card(min_buena=min_buena, min_mala=min_mala),
            _calibration_card(),
            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )