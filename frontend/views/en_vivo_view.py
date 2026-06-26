"""Tab 1 — En vivo: visualización en tiempo real + control de sesión."""

from __future__ import annotations
import time
import threading
from datetime import datetime
import flet as ft
import theme as t
from .components import card, card_label, section_header


# ─── SVG de espalda con IMUs ─────────────────────────────────────────────────

def _imu_color(status: str) -> str:
    return {"listo": t.GOOD, "calibrar": t.NEUTRAL, "desconectado": t.BAD}.get(status, t.BAD)


def _back_svg_widget(imu_states: dict) -> ft.Control:
    import base64
    sup = _imu_color(imu_states.get("dorsal_superior", "desconectado"))
    mid = _imu_color(imu_states.get("dorsal_medio",    "desconectado"))
    pel = _imu_color(imu_states.get("pelvis",          "desconectado"))

    svg = f"""<svg viewBox="0 0 200 340" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="100" cy="28" rx="22" ry="26" fill="#D9E3EE"/>
  <rect x="90" y="50" width="20" height="18" rx="4" fill="#D9E3EE"/>
  <path d="M100 60 Q78 60 64 68 Q48 78 46 100 Q44 124 50 150 Q50 180 58 210 Q68 230 100 232 Q132 230 142 210 Q150 180 150 150 Q156 124 154 100 Q152 78 136 68 Q122 60 100 60Z" fill="#D9E3EE"/>
  <path d="M44 88 Q36 120 38 155 Q40 168 48 172 Q56 176 60 164 Q66 140 68 110 Q64 92 56 86Z" fill="#D9E3EE"/>
  <path d="M156 88 Q164 120 162 155 Q160 168 152 172 Q144 176 140 164 Q134 140 132 110 Q136 92 144 86Z" fill="#D9E3EE"/>
  <path d="M60 210 Q58 235 65 248 Q80 258 100 258 Q120 258 135 248 Q142 235 140 210Z" fill="#C8D6E8"/>
  <line x1="100" y1="68" x2="100" y2="228" stroke="#B0C4D8" stroke-width="1.5" stroke-dasharray="4,4"/>
  <circle cx="100" cy="88"  r="16" fill="{sup}" opacity="0.2"/>
  <circle cx="100" cy="88"  r="9"  fill="{sup}"/>
  <circle cx="100" cy="88"  r="4"  fill="white" opacity="0.7"/>
  <circle cx="100" cy="148" r="16" fill="{mid}" opacity="0.2"/>
  <circle cx="100" cy="148" r="9"  fill="{mid}"/>
  <circle cx="100" cy="148" r="4"  fill="white" opacity="0.7"/>
  <circle cx="100" cy="215" r="16" fill="{pel}" opacity="0.2"/>
  <circle cx="100" cy="215" r="9"  fill="{pel}"/>
  <circle cx="100" cy="215" r="4"  fill="white" opacity="0.7"/>
</svg>"""
    return ft.Image(
        src_base64=base64.b64encode(svg.encode()).decode(),
        width=200, height=340, fit=ft.ImageFit.CONTAIN,
    )


def _legend_item(color: str, label: str) -> ft.Control:
    return ft.Row(
        [ft.Container(width=10, height=10, bgcolor=color, border_radius=10),
         ft.Text(label, size=11, color=t.TEXT_MUTED)],
        spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ─── Entry point ─────────────────────────────────────────────────────────────

def en_vivo_view(page: ft.Page) -> ft.Control:

    # ── Estado de IMUs — se actualiza con mensajes del ESP ────────────────────
    imu_states = {
        "dorsal_superior": "desconectado",
        "dorsal_medio":    "desconectado",
        "pelvis":          "desconectado",
    }

    # ── Controles reactivos ───────────────────────────────────────────────────
    back_img    = ft.Ref[ft.Image]()
    timer_text  = ft.Text("00:00", size=32, weight=ft.FontWeight.W_700, color=t.TEXT_DARK)
    status_text = ft.Text("Sin sesión activa", size=13, color=t.TEXT_MUTED)
    conn_status = ft.Text("Desconectado", size=13, color=t.TEXT_MUTED)

    start_btn = ft.FilledButton(
        "Iniciar sesión", icon=ft.icons.PLAY_ARROW,
        style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD), expand=True,
    )
    pause_btn = ft.FilledButton(
        "Pausar", icon=ft.icons.PAUSE,
        style=ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.CARD),
        expand=True, visible=False,
    )
    stop_btn = ft.OutlinedButton(
        "Finalizar", icon=ft.icons.STOP,
        style=ft.ButtonStyle(color=t.BAD, side=ft.BorderSide(1, t.BAD),
                             shape=ft.RoundedRectangleBorder(radius=8)),
        expand=True, visible=False,
    )

    # ── Estado local de sesión ────────────────────────────────────────────────
    session_active  = False
    session_paused  = False
    session_start:  datetime | None = None
    elapsed_seconds = 0
    timer_running   = [False]

    # Datos que llegan del ESP al finalizar sesión
    last_session_data: dict = {}

    def _fmt_time(s: int) -> str:
        h, m, sec = s // 3600, (s % 3600) // 60, s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}" if h > 0 else f"{m:02d}:{sec:02d}"

    def _tick():
        nonlocal elapsed_seconds
        while timer_running[0]:
            time.sleep(1)
            if timer_running[0] and not session_paused:
                elapsed_seconds += 1
                timer_text.value = _fmt_time(elapsed_seconds)
                try: page.update()
                except: break

    # ── WebSocket callbacks ───────────────────────────────────────────────────
    ws = getattr(page, "ws_client", None)

    def _on_ws_connect():
        conn_status.value = "Conectado"
        conn_status.color = t.GOOD
        try: page.update()
        except: pass

    def _on_ws_disconnect():
        conn_status.value = "Desconectado"
        conn_status.color = t.BAD
        # Actualizar IMUs a desconectado
        for k in imu_states: imu_states[k] = "desconectado"
        try: page.update()
        except: pass

    def _on_status(data: dict):
        # Actualizar estados de IMUs según respuesta del ESP
        imu_states["dorsal_superior"] = "listo" if data.get("imu_t12") else "desconectado"
        imu_states["dorsal_medio"]    = "listo" if data.get("imu_t1")  else "desconectado"
        imu_states["pelvis"]          = "listo" if data.get("imu_rpsis") else "desconectado"
        # Si no está calibrado, cambiar a "calibrar"
        if not data.get("calibrated"):
            for k in imu_states:
                if imu_states[k] == "listo":
                    imu_states[k] = "calibrar"
        try: page.update()
        except: pass

    def _on_session_end(data: dict):
        nonlocal last_session_data
        last_session_data = data
        # Guardar sesión en el backend
        try:
            page.api.create_session(
                started_at=session_start.isoformat() if session_start else datetime.now().isoformat(),
                duracion_min=data.get("duracion_min", elapsed_seconds / 60),
                alertas_hapticas=data.get("alertas_hapticas", 0),
                min_buena=data.get("min_buena", 0.0),
                min_mala=data.get("min_mala", 0.0),
            )
            page.snack_bar = ft.SnackBar(
                ft.Text("Sesión guardada correctamente", color=t.CARD), bgcolor=t.TEAL)
        except Exception as e:
            page.snack_bar = ft.SnackBar(
                ft.Text(f"Error guardando sesión: {e}", color=t.CARD), bgcolor=t.BAD)
        page.snack_bar.open = True
        try: page.update()
        except: pass

    def _on_session_status(data: dict):
        state = data.get("state")
        if state == "running":
            status_text.value = "Sesión en curso"
            status_text.color = t.GOOD
        elif state == "paused":
            status_text.value = "Sesión pausada"
            status_text.color = t.NEUTRAL
        elif state == "idle":
            status_text.value = "Sin sesión activa"
            status_text.color = t.TEXT_MUTED
        try: page.update()
        except: pass

    # Registrar callbacks si hay ws_client en page
    if ws:
        ws.on_connect        = _on_ws_connect
        ws.on_disconnect     = _on_ws_disconnect
        ws.on_status         = _on_status
        ws.on_session_end    = _on_session_end
        ws.on_session_status = _on_session_status
        if ws.connected:
            conn_status.value = "Conectado"
            conn_status.color = t.GOOD
        if getattr(ws, "last_status", None):
            _on_status(ws.last_status)

    # ── Handlers de botones ───────────────────────────────────────────────────

    def start_session(_):
        nonlocal session_active, session_paused, session_start, elapsed_seconds
        session_active  = True
        session_paused  = False
        session_start   = datetime.now()
        elapsed_seconds = 0
        start_btn.visible = False
        pause_btn.visible = True
        stop_btn.visible  = True
        status_text.value = "Sesión en curso"
        status_text.color = t.GOOD
        timer_text.value  = "00:00"
        timer_running[0]  = True
        threading.Thread(target=_tick, daemon=True).start()
        if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
            page.ws_client.start_session()
        page.update()

    def toggle_pause(_):
        nonlocal session_paused
        session_paused = not session_paused
        if session_paused:
            pause_btn.text  = "Reanudar"
            pause_btn.icon  = ft.icons.PLAY_ARROW
            pause_btn.style = ft.ButtonStyle(bgcolor=t.GOOD, color=t.CARD)
            if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
                page.ws_client.pause_session()
        else:
            pause_btn.text  = "Pausar"
            pause_btn.icon  = ft.icons.PAUSE
            pause_btn.style = ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.CARD)
            if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
                page.ws_client.resume_session()
        page.update()

    def stop_session(_):
        nonlocal session_active, session_paused, elapsed_seconds
        timer_running[0] = False
        session_active   = False
        session_paused   = False
        start_btn.visible = True
        pause_btn.visible = False
        stop_btn.visible  = False
        pause_btn.text    = "Pausar"
        pause_btn.icon    = ft.icons.PAUSE
        pause_btn.style   = ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.CARD)
        if hasattr(page, "ws_client") and page.ws_client and page.ws_client.connected:
            # El ESP responde con session_end que dispara _on_session_end
            page.ws_client.stop_session()
        else:
            # Sin ESP: guardar con datos del timer local
            try:
                page.api.create_session(
                    started_at=session_start.isoformat() if session_start else datetime.now().isoformat(),
                    duracion_min=elapsed_seconds / 60,
                    alertas_hapticas=0,
                    min_buena=0.0,
                    min_mala=0.0,
                )
                page.snack_bar = ft.SnackBar(
                    ft.Text("Sesión guardada (sin datos del dispositivo)", color=t.CARD),
                    bgcolor=t.NEUTRAL)
            except Exception as e:
                page.snack_bar = ft.SnackBar(
                    ft.Text(f"Error: {e}", color=t.CARD), bgcolor=t.BAD)
            page.snack_bar.open = True
        status_text.value = "Sin sesión activa"
        status_text.color = t.TEXT_MUTED
        timer_text.value  = "00:00"
        elapsed_seconds   = 0
        page.update()

    start_btn.on_click  = start_session
    pause_btn.on_click  = toggle_pause
    stop_btn.on_click   = stop_session

    return ft.Column(
        [
            section_header("En vivo", "Estado del dispositivo"),
            ft.Container(height=10),

            # ── Diagrama + leyenda ─────────────────────────────────────────
            card(
                ft.Column(
                    [
                        card_label("IMUs"),
                        ft.Container(height=8),
                        ft.Row(
                            [
                                ft.Container(
                                    content=_back_svg_widget(imu_states),
                                    expand=True,
                                    alignment=ft.alignment.center,
                                ),
                                ft.Column(
                                    [
                                        ft.Text("Estado", size=11, color=t.TEXT_MUTED, weight=ft.FontWeight.W_600),
                                        ft.Container(height=6),
                                        _legend_item(t.GOOD,    "Listo"),
                                        _legend_item(t.NEUTRAL, "Pendiente de calibrar"),
                                        _legend_item(t.BAD,     "Desconectado"),
                                    ],
                                    spacing=6,
                                    horizontal_alignment=ft.CrossAxisAlignment.START,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=8,
                        ),
                    ],
                    spacing=0,
                )
            ),

            # ── Timer + controles ──────────────────────────────────────────
            card(
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Column(
                                    [
                                        card_label("Sesión actual"),
                                        ft.Container(height=4),
                                        timer_text,
                                        status_text,
                                    ],
                                    spacing=2, expand=True,
                                ),
                                ft.Icon(ft.icons.TIMER_OUTLINED, color=t.TEAL_SOFT, size=40),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=12),
                        ft.Row([start_btn, pause_btn, stop_btn], spacing=8),
                    ],
                    spacing=0,
                )
            ),

            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )