"""Badge de racha de uso + celebración a pantalla completa (estilo Duolingo).

- RachaBadge: la llama + el número en un pill, al lado del saludo en el header.
  La llama está apagada (gris) en 0 y se prende (ámbar) con racha activa.
- Cuando la racha SUBE un día, se dispara una celebración a pantalla completa:
  oscurece el fondo, muestra la llama grande + el número, tira confeti y se
  cierra sola a los ~2s (o al tocar la pantalla).

Uso:
    badge = RachaBadge(page, value=6)
    section_header("Hola, Thiago", tr("Resumen de hoy"), badge=badge.control)
    ...
    badge.set(6)            # setear sin celebrar (carga inicial)
    badge.animate_to(7)     # setear + celebrar (cuando sube la racha)
"""

from __future__ import annotations

import math
import random
import threading
import time

import flet as ft
import theme as t
from i18n import tr


# ── Config ────────────────────────────────────────────────────────────────────
CONFETTI       = True    # confeti en la celebración
FULLSCREEN     = True     # True = overlay a pantalla completa (Duolingo). False = solo bounce del pill.
AUTO_CLOSE_SEG = 2.0      # segundos que dura la celebración antes de cerrarse sola

_AMBER      = t.NEUTRAL        # "#F59E0B" — llama prendida
_AMBER_DK   = "#854F0B"        # número sobre el pill prendido
_AMBER_TINT = "#FAEEDA"        # fondo del pill prendido
_AMBER_BRD  = "#F6D9A6"        # borde del pill prendido
_OFF        = t.TEXT_LIGHT     # "#9AA4B0" — llama/número apagados
_OFF_BG     = t.CARD           # fondo del pill apagado
_OFF_BRD    = t.DIVIDER        # borde del pill apagado

_SCRIM      = "#0B1020"        # fondo oscuro de la celebración
_WHITE      = "#FFFFFF"
_WHITE_DIM  = "#C7CEDB"


class RachaBadge:
    def __init__(self, page: ft.Page, value: int = 0) -> None:
        self.page = page
        self.value = int(value)

        self._flame = ft.Icon(ft.icons.LOCAL_FIRE_DEPARTMENT, size=18)
        self._count = ft.Text(str(self.value), size=15, weight=ft.FontWeight.W_600)

        self._pill = ft.Container(
            content=ft.Row([self._flame, self._count], spacing=4, tight=True),
            padding=ft.padding.only(left=10, right=12, top=6, bottom=6),
            border_radius=999,
            scale=1.0,
            animate_scale=ft.Animation(430, ft.AnimationCurve.BOUNCE_OUT),
            tooltip=tr("Racha de uso: días seguidos con al menos una sesión"),
        )
        self.control = self._pill
        self._apply(active=self.value > 0)

    # ── API pública ──────────────────────────────────────────────────────────
    def set(self, value: int, animate: bool = False) -> None:
        value = int(value)
        self.value = value
        self._count.value = str(value)
        self._apply(active=value > 0)
        if animate and value > 0:
            self.celebrate(value)
        else:
            self._safe_update()

    def animate_to(self, value: int) -> None:
        self.set(value, animate=True)

    def celebrate(self, value: int | None = None) -> None:
        value = self.value if value is None else int(value)
        # Bounce chico del pill (siempre)
        def bump():
            try:
                self._pill.scale = 1.0
                self._safe_update()
                time.sleep(0.02)
                self._pill.scale = 1.35
                self._safe_update()
                time.sleep(0.42)
                self._pill.scale = 1.0
                self._safe_update()
            except Exception:
                pass
        threading.Thread(target=bump, daemon=True).start()
        # Celebración grande
        if FULLSCREEN:
            _celebrar_pantalla(self.page, value)

    # ── Interno ──────────────────────────────────────────────────────────────
    def _apply(self, active: bool) -> None:
        self._flame.color = _AMBER if active else _OFF
        self._count.color = _AMBER_DK if active else _OFF
        self._pill.bgcolor = _AMBER_TINT if active else _OFF_BG
        self._pill.border = ft.border.all(0.5, _AMBER_BRD if active else _OFF_BRD)

    def _safe_update(self) -> None:
        try:
            self.page.update()
        except Exception:
            pass


# ── Celebración a pantalla completa ───────────────────────────────────────────
def _celebrar_pantalla(page: ft.Page, value: int) -> None:
    """Overlay full-screen: oscurece, llama grande + número, confeti, se cierra sola."""
    try:
        titulo = "¡Arrancó tu racha!" if value <= 1 else f"¡{value} días seguidos!"

        flame = ft.Icon(
            ft.icons.LOCAL_FIRE_DEPARTMENT, size=150, color=_AMBER,
            scale=0.4, opacity=0.0,
            animate_scale=ft.Animation(520, ft.AnimationCurve.BOUNCE_OUT),
            animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
        )
        numero = ft.Text(
            str(value), size=72, weight=ft.FontWeight.W_700, color=_WHITE,
            scale=0.6, opacity=0.0,
            animate_scale=ft.Animation(420, ft.AnimationCurve.BOUNCE_OUT),
            animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
        )
        label = ft.Text(
            titulo, size=18, weight=ft.FontWeight.W_600, color=_WHITE_DIM,
            opacity=0.0, animate_opacity=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        )
        centro = ft.Container(
            content=ft.Column(
                [flame, numero, label],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6, tight=True,
            ),
            alignment=ft.alignment.center,
            expand=True,
        )
        stack = ft.Stack([centro], expand=True, clip_behavior=ft.ClipBehavior.NONE)

        scrim = ft.Container(
            content=stack,
            bgcolor=_SCRIM,
            opacity=0.0,
            animate_opacity=ft.Animation(260, ft.AnimationCurve.EASE_OUT),
            expand=True,
        )

        done = threading.Event()

        def cerrar(_=None):
            done.set()

        scrim.on_click = cerrar

        page.overlay.append(scrim)
        _upd(page)

        def run():
            try:
                time.sleep(0.03)
                scrim.opacity = 0.86
                flame.opacity = 1.0; flame.scale = 1.0
                numero.opacity = 1.0; numero.scale = 1.0
                label.opacity = 1.0
                _upd(page)
                if CONFETTI:
                    _confeti_full(page, stack)
                done.wait(AUTO_CLOSE_SEG)
                # salida
                scrim.opacity = 0.0
                flame.opacity = 0.0
                numero.opacity = 0.0
                label.opacity = 0.0
                _upd(page)
                time.sleep(0.30)
                if scrim in page.overlay:
                    page.overlay.remove(scrim)
                    _upd(page)
            except Exception:
                try:
                    if scrim in page.overlay:
                        page.overlay.remove(scrim)
                        _upd(page)
                except Exception:
                    pass

        threading.Thread(target=run, daemon=True).start()
    except Exception:
        pass


def _confeti_full(page: ft.Page, stack: ft.Stack) -> None:
    try:
        w = page.width or 420
        h = page.height or 820
        cx, cy = w / 2, h / 2 - 40
        cols = [_AMBER, "#EF9F27", "#03A097", "#5DCAA5", _WHITE, "#F6D9A6"]
        parts: list[ft.Container] = []
        for i in range(28):
            p = ft.Container(
                width=9, height=9, bgcolor=cols[i % len(cols)],
                border_radius=2, left=cx, top=cy, opacity=1.0,
                rotate=ft.Rotate(0),
                animate_position=ft.Animation(1000, ft.AnimationCurve.DECELERATE),
                animate_opacity=ft.Animation(1000, ft.AnimationCurve.EASE_OUT),
                animate_rotation=ft.Animation(1000, ft.AnimationCurve.DECELERATE),
            )
            parts.append(p)
        stack.controls.extend(parts)
        _upd(page)

        def fly():
            time.sleep(0.03)
            for p in parts:
                ang = random.uniform(0, 2 * math.pi)
                dist = random.uniform(120, 340)
                p.left = cx + math.cos(ang) * dist
                p.top = cy + math.sin(ang) * dist + random.uniform(20, 120)  # gravedad
                p.opacity = 0.0
                p.rotate = ft.Rotate(random.uniform(-6, 6))
            _upd(page)
            time.sleep(1.2)
            for p in parts:
                if p in stack.controls:
                    stack.controls.remove(p)
            _upd(page)

        threading.Thread(target=fly, daemon=True).start()
    except Exception:
        pass


def _upd(page: ft.Page) -> None:
    try:
        page.update()
    except Exception:
        pass
