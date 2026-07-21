"""Tab 0 — Resumen: dashboard del día."""

from __future__ import annotations
import threading
import time
import flet as ft
import theme as t
from .components import card, card_label, dot, pill, divider, section_header
from .racha import RachaBadge


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
    conn_dot_ref = ft.Ref[ft.Icon]()

    # def connect_esp(_):
    #     ip = ip_field.value.strip()
    #     if not ip:
    #         return
    #     page.esp_ip = ip
    #     from ws_client import ALINAWebSocket
    #     if not hasattr(page, "ws_client") or page.ws_client is None:
    #         page.ws_client = ALINAWebSocket()
    #     page.ws_client.connect(ip)
    #     conn_status_text.value = "Conectando..."
    #     conn_status_text.color = t.NEUTRAL
    #     page.update()
    
    def connect_esp(_):
        ip = ip_field.value.strip()
        if not ip:
            return
        page.esp_ip = ip
        # page.ws_client ya existe siempre (lo crea home_view al arrancar la app) —
        # acá solo lo conectamos, no lo recreamos.
        ws_local = page.ws_client

        def _on_connected():
            conn_status_text.value = "Conectado"
            conn_status_text.color = t.GOOD
            if conn_dot_ref.current:
                conn_dot_ref.current.color = t.GOOD
            status_text.value = "Conectado"
            status_text.color = t.GOOD
            if status_dot_ref.current:
                status_dot_ref.current.bgcolor = t.GOOD
            _set_connected_ui(True)
            page.update()

        def _on_disconnected():
            conn_status_text.value = "Desconectado"
            conn_status_text.color = t.BAD
            if conn_dot_ref.current:
                conn_dot_ref.current.color = t.BAD
            status_text.value = "Desconectado"
            status_text.color = t.BAD
            if status_dot_ref.current:
                status_dot_ref.current.bgcolor = t.BAD
            _set_connected_ui(False)
            page.update()

        # Sacar listeners viejos de esta misma hoja antes de registrar de nuevo
        # (evita acumular duplicados si tocás "Conectar" más de una vez).
        ws_local.clear_listeners("resumen_sheet_conn")
        ws_local.add_listener("connect",    _on_connected,    owner="resumen_sheet_conn")
        ws_local.add_listener("disconnect", _on_disconnected, owner="resumen_sheet_conn")

        ws_local.connect(ip)
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
    status_dot_ref = ft.Ref[ft.Container]()
    battery_text = ft.Text(
        f"{battery_pct}%" if battery_pct is not None else "—",
        size=13, color=t.TEXT_DARK, weight=ft.FontWeight.W_700,
    )

    # ── Mensajes inline dentro del sheet ──────────────────────────────────────
    # page.snack_bar / show_snack (page.overlay) quedan TAPADOS por este mismo
    # BottomSheet — un modal siempre se pinta por encima del snackbar de la
    # página de atrás, no importa el orden en que se agreguen los controles.
    # En vez de un banner único arriba, cada aviso vive pegado a la acción que
    # lo dispara: el de vibración al lado del título "Duración de la
    # vibración", el de calibración debajo de "Calibrar equipo", el de
    # apagado debajo de "Apagar dispositivo".
    vib_msg_text   = ft.Text("", size=11, weight=ft.FontWeight.W_600, visible=False)
    calib_msg_text = ft.Text("", size=11, weight=ft.FontWeight.W_600, visible=False)
    power_msg_text = ft.Text("", size=11, weight=ft.FontWeight.W_600, visible=False)

    def _set_msg(ctrl: ft.Text, msg: str, color: str, duration: float = 3.5):
        ctrl.value = msg
        ctrl.color = color
        ctrl.visible = True
        page.update()

        # Auto-ocultar después de `duration` segundos — antes quedaba pegado
        # para siempre porque nada volvía a poner visible=False.
        token = object()
        ctrl.data = token  # marca "este es el mensaje más reciente de este control"

        def _clear():
            time.sleep(duration)
            if ctrl.data is token:  # nadie puso un mensaje más nuevo mientras tanto
                ctrl.visible = False
                try:
                    page.update()
                except Exception:
                    pass

        threading.Thread(target=_clear, daemon=True).start()

    def apply_duration(_):
        dur = _snap(float(haptic_slider.value))
        try:
            page.api.update_device_status(haptic_intensity=dur)
        except Exception:
            pass
        if ws and ws.connected:
            ws.set_config(haptic_intensity=dur)
        _set_msg(vib_msg_text, "Duración guardada", t.TEAL)

    def test_vibration(_):
        if ws and ws.connected:
            dur_ms = _snap(float(haptic_slider.value))
            ws.test_vibration(dur_ms)
            # El mensaje dura lo mismo que la vibración real (+ un margen chico
            # para que no se corte justo cuando termina de vibrar).
            _set_msg(vib_msg_text, "Probando vibración…", t.NAVY, duration=dur_ms / 1000 + 0.3)

    def calibrate(_):
        # El firmware (desde la versión con buzzer) solo necesita UN llamado
        # a "calibrate": arranca la calibración y se autocompleta sola a los
        # 5s, sin pedir un segundo toque/comando. No marcamos calibrated=True
        # acá igual, porque el guardado real lo hace el ESP recién cuando
        # terminan esos 5s — eso se refleja en el listener de "status" (ver
        # más abajo, _on_ws_status), que espera la confirmación real del
        # dispositivo en vez de asumirla al tocar el botón.
        if ws and ws.connected:
            ws.calibrate()
            # El firmware ya no pide un segundo toque: con uno solo arranca y
            # se completa sola a los 5s (el buzzer del dispositivo avisa
            # cuando termina) — este mensaje solo tiene que avisar que no hay
            # que tocar nada más mientras tanto.
            _set_msg(calib_msg_text, "Calibrando… mantené la postura 5s (el dispositivo avisa con un sonido al terminar).", t.TEAL, duration=6.0)
        else:
            _set_msg(calib_msg_text, "Conectá el dispositivo antes de calibrar", t.BAD)

    def toggle_power(_):
        _set_msg(power_msg_text, "Comando enviado al dispositivo", t.NAVY)

    # ── Controles cuyo estado (habilitado/deshabilitado, colores) depende de
    # is_connected — antes se calculaba UNA sola vez al abrir la hoja y nunca
    # se actualizaba si te conectabas con la hoja ya abierta. Ahora quedan
    # como variables para poder tocarlos desde _set_connected_ui().
    test_btn = ft.OutlinedButton(
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
    )
    apply_btn = ft.FilledButton(
        "Aplicar",
        icon=ft.icons.CHECK,
        on_click=apply_duration,
        disabled=not is_connected,
        style=ft.ButtonStyle(
            bgcolor=t.NAVY if is_connected else t.DIVIDER,
            color=t.CARD,
        ),
        expand=True,
    )
    calibrate_btn = ft.FilledButton(
        "Calibrar equipo",
        icon=ft.icons.TUNE,
        on_click=calibrate,
        disabled=not is_connected,
        style=ft.ButtonStyle(
            bgcolor=t.TEAL if is_connected else t.DIVIDER,
            color=t.CARD,
        ),
        width=float("inf"),
    )
    power_icon = ft.Icon(ft.icons.POWER_SETTINGS_NEW,
                         color=t.BAD if is_connected else t.TEXT_LIGHT, size=18)
    power_label = ft.Text("Apagar dispositivo", size=14,
                          color=t.BAD if is_connected else t.TEXT_LIGHT,
                          weight=ft.FontWeight.W_500)
    power_btn = ft.OutlinedButton(
        content=ft.Row([power_icon, power_label], spacing=8, alignment=ft.MainAxisAlignment.CENTER),
        on_click=toggle_power,
        disabled=not is_connected,
        style=ft.ButtonStyle(
            side=ft.BorderSide(1, t.BAD if is_connected else t.DIVIDER),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        width=float("inf"),
    )

    def _set_connected_ui(connected: bool):
        """Habilita/deshabilita y recolorea todos los controles que dependen
        de si el ESP está conectado. Se llama desde _on_connected/_on_disconnected
        para que no haga falta cerrar y reabrir la hoja para verlos reaccionar."""
        haptic_slider.disabled = not connected
        haptic_slider.active_color = t.TEAL if connected else t.TEAL_SOFT

        test_btn.disabled = not connected
        test_btn.style = ft.ButtonStyle(
            color=t.TEAL if connected else t.TEXT_LIGHT,
            side=ft.BorderSide(1, t.TEAL if connected else t.DIVIDER),
            shape=ft.RoundedRectangleBorder(radius=8),
        )

        apply_btn.disabled = not connected
        apply_btn.style = ft.ButtonStyle(bgcolor=t.NAVY if connected else t.DIVIDER, color=t.CARD)

        calibrate_btn.disabled = not connected
        calibrate_btn.style = ft.ButtonStyle(bgcolor=t.TEAL if connected else t.DIVIDER, color=t.CARD)

        power_btn.disabled = not connected
        power_btn.style = ft.ButtonStyle(
            side=ft.BorderSide(1, t.BAD if connected else t.DIVIDER),
            shape=ft.RoundedRectangleBorder(radius=8),
        )
        power_icon.color = t.BAD if connected else t.TEXT_LIGHT
        power_label.color = t.BAD if connected else t.TEXT_LIGHT

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
                                    ft.Row([
                                        ft.Container(ref=status_dot_ref, width=8, height=8, border_radius=8,
                                                     bgcolor=t.GOOD if is_connected else t.BAD),
                                        status_text,
                                    ], spacing=6),
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
                        [ft.Icon(ft.icons.CIRCLE, ref=conn_dot_ref, size=10,
                                 color=t.GOOD if is_connected else t.BAD),
                         conn_status_text],
                        spacing=6,
                    ),

                    divider(),

                    # ── Duración de vibración ─────────────────────────────────
                    ft.Row(
                        [
                            ft.Text("Duración de la vibración", size=12, color=t.TEXT_MUTED, weight=ft.FontWeight.W_600),
                            vib_msg_text,
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
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
                        [test_btn, apply_btn],
                        spacing=8,
                    ),

                    divider(),

                    # ── Controles del equipo ───────────────────────────────────
                    ft.Text("Controles", size=12, color=t.TEXT_MUTED, weight=ft.FontWeight.W_600),
                    calibrate_btn,
                    calib_msg_text,
                    ft.Container(height=2),
                    power_btn,
                    power_msg_text,
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
    """m viene en minutos (float). Siempre muestra minutos + segundos con
    1 decimal (ej. "3m 54.2s"), salvo que pase la hora, donde vuelve al
    formato "Xh YYm" (los segundos ya no aportan nada a esa escala)."""
    total_sec = m * 60
    if total_sec >= 3600:
        mins = int(m)
        return f"{mins // 60}h {mins % 60:02d}m"
    mins = int(total_sec // 60)
    secs = total_sec - mins * 60
    return f"{mins}m {secs:.1f}s"


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

    # ── Cargar datos iniciales ────────────────────────────────────────────────
    def _load_device():
        # El estado de conexión es del WebSocket (en memoria) y NO depende de
        # si el backend responde — antes, si get_device_status() fallaba por
        # lo que sea, esto forzaba "connected": False aunque el ESP estuviera
        # conectado. Ahora se calcula siempre, incluso si el resto falla.
        ws = getattr(page, "ws_client", None)
        connected = ws is not None and ws.connected
        try:
            ds = page.api.get_device_status()
            return {
                "name":      ds.get("device_name", "ALINA Dispositivo"),
                "battery":   ds.get("battery_pct"),
                "haptic":    ds.get("haptic_intensity", 60),
                "calibrated":ds.get("calibrated", False),
                "connected": connected,
            }
        except Exception:
            return {"name": "ALINA Dispositivo", "battery": None, "haptic": 60, "calibrated": False, "connected": connected}

    def _load_score():
        try:
            summary = page.api.get_score_summary()
            return int(summary["score_promedio"]) if summary["total_sesiones"] > 0 else None
        except Exception:
            return None

    def _load_today():
        try:
            today = page.api.get_today_summary()
            total_min = today["total_min_uso"]
            horas = int(total_min // 60)
            mins  = int(total_min % 60)
            tiempo_str = f"{horas}h {mins:02d}m" if horas > 0 else (f"{mins}m" if mins > 0 else "0m")
            return {
                "tiempo":    tiempo_str,
                "alertas":   today.get("total_alertas", 0),
                "min_buena": today.get("total_min_buena", 0.0),
                "min_mala":  today.get("total_min_mala", 0.0),
            }
        except Exception:
            return {"tiempo": "—", "alertas": 0, "min_buena": 0.0, "min_mala": 0.0}

    dev   = _load_device()
    score = _load_score()
    today = _load_today()
    username = getattr(page, "username", None)
    if not username:
        try:
            me = page.api.get_me()
            username = me.get("nombre") or me.get("email", "").split("@")[0]
        except Exception:
            username = "vos"

    # ── Refs para actualizar sin reconstruir ──────────────────────────────────
    device_card_ref  = ft.Ref[ft.Container]()
    score_card_ref   = ft.Ref[ft.Container]()
    tiempo_ref       = ft.Ref[ft.Text]()
    alertas_ref      = ft.Ref[ft.Text]()
    min_buena_ref    = ft.Ref[ft.Text]()
    min_mala_ref     = ft.Ref[ft.Text]()

    # ── Badge de racha (header) ───────────────────────────────────────────────
    def _load_racha():
        """Racha actual (int) o None si el backend no responde."""
        try:
            return int(page.api.get_racha().get("racha_actual", 0))
        except Exception:
            return None

    _racha_val = _load_racha()
    racha_badge = RachaBadge(page, value=_racha_val or 0)
    # Guardamos la racha de arranque como "vista": solo festejamos cuando SUBE
    # respecto de lo último visto (lo detecta refresh() o el force por terminal).
    if _racha_val is not None:
        try:
            page.client_storage.set("alina_racha_seen", _racha_val)
        except Exception:
            pass

    def _refresh_racha():
        nueva = _load_racha()
        if nueva is None:
            return
        if nueva > racha_badge.value:
            racha_badge.animate_to(nueva)   # subió → celebrar
        elif nueva != racha_badge.value:
            racha_badge.set(nueva)          # bajó/reset → sin animación
        else:
            return
        try:
            page.client_storage.set("alina_racha_seen", nueva)
        except Exception:
            pass

    # ── Nombre compartido entre card y sheet ─────────────────────────────────
    card_name_text  = ft.Text(dev["name"], size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK)
    sheet_name_text = ft.Text(dev["name"], size=16, weight=ft.FontWeight.W_700, color=t.TEXT_DARK)

    device_sheet = _build_device_sheet(page, sheet_name_text, card_name_text,
                                       haptic_init=dev["haptic"], battery_pct=dev["battery"])
    # Sacar el sheet de una visita anterior a esta tab antes de agregar el
    # nuevo — si no, page.overlay va acumulando uno por cada vez que se entra
    # a Resumen, y alguno puede quedar "open" y aparecer flotando sobre otra
    # tab al navegar (el overlay es global, no se cierra solo al cambiar de tab).
    old_sheet = getattr(page, "_device_sheet", None)
    if old_sheet is not None:
        old_sheet.open = False
        if old_sheet in page.overlay:
            page.overlay.remove(old_sheet)
    page._device_sheet = device_sheet
    page.overlay.append(device_sheet)

    # ── Escuchar "status" del ESP para reflejar la calibración REAL ──────────
    # (el firmware manda "calibrated": true/false en cada status; acá lo
    # persistimos en el backend en vez de asumirlo al tocar el botón).
    ws = getattr(page, "ws_client", None)
    if ws:
        ws.clear_listeners("resumen_status")

        def _on_ws_status(data: dict):
            from datetime import datetime
            cal = bool(data.get("calibrated", False))
            try:
                payload = {"calibrated": cal}
                if cal:
                    payload["last_calibration_at"] = datetime.now().isoformat(timespec="seconds")
                page.api.update_device_status(**payload)
            except Exception:
                pass
            device_card_ref.current.content = _device_card(
                on_tap=open_device_sheet,
                name_text=ft.Text(card_name_text.value, size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
                battery_pct=dev.get("battery"),
                calibrated=cal,
                connected=ws.connected,
            )
            try:
                page.update()
            except Exception:
                pass

        ws.add_listener("status", _on_ws_status, owner="resumen_status")

    def open_device_sheet(_):
        device_sheet.open = True
        page.update()

    # ── Refresh — llamado por el timer en home_view ───────────────────────────
    def refresh():
        new_dev   = _load_device()
        new_score = _load_score()
        new_today = _load_today()

        # Actualizar card del dispositivo
        device_card_ref.current.content = _device_card(
            on_tap=open_device_sheet,
            name_text=ft.Text(new_dev["name"], size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
            battery_pct=new_dev["battery"],
            calibrated=new_dev["calibrated"],
            connected=new_dev["connected"],
        )

        # Actualizar score
        score_card_ref.current.content = _score_card(score=new_score)

        # Actualizar métricas
        tiempo_ref.current.value    = new_today["tiempo"]
        alertas_ref.current.value   = str(new_today["alertas"])
        min_buena_ref.current.value = _fmt_min(new_today["min_buena"])
        min_mala_ref.current.value  = _fmt_min(new_today["min_mala"])

        # Racha: si subió respecto de lo mostrado, dispara la animación.
        _refresh_racha()

    def on_device_change(connected: bool, calibrated: bool = False):
        """Llamado desde ws_client.on_connect / on_disconnect — actualiza solo la card del dispositivo."""
        try:
            ds = page.api.get_device_status()
            name     = ds.get("device_name", "ALINA Dispositivo")
            battery  = ds.get("battery_pct")
            cal      = calibrated or ds.get("calibrated", False)
        except Exception:
            name, battery, cal = "ALINA Dispositivo", None, calibrated
        device_card_ref.current.content = _device_card(
            on_tap=open_device_sheet,
            name_text=ft.Text(name, size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
            battery_pct=battery,
            calibrated=cal,
            connected=connected,
        )
        try:
            page.update()
        except Exception:
            pass

    def on_session_saved():
        """Llamado desde en_vivo_view cuando se guarda una sesión — actualiza score y métricas."""
        new_score = _load_score()
        new_today = _load_today()
        score_card_ref.current.content = _score_card(score=new_score)
        tiempo_ref.current.value    = new_today["tiempo"]
        alertas_ref.current.value   = str(new_today["alertas"])
        min_buena_ref.current.value = _fmt_min(new_today["min_buena"])
        min_mala_ref.current.value  = _fmt_min(new_today["min_mala"])
        _refresh_racha()
        try:
            page.update()
        except Exception:
            pass
        
    def on_alert_received():
        """Llamado desde en_vivo cuando el ESP manda una alerta (vibró por mala postura)."""
        try:
            current = int(alertas_ref.current.value or "0")
        except Exception:
            current = 0
        alertas_ref.current.value = str(current + 1)
        try:
            page.update()
        except Exception:
            pass



    # ── Construir UI ──────────────────────────────────────────────────────────
    col = ft.Column(
        [
            section_header(f"Hola, {username}", "Resumen de hoy", badge=racha_badge.control),
            ft.Container(height=10),
            ft.Container(
                ref=device_card_ref,
                content=_device_card(
                    on_tap=open_device_sheet,
                    name_text=card_name_text,
                    battery_pct=dev["battery"],
                    calibrated=dev["calibrated"],
                    connected=dev["connected"],
                ),
            ),
            ft.Container(
                ref=score_card_ref,
                content=_score_card(score=score),
            ),
            ft.Row(
                [
                    ft.Container(
                        expand=True,
                        content=card(ft.Column([
                            card_label("Tiempo hoy"),
                            ft.Container(height=2),
                            ft.Text(ref=tiempo_ref, value=today["tiempo"], size=24, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                            ft.Text("activos", size=11, color=t.TEXT_LIGHT),
                        ], spacing=2), padding=14),
                    ),
                    ft.Container(
                        expand=True,
                        content=card(ft.Column([
                            card_label("Alertas"),
                            ft.Container(height=2),
                            ft.Text(ref=alertas_ref, value=str(today["alertas"]), size=24, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                            ft.Text("hoy", size=11, color=t.TEXT_LIGHT),
                        ], spacing=2), padding=14),
                    ),
                ],
                spacing=12,
            ),
            card(
                ft.Column([
                    card_label("Resumen diario"),
                    ft.Container(height=6),
                    ft.Row(
                        [
                            ft.Row([dot(t.GOOD), ft.Text("Buena postura", size=13, color=t.TEXT_DARK)], spacing=8),
                            ft.Text(ref=min_buena_ref, value=_fmt_min(today["min_buena"]), size=13, color=t.TEXT_MUTED, weight=ft.FontWeight.W_500),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Row(
                        [
                            ft.Row([dot(t.BAD), ft.Text("Mala postura", size=13, color=t.TEXT_DARK)], spacing=8),
                            ft.Text(ref=min_mala_ref, value=_fmt_min(today["min_mala"]), size=13, color=t.TEXT_MUTED, weight=ft.FontWeight.W_500),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                ], spacing=10)
            ),
            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Adjuntar el método refresh al Column para que home_view pueda llamarlo
    col.refresh          = refresh
    col.on_device_change = on_device_change
    col.on_session_saved = on_session_saved
    col.on_alert_received = on_alert_received
    return col