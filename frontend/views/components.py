"""Componentes de UI reutilizables compartidos entre todas las vistas de ALINA."""

from __future__ import annotations
import flet as ft
import theme as t


# ── Logo ─────────────────────────────────────────────────────────────────────

def alina_logo_mark(size: int = 32) -> ft.Control:
    dot_sizes = [size * 0.28, size * 0.22, size * 0.19, size * 0.16]
    dots = ft.Column(
        [ft.Container(width=s, height=s, bgcolor=t.TEAL, border_radius=s) for s in dot_sizes],
        spacing=max(1, int(size * 0.06)),
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        alignment=ft.MainAxisAlignment.CENTER,
    )
    return ft.Stack(
        [
            ft.Icon(ft.icons.CHANGE_HISTORY, size=size, color=t.NAVY),
            ft.Container(
                content=dots,
                alignment=ft.alignment.center,
                width=size,
                height=size,
                padding=ft.padding.only(top=size * 0.25),
            ),
        ],
        width=size,
        height=size,
    )


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

def section_header(title: str, subtitle: str, action: ft.Control | None = None) -> ft.Control:
    right = action if action is not None else alina_logo_lockup()
    return ft.Row(
        [
            ft.Column(
                [
                    ft.Text(title, size=22, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                    ft.Text(subtitle, size=13, color=t.TEXT_MUTED),
                ],
                spacing=2,
                expand=True,
            ),
            right,
        ],
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