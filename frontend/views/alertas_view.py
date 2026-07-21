"""Tab Alertas — hub de notificaciones.

- Sin botón "visto": al abrir el tab se marcan todas como vistas (limpia el
  badge del nav). El contador vive en la barra inferior (ver home_view).
- Borrado manual: deslizá una notificación hacia la derecha → "Borrar".
- Las notificaciones tienen tiempo de vida (TTL de 3 días, lo maneja el backend).
"""

from __future__ import annotations
from datetime import datetime
import flet as ft
import theme as t
from i18n import tr
from .components import section_header

# ── Iconos y colores por tipo ─────────────────────────────────────────────────
_TIPO_META = {
    "session_score_low":   (ft.icons.FITNESS_CENTER,        t.NEUTRAL, "Sesión"),
    "buena_sesion":        (ft.icons.THUMB_UP_OUTLINED,     t.GOOD,    "Sesión"),
    "nuevo_record":        (ft.icons.EMOJI_EVENTS_OUTLINED, t.NEUTRAL, "Récord"),
    "racha_en_riesgo":     (ft.icons.LOCAL_FIRE_DEPARTMENT, t.NEUTRAL, "Racha"),
    "resumen_semanal":     (ft.icons.INSIGHTS,              t.TEAL,    "Semanal"),
    "device_disconnected": (ft.icons.SENSORS_OFF,           t.BAD,     "Dispositivo"),
    "calibration_pending": (ft.icons.TUNE,                  t.NEUTRAL, "Dispositivo"),
    "password_changed":    (ft.icons.LOCK_OUTLINED,         t.GOOD,    "Cuenta"),
}
_DEFAULT_META = (ft.icons.NOTIFICATIONS_OUTLINED, t.TEXT_MUTED, "Sistema")


def _fmt_fecha(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso)
        diff = datetime.now() - dt
        if diff.days == 0:
            h = diff.seconds // 3600
            if h == 0:
                m = diff.seconds // 60
                return f"Hace {m} min" if m > 0 else "Ahora"
            return f"Hace {h}h"
        if diff.days == 1:
            return "Ayer"
        if diff.days < 7:
            return f"Hace {diff.days} días"
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return ""


def _notif_card(notif: dict) -> ft.Control:
    icon, color, categoria = _TIPO_META.get(notif["tipo"], _DEFAULT_META)
    return ft.Container(
        bgcolor=t.CARD, border_radius=12, padding=14,
        content=ft.Row(
            [
                ft.Container(
                    content=ft.Icon(icon, color=color, size=20),
                    width=40, height=40, bgcolor=f"{color}18",
                    border_radius=10, alignment=ft.alignment.center,
                ),
                ft.Column(
                    [
                        ft.Row(
                            [ft.Text(tr(notif["titulo"]), size=13, weight=ft.FontWeight.W_600,
                                     color=t.TEXT_DARK, expand=True),
                             ft.Text(_fmt_fecha(notif["created_at"]), size=11, color=t.TEXT_LIGHT)],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Text(notif["mensaje"], size=12, color=t.TEXT_MUTED,
                                max_lines=3, overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(tr(categoria), size=10, color=color, weight=ft.FontWeight.W_600),
                    ],
                    spacing=2, expand=True,
                ),
            ],
            spacing=12, vertical_alignment=ft.CrossAxisAlignment.START,
        ),
    )


def _swipe_bg() -> ft.Control:
    return ft.Container(
        bgcolor=t.BAD, border_radius=12, padding=ft.padding.only(left=20),
        alignment=ft.alignment.center_left,
        content=ft.Row(
            [ft.Icon(ft.icons.DELETE_OUTLINE, color=t.ON_COLOR, size=20),
             ft.Text(tr("Borrar"), color=t.ON_COLOR, size=13, weight=ft.FontWeight.W_600)],
            spacing=8, tight=True,
        ),
    )


def alertas_view(page: ft.Page) -> ft.Control:
    try:
        notifs = page.api.get_notifications(limit=50)
    except Exception:
        notifs = []

    # Al abrir el tab, marcar todo como visto → limpia el badge del nav.
    try:
        page.api.mark_all_notifications_read()
    except Exception:
        pass

    list_col   = ft.Ref[ft.Column]()
    empty_cont = ft.Ref[ft.Container]()

    def _on_delete(nid: int):
        try:
            page.api.delete_notification(nid)
        except Exception:
            pass
        notifs[:] = [n for n in notifs if n["id"] != nid]
        if empty_cont.current is not None:
            empty_cont.current.visible = len(notifs) == 0
        try:
            page.update()
        except Exception:
            pass

    def _dismissible(notif: dict) -> ft.Control:
        return ft.Dismissible(
            key=str(notif["id"]),
            content=_notif_card(notif),
            background=_swipe_bg(),
            dismiss_direction=ft.DismissDirection.START_TO_END,
            dismiss_thresholds={ft.DismissDirection.START_TO_END: 0.4},
            on_dismiss=lambda e, nid=notif["id"]: _on_delete(nid),
        )

    rows = [_dismissible(n) for n in notifs]

    def _rebuild():
        if list_col.current is not None:
            list_col.current.controls = [_dismissible(n) for n in notifs]
        if empty_cont.current is not None:
            empty_cont.current.visible = len(notifs) == 0

    def refresh():
        """Poll periódico: re-dibuja solo si cambió el set de notificaciones.

        No re-marca leídas en cada tick para no parpadear; marca visto una vez,
        al detectar cambios, porque estás mirando la pantalla.
        """
        try:
            nuevas = page.api.get_notifications(limit=50)
        except Exception:
            return
        if {n["id"] for n in nuevas} == {n["id"] for n in notifs}:
            return  # nada nuevo ni borrado → no tocar la UI
        notifs[:] = nuevas
        _rebuild()
        try:
            page.api.mark_all_notifications_read()  # las estás viendo → visto
        except Exception:
            pass
        try:
            page.update()
        except Exception:
            pass

    empty = ft.Container(
        ref=empty_cont,
        content=ft.Column(
            [ft.Icon(ft.icons.NOTIFICATIONS_NONE, color=t.TEAL_SOFT, size=48),
             ft.Container(height=8),
             ft.Text(tr("Sin notificaciones"), size=14, color=t.TEXT_MUTED, weight=ft.FontWeight.W_500),
             ft.Text(tr("Todo en orden por acá"), size=12, color=t.TEXT_LIGHT)],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER, spacing=4,
        ),
        alignment=ft.alignment.center, padding=ft.padding.symmetric(vertical=48),
        visible=len(notifs) == 0,
    )

    col = ft.Column(
        [
            section_header(tr("Alertas"), tr("Notificaciones del sistema")),
            ft.Text(tr("Deslizá una notificación para borrarla."), size=11, color=t.TEXT_LIGHT),
            ft.Container(height=6),
            ft.Column(ref=list_col, controls=rows, spacing=10),
            empty,
            ft.Container(height=12),
        ],
        spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
    )
    col.refresh = refresh  # el timer de home_view lo llama cada 3s
    return col