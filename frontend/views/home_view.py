"""Shell de ALINA — NavigationBar + router entre tabs."""

from __future__ import annotations
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


def home_view(page: ft.Page) -> ft.View:
    page.bgcolor = t.BG

    content = ft.Container(
        content=resumen_view(page),
        padding=ft.padding.only(left=16, right=16, top=20, bottom=0),
        expand=True,
    )

    def on_nav_change(e: ft.ControlEvent):
        content.content = _TABS[e.control.selected_index](page)
        page.update()

    nav = ft.NavigationBar(
        selected_index=0,
        bgcolor=t.CARD,
        indicator_color=t.TEAL_SOFT,
        on_change=on_nav_change,
        destinations=[
            ft.NavigationBarDestination(icon=ft.icons.HOME_OUTLINED,            selected_icon=ft.icons.HOME,              label="Resumen"),
            ft.NavigationBarDestination(icon=ft.icons.ACCESSIBILITY_NEW_OUTLINED, selected_icon=ft.icons.ACCESSIBILITY_NEW, label="En vivo"),
            ft.NavigationBarDestination(icon=ft.icons.HISTORY,                  label="Historial"),
            ft.NavigationBarDestination(icon=ft.icons.INSIGHTS_OUTLINED,        selected_icon=ft.icons.INSIGHTS,           label="Análisis"),
            ft.NavigationBarDestination(icon=ft.icons.NOTIFICATIONS_NONE,       selected_icon=ft.icons.NOTIFICATIONS,      label="Alertas"),
            ft.NavigationBarDestination(icon=ft.icons.PERSON_OUTLINE,           selected_icon=ft.icons.PERSON,             label="Perfil"),
        ],
    )

    return ft.View(
        route="/",
        bgcolor=t.BG,
        padding=0,
        navigation_bar=nav,
        controls=[content],
    )