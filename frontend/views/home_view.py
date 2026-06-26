"""Shell de ALINA — NavigationBar + router entre tabs + timer global de refresh."""

from __future__ import annotations
import threading
import flet as ft
import theme as t

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
_REFRESHABLE_TABS = {0, 1}  # Resumen, En vivo
_REFRESH_INTERVAL = 3  # segundos


def home_view(page: ft.Page) -> ft.View:
    page.bgcolor = t.BG

    current_tab = [0]
    current_view = [None]  # Control activo con método refresh()
    timer_running = [True]

    content = ft.Container(
        padding=ft.padding.only(left=16, right=16, top=20, bottom=0),
        expand=True,
    )

    def _build_tab(index: int):
        view = _TABS[index](page)
        current_view[0] = view
        content.content = view

        # Registrar callbacks del WS en resumen y en_vivo
        ws = getattr(page, "ws_client", None)
        resumen = current_view[0] if index == 0 else getattr(page, "_resumen_ctrl", None)

        if index == 0:
            page._resumen_ctrl = view  # guardar ref global al resumen
            if ws:
                def _ws_connect():
                    if hasattr(page, "_resumen_ctrl") and hasattr(page._resumen_ctrl, "on_device_change"):
                        page._resumen_ctrl.on_device_change(connected=True)
                def _ws_disconnect():
                    if hasattr(page, "_resumen_ctrl") and hasattr(page._resumen_ctrl, "on_device_change"):
                        page._resumen_ctrl.on_device_change(connected=False)
                ws.on_connect    = _ws_connect
                ws.on_disconnect = _ws_disconnect

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
                
        # if index == 1:
        #     # En vivo notifica al resumen e historial cuando guarda una sesión
        #     def _notify_all():
        #         if hasattr(page, "_resumen_ctrl") and hasattr(page._resumen_ctrl, "on_session_saved"):
        #             page._resumen_ctrl.on_session_saved()
        #         if hasattr(page, "_historial_ctrl") and hasattr(page._historial_ctrl, "refresh"):
        #             page._historial_ctrl.refresh()
        #     if hasattr(view, "on_session_saved"):
        #         view.on_session_saved = _notify_all

        page.update()

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
            threading.Event().wait(_REFRESH_INTERVAL)

    def on_nav_change(e: ft.ControlEvent):
        current_tab[0] = e.control.selected_index
        _build_tab(current_tab[0])

    # Iniciar tab inicial y timer
    _build_tab(0)
    threading.Thread(target=_refresh_loop, daemon=True).start()

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
            ft.NavigationBarDestination(icon=ft.icons.NOTIFICATIONS_NONE,        selected_icon=ft.icons.NOTIFICATIONS,      label="Alertas"),
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