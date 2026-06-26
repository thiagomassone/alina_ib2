"""Tab 0 — Resumen: dashboard del día."""

from __future__ import annotations
import flet as ft
import theme as t
from .components import card, card_label, dot, pill, divider, section_header


# ─── Panel de dispositivo (BottomSheet) ──────────────────────────────────────

def _build_device_sheet(page: ft.Page, device_name_text: ft.Text, card_name_text: ft.Text, haptic_init: int = 1000, battery_pct: int | None = None) -> ft.BottomSheet:
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
            page.api.update_device_status(device_name=new_name)
        except Exception:
            pass  # Si el backend no está disponible, queda en memoria
        page.update()

    edit_btn.on_click = start_edit
    confirm_btn.on_click = finish_edit
    name_field.on_submit = finish_edit

    # ── Estado de conexión ───────────────────────────────────────────────────
    ws = getattr(page, "ws_client", None)
    #is_connected = True  # TEST para validar opciones con conexion
    is_connected = ws is not None and ws.connected

    # ── IP del dispositivo ────────────────────────────────────────────────────
    ip_field = ft.TextField(
        label="Dirección del dispositivo",
        hint_text="alina.local o IP manual",
        value=getattr(page, "esp_ip", "alina.local"),
        border_color=t.DIVIDER,
        focused_border_color=t.TEAL,
        expand=True,
        disabled=False,  # siempre editable
    )
    conn_status_text = ft.Text(
        "Conectado" if is_connected else "Desconectado",
        size=12,
        color=t.GOOD if is_connected else t.BAD,
        weight=ft.FontWeight.W_500,
    )

    def connect_esp(_):
        ip = ip_field.value.strip()
        if not ip:
            return
        page.esp_ip = ip
        from ws_client import ALINAWebSocket
        if not hasattr(page, "ws_client") or page.ws_client is None:
            page.ws_client = ALINAWebSocket()
        page.ws_client.connect(ip)
        conn_status_text.value = "Conectando..."
        conn_status_text.color = t.NEUTRAL
        page.update()

    # ── Slider de duración de vibración — 5 posiciones fijas ────────────────
    _STEPS = [250, 500, 1000, 1500, 2000]
    _LABELS = {250: "Muy corta", 500: "Corta", 1000: "Media", 1500: "Larga", 2000: "Muy larga"}

    def _snap(val: float) -> int:
        return min(_STEPS, key=lambda s: abs(s - val))

    # Valor inicial: el más cercano al haptic_init guardado
    _init_val = _snap(haptic_init)

    slider_label = ft.Text(
        _LABELS[_init_val],
        size=13, color=t.TEAL, weight=ft.FontWeight.W_600,
    )

    def _on_slider_change(e):
        snapped = _snap(float(e.control.value))
        e.control.value = snapped
        slider_label.value = _LABELS[snapped]
        page.update()

    haptic_slider = ft.Slider(
        min=250, max=2000, value=_init_val,
        divisions=4,
        active_color=t.TEAL if is_connected else t.TEAL_SOFT,
        inactive_color=t.TEAL_SOFT,
        expand=True,
        disabled=not is_connected,
        on_change=_on_slider_change,
    )

    status_text  = ft.Text(
        "Conectado" if is_connected else "Desconectado",
        size=13,
        color=t.GOOD if is_connected else t.BAD,
        weight=ft.FontWeight.W_500,
    )
    battery_text = ft.Text(
        f"{battery_pct}%" if battery_pct is not None else "—",
        size=13, color=t.TEXT_DARK, weight=ft.FontWeight.W_700,
    )

    def apply_duration(_):
        dur = _snap(float(haptic_slider.value))
        try:
            page.api.update_device_status(haptic_intensity=dur)
        except Exception:
            pass
        if ws and ws.connected:
            ws.set_config(haptic_intensity=dur)
        page.snack_bar = ft.SnackBar(
            ft.Text("Duración guardada en el dispositivo", color=t.CARD),
            bgcolor=t.TEAL,
        )
        page.snack_bar.open = True
        page.update()

    def test_vibration(_):
        if ws and ws.connected:
            ws.test_vibration(_snap(float(haptic_slider.value)))
            page.snack_bar = ft.SnackBar(
                ft.Text("Probando vibración…", color=t.CARD), bgcolor=t.NAVY)
            page.snack_bar.open = True
            page.update()

    def calibrate(_):
        from datetime import datetime
        ts = datetime.now().isoformat(timespec="seconds")
        try:
            page.api.update_device_status(last_calibration_at=ts, calibrated=True)
        except Exception:
            pass
        if ws and ws.connected:
            ws.calibrate()
        page.snack_bar = ft.SnackBar(
            ft.Text("Calibración iniciada", color=t.CARD), bgcolor=t.TEAL)
        page.snack_bar.open = True
        page.update()

    def toggle_power(_):
        page.snack_bar = ft.SnackBar(
            ft.Text("Comando enviado al dispositivo", color=t.CARD), bgcolor=t.NAVY)
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

                    # ── Conexión ──────────────────────────────────────────────
                    ft.Text("Conexión", size=12, color=t.TEXT_MUTED, weight=ft.FontWeight.W_600),
                    ft.Row(
                        [ip_field, ft.FilledButton(
                            "Conectar",
                            icon=ft.icons.WIFI,
                            on_click=connect_esp,
                            style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD),
                        )],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [ft.Icon(ft.icons.CIRCLE, size=10,
                                 color=t.GOOD if is_connected else t.BAD),
                         conn_status_text],
                        spacing=6,
                    ),

                    divider(),

                    # ── Duración de vibración ─────────────────────────────────
                    ft.Text("Duración de la vibración", size=12, color=t.TEXT_MUTED, weight=ft.FontWeight.W_600),
                    ft.Row(
                        [
                            ft.Text("−", size=20, color=t.TEXT_MUTED, weight=ft.FontWeight.W_300),
                            haptic_slider,
                            ft.Text("+", size=20, color=t.TEXT_MUTED, weight=ft.FontWeight.W_300),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "Probar",
                                icon=ft.icons.VIBRATION,
                                on_click=test_vibration,
                                disabled=not is_connected,
                                style=ft.ButtonStyle(
                                    color=t.TEAL if is_connected else t.TEXT_LIGHT,
                                    side=ft.BorderSide(1, t.TEAL if is_connected else t.DIVIDER),
                                    shape=ft.RoundedRectangleBorder(radius=8),
                                ),
                                expand=True,
                            ),
                            ft.FilledButton(
                                "Aplicar",
                                icon=ft.icons.CHECK,
                                on_click=apply_duration,
                                disabled=not is_connected,
                                style=ft.ButtonStyle(
                                    bgcolor=t.NAVY if is_connected else t.DIVIDER,
                                    color=t.CARD,
                                ),
                                expand=True,
                            ),
                        ],
                        spacing=8,
                    ),

                    divider(),

                    # ── Controles del equipo ───────────────────────────────────
                    ft.Text("Controles", size=12, color=t.TEXT_MUTED, weight=ft.FontWeight.W_600),
                    ft.FilledButton(
                        "Calibrar equipo",
                        icon=ft.icons.TUNE,
                        on_click=calibrate,
                        disabled=not is_connected,
                        style=ft.ButtonStyle(
                            bgcolor=t.TEAL if is_connected else t.DIVIDER,
                            color=t.CARD,
                        ),
                        width=float("inf"),
                    ),
                    ft.Container(height=2),
                    ft.OutlinedButton(
                        content=ft.Row(
                            [
                                ft.Icon(ft.icons.POWER_SETTINGS_NEW,
                                        color=t.BAD if is_connected else t.TEXT_LIGHT, size=18),
                                ft.Text("Apagar dispositivo", size=14,
                                        color=t.BAD if is_connected else t.TEXT_LIGHT,
                                        weight=ft.FontWeight.W_500),
                            ],
                            spacing=8,
                            alignment=ft.MainAxisAlignment.CENTER,
                        ),
                        on_click=toggle_power,
                        disabled=not is_connected,
                        style=ft.ButtonStyle(
                            side=ft.BorderSide(1, t.BAD if is_connected else t.DIVIDER),
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

def _device_card(on_tap, name_text: ft.Text, battery_pct: int | None, calibrated: bool, connected: bool) -> ft.Control:
    """Tarjeta del dispositivo con 3 estados:
    - Listo (verde): conectado y calibrado
    - Pendiente de calibrar (amarillo): conectado sin calibrar
    - Desconectado (rojo): sin señal
    """
    if not connected:
        status_color  = t.BAD
        status_label  = "Desconectado"
        status_dot_c  = t.BAD
    elif not calibrated:
        status_color  = t.NEUTRAL
        status_label  = "Pendiente de calibrar"
        status_dot_c  = t.NEUTRAL
    else:
        status_color  = t.GOOD
        status_label  = "Listo"
        status_dot_c  = t.GOOD

    # Batería
    if battery_pct is None:
        bat_icon  = ft.icons.BATTERY_UNKNOWN
        bat_color = t.TEXT_LIGHT
        bat_str   = "—"
    elif battery_pct > 60:
        bat_icon  = ft.icons.BATTERY_FULL
        bat_color = t.GOOD
        bat_str   = f"{battery_pct}%"
    elif battery_pct > 20:
        bat_icon  = ft.icons.BATTERY_4_BAR
        bat_color = t.NEUTRAL
        bat_str   = f"{battery_pct}%"
    else:
        bat_icon  = ft.icons.BATTERY_1_BAR
        bat_color = t.BAD
        bat_str   = f"{battery_pct}%"

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
                            ft.Row([dot(status_dot_c, 8), ft.Text(status_label, size=12, color=status_color, weight=ft.FontWeight.W_500)], spacing=6),
                        ],
                        spacing=4, expand=True,
                    ),
                    ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Icon(bat_icon, color=bat_color, size=18),
                                    ft.Text(bat_str, size=14, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
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
    # Cargar estado del dispositivo desde el backend
    try:
        ds = page.api.get_device_status()
        initial_name    = ds.get("device_name", "ALINA Dispositivo")
        battery_pct     = ds.get("battery_pct")
        haptic_init     = ds.get("haptic_intensity", 60)
        calibrated      = ds.get("calibrated", False)
        ws = getattr(page, "ws_client", None)
        connected = ws is not None and ws.connected
    except Exception:
        initial_name, battery_pct, haptic_init, calibrated, connected = "ALINA Dispositivo", None, 60, False, False

    # Instancias compartidas entre tarjeta y sheet para sincronizar el nombre
    card_name_text = ft.Text(initial_name, size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK)
    sheet_name_text = ft.Text(initial_name, size=16, weight=ft.FontWeight.W_700, color=t.TEXT_DARK)

    device_sheet = _build_device_sheet(page, sheet_name_text, card_name_text, haptic_init=haptic_init, battery_pct=battery_pct)
    page.overlay.append(device_sheet)

    def open_device_sheet(_):
        device_sheet.open = True
        page.update()

    return ft.Column(
        [
            section_header(f"Hola, {username}", "Resumen de hoy"),
            ft.Container(height=10),
            _device_card(on_tap=open_device_sheet, name_text=card_name_text, battery_pct=battery_pct, calibrated=calibrated, connected=connected),
            _score_card(score=score),
            ft.Row(
                [
                    ft.Container(content=_metric_card("Tiempo hoy", tiempo_str, "activos"), expand=True),
                    ft.Container(content=_metric_card("Alertas", str(alertas_hoy), "hoy"), expand=True),
                ],
                spacing=12,
            ),
            _daily_summary_card(min_buena=min_buena, min_mala=min_mala),
            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )
