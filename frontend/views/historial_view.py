"""Tab 2 — Historial: gráfico semanal + sesiones recientes."""

from __future__ import annotations
import flet as ft
import theme as t
from .components import card, card_label, divider, section_header

_WEEKLY_DATA = [
    ("Lun", 72), ("Mar", 68), ("Mié", 75), ("Jue", 80), ("Sáb", 78), ("Dom", 82),
]

_RECENT_SESSIONS = [
    {"fecha": "Hoy, 14:30",  "duracion": "45 min", "score": 83},
    {"fecha": "Hoy, 08:15",  "duracion": "60 min", "score": 76},
    {"fecha": "Ayer, 18:20", "duracion": "35 min", "score": 74},
]


def _score_badge(score: int) -> ft.Control:
    color = t.GOOD if score >= 80 else (t.NEUTRAL if score >= 65 else t.BAD)
    return ft.Container(
        content=ft.Text(str(score), size=13, weight=ft.FontWeight.W_700, color=t.CARD),
        bgcolor=color, border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        width=38, alignment=ft.alignment.center,
    )


def _session_row(session: dict, last: bool = False) -> ft.Control:
    return ft.Column(
        [
            ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text(session["fecha"], size=13, weight=ft.FontWeight.W_500, color=t.TEXT_DARK),
                            ft.Text(session["duracion"], size=12, color=t.TEXT_MUTED),
                        ],
                        spacing=2, expand=True,
                    ),
                    _score_badge(session["score"]),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        ] + ([] if last else [ft.Container(height=2), divider(), ft.Container(height=2)]),
        spacing=0,
    )


def _mini_bar_chart(data: list[tuple[str, int]]) -> ft.Control:
    max_val = max(v for _, v in data) if data else 100
    chart_height = 90
    bars = []
    for label, val in data:
        bar_h = int((val / max_val) * chart_height)
        bars.append(
            ft.Column(
                [
                    ft.Text(str(val), size=9, color=t.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                    ft.Container(
                        content=ft.Container(
                            bgcolor=t.TEAL,
                            border_radius=ft.border_radius.only(top_left=4, top_right=4),
                            height=bar_h, width=28,
                        ),
                        height=chart_height, alignment=ft.alignment.bottom_center,
                    ),
                    ft.Text(label, size=10, color=t.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=4,
            )
        )
    return ft.Row(bars, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.END)


def _period_chip(label: str, selected: bool) -> ft.Container:
    return ft.Container(
        content=ft.Text(
            label,
            size=13,
            weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
            color=t.CARD if selected else t.TEXT_MUTED,
        ),
        bgcolor=t.TEAL if selected else t.CARD,
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=16, vertical=6),
        border=ft.border.all(1, t.TEAL if selected else t.DIVIDER),
    )


def historial_view(page: ft.Page) -> ft.Control:
    return ft.Column(
        [
            section_header("Historial", "Seguimiento de tus sesiones"),
            ft.Container(height=10),
            card(
                ft.Column(
                    [
                        ft.Row([_period_chip("Semana", True), _period_chip("Mes", False), _period_chip("3 meses", False), _period_chip("Año", False)], spacing=8),
                        ft.Container(height=10),
                        ft.Row(
                            [
                                ft.Icon(ft.icons.CHEVRON_LEFT, color=t.TEXT_MUTED, size=20),
                                ft.Row(
                                    [
                                        ft.Icon(ft.icons.CALENDAR_TODAY_OUTLINED, size=14, color=t.TEXT_MUTED),
                                        ft.Text("6 – 12 mayo 2024", size=13, color=t.TEXT_DARK, weight=ft.FontWeight.W_500),
                                    ],
                                    spacing=6,
                                ),
                                ft.Icon(ft.icons.CHEVRON_RIGHT, color=t.TEXT_MUTED, size=20),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Container(height=12),
                        card_label("Puntuación postural"),
                        ft.Container(height=4),
                        ft.Row(
                            [
                                ft.Row(
                                    [
                                        ft.Text("78", size=36, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                        ft.Container(content=ft.Text("/100", size=14, color=t.TEXT_MUTED), padding=ft.padding.only(bottom=6)),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.END, spacing=4,
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            ft.Icon(ft.icons.ARROW_UPWARD, size=12, color=t.GOOD),
                                            ft.Text("4% vs. semana anterior", size=11, color=t.GOOD, weight=ft.FontWeight.W_500),
                                        ],
                                        spacing=2,
                                    ),
                                    bgcolor="#E6F9F8", border_radius=10,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                ),
                            ],
                            spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=12),
                        _mini_bar_chart(_WEEKLY_DATA),
                    ],
                    spacing=0,
                )
            ),
            card(
                ft.Column(
                    [card_label("Sesiones recientes"), ft.Container(height=8)]
                    + [_session_row(s, last=(i == len(_RECENT_SESSIONS) - 1)) for i, s in enumerate(_RECENT_SESSIONS)],
                    spacing=0,
                )
            ),
            ft.Container(
                content=ft.Text("Ver todas las sesiones", size=13, color=t.TEAL, weight=ft.FontWeight.W_600, text_align=ft.TextAlign.CENTER),
                alignment=ft.alignment.center,
                padding=ft.padding.symmetric(vertical=4),
            ),
            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )