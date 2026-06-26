"""Tab 4 — Alertas: hub de notificaciones del sistema."""

from __future__ import annotations
from datetime import datetime
import flet as ft
import theme as t
from .components import card, card_label, divider, section_header

# ── Iconos y colores por tipo de notificación ─────────────────────────────────

_TIPO_META = {
    "session_score_low":   (ft.icons.FITNESS_CENTER,       t.NEUTRAL, "Sesión"),
    "device_disconnected": (ft.icons.SENSORS_OFF,          t.BAD,     "Dispositivo"),
    "haptic_alert":        (ft.icons.VIBRATION,            t.NEUTRAL, "Alerta háptica"),
    "password_changed":    (ft.icons.LOCK_OUTLINED,        t.GOOD,    "Cuenta"),
    "calibration_pending": (ft.icons.TUNE,                 t.NEUTRAL, "Dispositivo"),
}
_DEFAULT_META = (ft.icons.NOTIFICATIONS_OUTLINED, t.TEXT_MUTED, "Sistema")


def _fmt_fecha(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        now = datetime.now()
        diff = now - dt
        if diff.days == 0:
            h = diff.seconds // 3600
            if h == 0:
                m = diff.seconds // 60
                return f"Hace {m} min" if m > 0 else "Ahora"
            return f"Hace {h}h"
        elif diff.days == 1:
            return "Ayer"
        elif diff.days < 7:
            return f"Hace {diff.days} días"
        else:
            return dt.strftime("%d/%m/%Y")
    except Exception:
        return ""


def _notif_row(notif: dict, on_mark_read, last: bool = False) -> ft.Control:
    icon, color, categoria = _TIPO_META.get(notif["tipo"], _DEFAULT_META)
    leida = notif["leida"]

    def tap(_):
        if not notif["leida"]:
            on_mark_read(notif["id"])

    row = ft.GestureDetector(
        on_tap=tap,
        content=ft.Column(
            [
                ft.Row(
                    [
                        # Ícono con fondo
                        ft.Container(
                            content=ft.Icon(icon, color=color, size=20),
                            width=40, height=40,
                            bgcolor=f"{color}18",
                            border_radius=10,
                            alignment=ft.alignment.center,
                        ),
                        # Contenido
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            notif["titulo"],
                                            size=13,
                                            weight=ft.FontWeight.W_600 if not leida else ft.FontWeight.W_400,
                                            color=t.TEXT_DARK,
                                            expand=True,
                                        ),
                                        ft.Text(
                                            _fmt_fecha(notif["created_at"]),
                                            size=11,
                                            color=t.TEXT_LIGHT,
                                        ),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                                ft.Text(
                                    notif["mensaje"],
                                    size=12,
                                    color=t.TEXT_MUTED,
                                    max_lines=2,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                ft.Text(
                                    categoria,
                                    size=10,
                                    color=color,
                                    weight=ft.FontWeight.W_600,
                                ),
                            ],
                            spacing=2,
                            expand=True,
                        ),
                        # Punto de no leída
                        ft.Container(
                            width=8, height=8,
                            bgcolor=t.TEAL,
                            border_radius=4,
                            visible=not leida,
                        ),
                    ],
                    spacing=12,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                ),
            ] + ([] if last else [ft.Container(height=8), divider(), ft.Container(height=8)]),
            spacing=0,
        ),
    )
    return row


def alertas_view(page: ft.Page) -> ft.Control:
    # ── Cargar notificaciones ─────────────────────────────────────────────────
    try:
        notifs = page.api.get_notifications(limit=50)
    except Exception:
        notifs = []

    unread = sum(1 for n in notifs if not n["leida"])

    # ── Controles reactivos ───────────────────────────────────────────────────
    list_col   = ft.Ref[ft.Column]()
    badge_text = ft.Ref[ft.Text]()
    badge_cont = ft.Ref[ft.Container]()
    empty_cont = ft.Ref[ft.Container]()

    def mark_read(notif_id: int):
        try:
            page.api.mark_notification_read(notif_id)
        except Exception:
            pass
        # Actualizar localmente sin recargar
        for n in notifs:
            if n["id"] == notif_id:
                n["leida"] = True
        _rebuild_list()
        page.update()

    def mark_all(_):
        try:
            page.api.mark_all_notifications_read()
        except Exception:
            pass
        for n in notifs:
            n["leida"] = True
        _rebuild_list()
        page.update()

    def _rebuild_list():
        nonlocal unread
        unread = sum(1 for n in notifs if not n["leida"])
        badge_text.current.value = str(unread)
        badge_cont.current.visible = unread > 0
        empty_cont.current.visible = len(notifs) == 0
        list_col.current.controls = (
            [_notif_row(n, mark_read, last=(i == len(notifs) - 1)) for i, n in enumerate(notifs)]
            if notifs else []
        )

    # ── Construir lista inicial ───────────────────────────────────────────────
    initial_rows = (
        [_notif_row(n, mark_read, last=(i == len(notifs) - 1)) for i, n in enumerate(notifs)]
        if notifs else []
    )

    return ft.Column(
        [
            section_header(
                "Alertas",
                "Notificaciones del sistema",
                action=ft.Row(
                    [
                        ft.Container(
                            ref=badge_cont,
                            content=ft.Text(ref=badge_text, value=str(unread), size=11, color=t.CARD, weight=ft.FontWeight.W_700),
                            bgcolor=t.BAD,
                            border_radius=10,
                            padding=ft.padding.symmetric(horizontal=7, vertical=2),
                            visible=unread > 0,
                        ),
                    ],
                    spacing=6,
                ),
            ),
            ft.Container(height=10),

            # Botón "Marcar todas como leídas"
            ft.Container(
                content=ft.TextButton(
                    "Marcar todas como leídas",
                    icon=ft.icons.DONE_ALL,
                    on_click=mark_all,
                    style=ft.ButtonStyle(color=t.TEAL),
                ),
                alignment=ft.alignment.center_right,
                visible=unread > 0,
            ),

            # Lista de notificaciones
            card(
                ft.Column(
                    [
                        card_label("Recientes"),
                        ft.Container(height=8),
                        ft.Column(
                            ref=list_col,
                            controls=initial_rows,
                            spacing=0,
                        ),
                        # Estado vacío
                        ft.Container(
                            ref=empty_cont,
                            content=ft.Column(
                                [
                                    ft.Icon(ft.icons.NOTIFICATIONS_NONE, color=t.TEAL_SOFT, size=48),
                                    ft.Container(height=8),
                                    ft.Text("Sin notificaciones", size=14, color=t.TEXT_MUTED, weight=ft.FontWeight.W_500),
                                    ft.Text("Todo en orden por acá", size=12, color=t.TEXT_LIGHT),
                                ],
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                alignment=ft.MainAxisAlignment.CENTER,
                                spacing=4,
                            ),
                            alignment=ft.alignment.center,
                            padding=ft.padding.symmetric(vertical=32),
                            visible=len(notifs) == 0,
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