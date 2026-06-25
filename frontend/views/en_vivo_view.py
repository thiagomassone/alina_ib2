"""Tab 1 — En vivo: visualización en tiempo real + control de sesión."""

from __future__ import annotations
import time
import threading
from datetime import datetime
import flet as ft
import theme as t
from .components import card, card_label, section_header


# ─── SVG de espalda con IMUs ─────────────────────────────────────────────────

def _imu_status_color(status: str) -> str:
    return {
        "listo":     t.GOOD,
        "calibrar":  t.NEUTRAL,
        "desconectado": t.BAD,
    }.get(status, t.BAD)


def _back_svg_widget(imu_states: dict[str, str]) -> ft.Control:
    """Renderiza el SVG de la espalda usando ft.Image con SVG embebido."""
    pelvis_color   = _imu_status_color(imu_states.get("pelvis", "desconectado"))
    dorsal_color   = _imu_status_color(imu_states.get("dorsal_medio", "desconectado"))
    superior_color = _imu_status_color(imu_states.get("dorsal_superior", "desconectado"))

    import base64
    svg = f"""<svg viewBox="0 0 200 340" xmlns="http://www.w3.org/2000/svg">
  <ellipse cx="100" cy="28" rx="22" ry="26" fill="#D9E3EE"/>
  <rect x="90" y="50" width="20" height="18" rx="4" fill="#D9E3EE"/>
  <path d="M100 60 Q78 60 64 68 Q48 78 46 100 Q44 124 50 150 Q50 180 58 210 Q68 230 100 232 Q132 230 142 210 Q150 180 150 150 Q156 124 154 100 Q152 78 136 68 Q122 60 100 60Z" fill="#D9E3EE"/>
  <path d="M44 88 Q36 120 38 155 Q40 168 48 172 Q56 176 60 164 Q66 140 68 110 Q64 92 56 86Z" fill="#D9E3EE"/>
  <path d="M156 88 Q164 120 162 155 Q160 168 152 172 Q144 176 140 164 Q134 140 132 110 Q136 92 144 86Z" fill="#D9E3EE"/>
  <path d="M60 210 Q58 235 65 248 Q80 258 100 258 Q120 258 135 248 Q142 235 140 210Z" fill="#C8D6E8"/>
  <line x1="100" y1="68" x2="100" y2="228" stroke="#B0C4D8" stroke-width="2.5" stroke-dasharray="5,4"/>
  <!-- IMU Superior -->
  <circle cx="100" cy="88"  r="16" fill="{superior_color}" opacity="0.2"/>
  <circle cx="100" cy="88"  r="9"  fill="{superior_color}"/>
  <circle cx="100" cy="88"  r="4"  fill="white" opacity="0.7"/>
  <!-- IMU Dorsal -->
  <circle cx="100" cy="148" r="16" fill="{dorsal_color}" opacity="0.2"/>
  <circle cx="100" cy="148" r="9"  fill="{dorsal_color}"/>
  <circle cx="100" cy="148" r="4"  fill="white" opacity="0.7"/>
  <!-- IMU Pelvis -->
  <circle cx="100" cy="215" r="16" fill="{pelvis_color}" opacity="0.2"/>
  <circle cx="100" cy="215" r="9"  fill="{pelvis_color}"/>
  <circle cx="100" cy="215" r="4"  fill="white" opacity="0.7"/>
  <!-- Etiquetas -->
</svg>"""

    svg_b64 = base64.b64encode(svg.encode()).decode()
    return ft.Image(
        src_base64=svg_b64,
        width=200,
        height=340,
        fit=ft.ImageFit.CONTAIN,
    )


# ─── Leyenda de estados ───────────────────────────────────────────────────────

def _legend_item(color: str, label: str) -> ft.Control:
    return ft.Row(
        [
            ft.Container(width=10, height=10, bgcolor=color, border_radius=10),
            ft.Text(label, size=11, color=t.TEXT_MUTED),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ─── Entry point ─────────────────────────────────────────────────────────────

def en_vivo_view(page: ft.Page) -> ft.Control:
    # Estado mockeado de los IMUs — TODO: reemplazar con datos del WebSocket/BLE
    imu_states = {
        "dorsal_superior": "listo",
        "dorsal_medio":    "listo",
        "pelvis":          "listo",
    }

    # Estado de la sesión
    session_active  = False
    session_paused  = False
    session_start   = None
    elapsed_seconds = 0

    # Controles reactivos
    timer_text  = ft.Text("00:00", size=32, weight=ft.FontWeight.W_700, color=t.TEXT_DARK)
    status_text = ft.Text("Sin sesión activa", size=13, color=t.TEXT_MUTED)

    start_btn  = ft.FilledButton(
        "Iniciar sesión",
        icon=ft.icons.PLAY_ARROW,
        style=ft.ButtonStyle(bgcolor=t.TEAL, color=t.CARD),
        expand=True,
    )
    pause_btn  = ft.FilledButton(
        "Pausar",
        icon=ft.icons.PAUSE,
        style=ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.CARD),
        expand=True,
        visible=False,
    )
    stop_btn   = ft.OutlinedButton(
        "Finalizar",
        icon=ft.icons.STOP,
        style=ft.ButtonStyle(
            color=t.BAD,
            side=ft.BorderSide(1, t.BAD),
            shape=ft.RoundedRectangleBorder(radius=8),
        ),
        expand=True,
        visible=False,
    )

    timer_running = [False]

    def _fmt_time(secs: int) -> str:
        h = secs // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"

    def _tick():
        nonlocal elapsed_seconds
        while timer_running[0]:
            time.sleep(1)
            if timer_running[0] and not session_paused:
                elapsed_seconds += 1
                timer_text.value = _fmt_time(elapsed_seconds)
                try:
                    page.update()
                except Exception:
                    break

    def start_session(_):
        nonlocal session_active, session_paused, session_start, elapsed_seconds
        session_active  = True
        session_paused  = False
        session_start   = datetime.now()
        elapsed_seconds = 0

        start_btn.visible  = False
        pause_btn.visible  = True
        stop_btn.visible   = True
        status_text.value  = "Sesión en curso"
        status_text.color  = t.GOOD
        timer_text.value   = "00:00"

        timer_running[0] = True
        threading.Thread(target=_tick, daemon=True).start()
        page.update()

    def toggle_pause(_):
        nonlocal session_paused
        session_paused = not session_paused
        if session_paused:
            pause_btn.text  = "Reanudar"
            pause_btn.icon  = ft.icons.PLAY_ARROW
            pause_btn.style = ft.ButtonStyle(bgcolor=t.GOOD, color=t.CARD)
            status_text.value = "Sesión pausada"
            status_text.color = t.NEUTRAL
        else:
            pause_btn.text  = "Pausar"
            pause_btn.icon  = ft.icons.PAUSE
            pause_btn.style = ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.CARD)
            status_text.value = "Sesión en curso"
            status_text.color = t.GOOD
        page.update()

    def stop_session(_):
        nonlocal session_active, session_paused, elapsed_seconds
        timer_running[0] = False
        session_active   = False
        session_paused   = False

        start_btn.visible  = True
        pause_btn.visible  = False
        stop_btn.visible   = False
        pause_btn.text     = "Pausar"
        pause_btn.icon     = ft.icons.PAUSE
        pause_btn.style    = ft.ButtonStyle(bgcolor=t.NEUTRAL, color=t.CARD)
        status_text.value  = "Sin sesión activa"
        status_text.color  = t.TEXT_MUTED
        timer_text.value   = "00:00"

        # TODO: enviar resumen al backend vía api.create_session(...)
        # duracion_min = elapsed_seconds / 60
        # alertas_hapticas = contadas por el ESP32

        page.snack_bar = ft.SnackBar(
            ft.Text("Sesión finalizada — datos guardados al conectar el dispositivo", color=t.CARD),
            bgcolor=t.NAVY,
        )
        page.snack_bar.open = True
        elapsed_seconds = 0
        page.update()

    start_btn.on_click  = start_session
    pause_btn.on_click  = toggle_pause
    stop_btn.on_click   = stop_session

    return ft.Column(
        [
            section_header("En vivo", "Estado del dispositivo"),
            ft.Container(height=10),

            # ── Diagrama + leyenda ────────────────────────────────────────────
            card(
                ft.Column(
                    [
                        card_label("IMUs"),
                        ft.Container(height=8),
                        ft.Row(
                            [
                                # SVG centrado
                                ft.Container(
                                    content=_back_svg_widget(imu_states),
                                    expand=True,
                                    alignment=ft.alignment.center,
                                ),
                                # Leyenda a la derecha
                                ft.Column(
                                    [
                                        ft.Text("Estado", size=11, color=t.TEXT_MUTED, weight=ft.FontWeight.W_600),
                                        ft.Container(height=6),
                                        _legend_item(t.GOOD,    "Listo"),
                                        _legend_item(t.NEUTRAL, "Pendiente de calibrar"),
                                        _legend_item(t.BAD,     "Desconectado"),
                                        ft.Container(height=16),
                                        ft.Text("* Datos mockeados", size=9, color=t.TEXT_LIGHT),
                                        ft.Text("hasta conectar ESP32", size=9, color=t.TEXT_LIGHT),
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

            # ── Timer de sesión ───────────────────────────────────────────────
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
                                    spacing=2,
                                    expand=True,
                                ),
                                ft.Icon(ft.icons.TIMER_OUTLINED, color=t.TEAL_SOFT, size=40),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=12),
                        ft.Row(
                            [start_btn, pause_btn, stop_btn],
                            spacing=8,
                        ),
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