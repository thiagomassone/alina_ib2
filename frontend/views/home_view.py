"""Shell de ALINA — NavigationBar + router entre tabs + timer global de refresh."""

from __future__ import annotations
import threading
import flet as ft
import theme as t
from ws_client import ALINAWebSocket

from .resumen_view   import resumen_view
from .en_vivo_view   import en_vivo_view
from .historial_view import historial_view
from .analisis_view  import analisis_view
from .alertas_view   import alertas_view
from .perfil_view    import perfil_view

_TABS = [
    resumen_view,
    en_vivo_view,
    historial_view,
    analisis_view,
    alertas_view,
    perfil_view,
]

# Tabs que tienen refresh automático (índices)
_REFRESHABLE_TABS = {0, 1}  # Resumen, En vivo (Análisis sigue siendo placeholder)
_REFRESH_INTERVAL = 3  # segundos


def home_view(page: ft.Page) -> ft.View:
    page.bgcolor = t.BG

    # ── WebSocket compartido — se crea UNA sola vez acá, así siempre existe
    # cuando cualquier tab se construye (antes se creaba recién al tocar
    # "Conectar" desde Resumen, y para ese entonces home_view ya había
    # intentado registrar sus listeners sobre un ws_client que todavía
    # no existía — se perdían para siempre). connect() no se llama todavía,
    # solo instanciamos el cliente.
    if not hasattr(page, "ws_client") or page.ws_client is None:
        page.ws_client = ALINAWebSocket()

    # Aviso de desconexión → notificación (el backend hace debounce de 10 min).
    def _on_ws_disconnect_notif():
        try:
            page.api.notify_device_disconnected()
        except Exception:
            pass
    try:
        page.ws_client.clear_listeners("home_notif")
        page.ws_client.add_listener("disconnect", _on_ws_disconnect_notif, owner="home_notif")
    except Exception:
        pass

    current_tab = [0]
    current_view = [None]  # Control activo con método refresh()
    timer_running = [True]

    content = ft.Container(
        padding=ft.padding.only(left=16, right=16, top=20, bottom=0),
        expand=True,
    )

    def _build_tab(index: int):
        # Si el sheet de dispositivo (Resumen) había quedado abierto, cerrarlo
        # antes de cambiar de tab — vive en page.overlay, que es global, así
        # que si no se cierra queda flotando arriba de la tab nueva.
        old_sheet = getattr(page, "_device_sheet", None)
        if old_sheet is not None and old_sheet.open:
            old_sheet.open = False

        view = _TABS[index](page)
        current_view[0] = view
        content.content = view

        ws = page.ws_client

        if index == 0:
            page._resumen_ctrl = view  # guardar ref global al resumen

            # Sacar los listeners que había dejado esta misma tab la vez
            # anterior, para no ir acumulando duplicados.
            ws.clear_listeners("home_resumen")

            def _ws_connect():
                if hasattr(page, "_resumen_ctrl") and hasattr(page._resumen_ctrl, "on_device_change"):
                    page._resumen_ctrl.on_device_change(connected=True)

            def _ws_disconnect():
                if hasattr(page, "_resumen_ctrl") and hasattr(page._resumen_ctrl, "on_device_change"):
                    page._resumen_ctrl.on_device_change(connected=False)

            ws.add_listener("connect",    _ws_connect,    owner="home_resumen")
            ws.add_listener("disconnect", _ws_disconnect, owner="home_resumen")

            # Si ya estaba conectado de antes (volviste a esta tab), reflejarlo
            # ya mismo en vez de esperar al próximo evento o al polling.
            if ws.connected:
                _ws_connect()

        if index == 2:
            page._historial_ctrl = view  # guardar ref global al historial

        if index == 1:
            # En vivo notifica al resumen e historial cuando guarda una sesión
            def _notify_all():
                if hasattr(page, "_resumen_ctrl") and hasattr(page._resumen_ctrl, "on_session_saved"):
                    page._resumen_ctrl.on_session_saved()
                if hasattr(page, "_historial_ctrl") and hasattr(page._historial_ctrl, "refresh"):
                    page._historial_ctrl.refresh()
            if hasattr(view, "on_session_saved"):
                view.on_session_saved = _notify_all

            # En vivo notifica al resumen cuando llega una alerta del ESP
            def _notify_alert():
                if hasattr(page, "_resumen_ctrl") and hasattr(page._resumen_ctrl, "on_alert_received"):
                    page._resumen_ctrl.on_alert_received()
            if hasattr(view, "on_alert_relay"):
                view.on_alert_relay = _notify_alert

        page.update()

    def _refresh_badge():
        """Actualiza el contador de notificaciones sin ver en el nav (Alertas)."""
        try:
            n = page.api.get_unread_count()
        except Exception:
            return
        try:
            _badge_text.value = str(n)
            _badge_cont.visible = n > 0
            page.update()
        except Exception:
            pass

    def _refresh_loop():
        threading.Event().wait(1)  # primer refresh al segundo de cargar
        while timer_running[0]:
            if current_tab[0] in _REFRESHABLE_TABS:
                ctrl = current_view[0]
                if ctrl and hasattr(ctrl, "refresh"):
                    try:
                        ctrl.refresh()
                        page.update()
                    except Exception:
                        pass
            if current_tab[0] != 4:
                _refresh_badge()
            threading.Event().wait(_REFRESH_INTERVAL)

    def on_nav_change(e: ft.ControlEvent):
        idx = e.control.selected_index
        current_tab[0] = idx
        _build_tab(idx)
        if idx == 4:
            # Al abrir Alertas: marcar todo como visto y limpiar el badge.
            try:
                page.api.mark_all_notifications_read()
            except Exception:
                pass
            try:
                _badge_cont.visible = False
                page.update()
            except Exception:
                pass
        else:
            _refresh_badge()

    # Iniciar tab inicial y timer
    _build_tab(0)
    threading.Thread(target=_refresh_loop, daemon=True).start()

    try:
        _n0 = page.api.get_unread_count()
    except Exception:
        _n0 = 0

    # Badge del nav hecho a mano (ícono + puntito rojo) para no depender de la
    # prop `badge` del NavigationBarDestination, que no existe en Flet viejo.
    _badge_text = ft.Text(str(_n0), size=9, color=t.CARD, weight=ft.FontWeight.W_700)
    _badge_cont = ft.Container(
        content=_badge_text,
        bgcolor=t.BAD, border_radius=8,
        padding=ft.padding.symmetric(horizontal=5, vertical=1),
        right=0, top=0, visible=_n0 > 0,
    )
    _alertas_icon = ft.Stack(
        [
            ft.Container(ft.Icon(ft.icons.NOTIFICATIONS_NONE), width=28, height=28,
                         alignment=ft.alignment.center),
            _badge_cont,
        ],
        width=30, height=28, clip_behavior=ft.ClipBehavior.NONE,
    )

    nav = ft.NavigationBar(
        selected_index=0,
        bgcolor=t.CARD,
        indicator_color=t.TEAL_SOFT,
        on_change=on_nav_change,
        destinations=[
            ft.NavigationBarDestination(icon=ft.icons.HOME_OUTLINED,             selected_icon=ft.icons.HOME,              label="Resumen"),
            ft.NavigationBarDestination(icon=ft.icons.ACCESSIBILITY_NEW_OUTLINED, selected_icon=ft.icons.ACCESSIBILITY_NEW, label="En vivo"),
            ft.NavigationBarDestination(icon=ft.icons.HISTORY,                   label="Historial"),
            ft.NavigationBarDestination(icon=ft.icons.INSIGHTS_OUTLINED,         selected_icon=ft.icons.INSIGHTS,           label="Análisis"),
            ft.NavigationBarDestination(icon_content=_alertas_icon, label="Alertas"),
            ft.NavigationBarDestination(icon=ft.icons.PERSON_OUTLINE,            selected_icon=ft.icons.PERSON,             label="Perfil"),
        ],
    )

    view = ft.View(
        route="/",
        bgcolor=t.BG,
        padding=0,
        navigation_bar=nav,
        controls=[content],
    )
    return view