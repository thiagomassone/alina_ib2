"""Componentes de UI reutilizables compartidos entre todas las vistas de ALINA."""

from __future__ import annotations
import flet as ft
import theme as t


# ── Notificaciones ────────────────────────────────────────────────────────────

def show_snack(page: ft.Page, message: str, bgcolor: str | None = None, color: str | None = None) -> None:
    """Reemplazo de `page.snack_bar = ft.SnackBar(...); page.snack_bar.open = True`.

    Ese patrón (deprecado en Flet 0.24, se saca en 0.26) cuelga el SnackBar de
    un slot del Scaffold que queda TAPADO por cualquier modal — por ejemplo el
    BottomSheet de "Estado del dispositivo" en Resumen: si el sheet está
    abierto, el snackbar se sigue disparando pero no se ve, queda atrás.

    Esta versión usa `page.overlay`, el mismo mecanismo con el que se agregan
    los sheets modales, y siempre se reinserta al FINAL de esa lista antes de
    abrirse — así queda por encima de cualquier sheet que se haya agregado
    después (los sheets también son reordenados al reabrirse, ver
    resumen_view.py), sin importar cuál se agregó primero.
    """
    snack = getattr(page, "_snack", None)
    if snack is None:
        snack = ft.SnackBar(content=ft.Text(""), open=False)
        page._snack = snack
    elif snack in page.overlay:
        page.overlay.remove(snack)
    page.overlay.append(snack)

    snack.content = ft.Text(message, color=color or t.CARD)
    snack.bgcolor = bgcolor or t.NAVY
    snack.open = True
    try:
        page.update()
    except Exception:
        pass


# ── Logo ─────────────────────────────────────────────────────────────────────

def alina_logo_mark(size: int = 32) -> ft.Control:
    import base64
    s = size
    # Triángulo sin base + 4 círculos teal apilados
    cx = s / 2
    # Triángulo: vértice arriba, dos lados sin base
    tip_x, tip_y = cx, s * 0.05
    left_x, left_y = s * 0.05, s * 0.92
    right_x, right_y = s * 0.95, s * 0.92
    stroke = max(1.5, s * 0.07)
    # 4 círculos de mayor a menor, centrados, dentro del triángulo
    circle_cx = cx
    radii = [s * 0.13, s * 0.10, s * 0.08, s * 0.06]
    total_h = sum(r * 2 for r in radii) + s * 0.04 * 3
    start_y = s * 0.28
    circles_svg = ""
    y = start_y
    for r in radii:
        y += r
        circles_svg += f'<circle cx="{circle_cx:.1f}" cy="{y:.1f}" r="{r:.1f}" fill="#03A097"/>'
        y += r + s * 0.04

    svg = f"""<svg viewBox="0 0 {s} {s}" xmlns="http://www.w3.org/2000/svg">
  <polyline points="{left_x:.1f},{left_y:.1f} {tip_x:.1f},{tip_y:.1f} {right_x:.1f},{right_y:.1f}"
    fill="none" stroke="#1A2E4D" stroke-width="{stroke:.1f}" stroke-linejoin="round" stroke-linecap="round"/>
  {circles_svg}
</svg>"""
    b64 = base64.b64encode(svg.encode()).decode()
    return ft.Image(src_base64=b64, width=size, height=size, fit=ft.ImageFit.CONTAIN)


def alina_logo_lockup(mark_size: int = 22, text_size: int = 14) -> ft.Control:
    return ft.Row(
        [
            alina_logo_mark(mark_size),
            ft.Text("ALINA", size=text_size, weight=ft.FontWeight.W_700, color=t.NAVY),
        ],
        spacing=6,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ── Estructurales ─────────────────────────────────────────────────────────────

def section_header(
    title: str,
    subtitle: str,
    action: ft.Control | None = None,
    badge: ft.Control | None = None,
) -> ft.Control:
    right = action if action is not None else alina_logo_lockup()
    row: list[ft.Control] = [
        ft.Column(
            [
                ft.Text(title, size=22, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                ft.Text(subtitle, size=13, color=t.TEXT_MUTED),
            ],
            spacing=2,
            expand=True,
        ),
    ]
    if badge is not None:
        row.append(badge)
    row.append(right)
    return ft.Row(
        row,
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


def card(content: ft.Control, padding: int = 16) -> ft.Container:
    return ft.Container(
        content=content,
        bgcolor=t.CARD,
        border_radius=14,
        padding=padding,
        shadow=ft.BoxShadow(
            spread_radius=0,
            blur_radius=8,
            color=t.SHADOW,
            offset=ft.Offset(0, 2),
        ),
    )


def card_label(text: str) -> ft.Text:
    return ft.Text(text, size=13, color=t.TEXT_DARK, weight=ft.FontWeight.W_700)


def dot(color: str, size: int = 10) -> ft.Control:
    return ft.Container(width=size, height=size, bgcolor=color, border_radius=size)


def pill(text: str, bgcolor: str, fgcolor: str = "#FFFFFF") -> ft.Control:
    return ft.Container(
        content=ft.Text(text, color=fgcolor, size=12, weight=ft.FontWeight.W_600),
        bgcolor=bgcolor,
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
    )


def divider() -> ft.Container:
    return ft.Container(height=1, bgcolor=t.DIVIDER)


def placeholder_view(label: str, icon) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(icon, color=t.TEAL_SOFT, size=72),
                ft.Container(height=8),
                ft.Text(label, size=18, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
                ft.Text("Próximamente", size=13, color=t.TEXT_MUTED),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
        alignment=ft.alignment.center,
        expand=True,
    )