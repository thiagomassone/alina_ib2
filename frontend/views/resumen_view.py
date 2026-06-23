"""Tab 0 — Resumen: dashboard del día."""

from __future__ import annotations
import flet as ft
import theme as t
from .components import card, card_label, dot, pill, divider, section_header


def _device_card() -> ft.Control:
    return card(
        ft.Row(
            [
                ft.Container(
                    content=ft.Icon(ft.icons.SENSORS, color=t.NAVY, size=28),
                    width=52, height=52, bgcolor="#EEF2F7",
                    border_radius=12, alignment=ft.alignment.center,
                ),
                ft.Column(
                    [
                        ft.Text("ALINA Dispositivo", size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
                        ft.Row([dot(t.GOOD, 8), ft.Text("Conectado", size=12, color=t.TEXT_MUTED)], spacing=6),
                    ],
                    spacing=4, expand=True,
                ),
                ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.icons.BATTERY_FULL, color=t.GOOD, size=18),
                                ft.Text("92%", size=14, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                            ],
                            spacing=4, alignment=ft.MainAxisAlignment.END,
                        ),
                        ft.Text("Batería", size=10, color=t.TEXT_MUTED),
                    ],
                    spacing=2, horizontal_alignment=ft.CrossAxisAlignment.END,
                ),
            ],
            spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
    )


def _score_card(score: int = 82) -> ft.Control:
    score = max(0, min(100, score))
    return card(
        ft.Column(
            [
                card_label("Puntuación postural"),
                ft.Container(height=4),
                ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Row(
                                    [
                                        ft.Text(str(score), size=44, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                                        ft.Container(
                                            content=ft.Text("/100", size=15, color=t.TEXT_MUTED),
                                            padding=ft.padding.only(bottom=8),
                                        ),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.END,
                                    spacing=4,
                                ),
                                pill("Buena", t.TEAL),
                            ],
                            spacing=10, expand=True,
                        ),
                        ft.Stack(
                            [
                                ft.PieChart(
                                    sections=[
                                        ft.PieChartSection(score, color=t.TEAL, radius=14),
                                        ft.PieChartSection(100 - score, color=t.TEAL_SOFT, radius=14),
                                    ],
                                    sections_space=0,
                                    center_space_radius=38,
                                    width=110, height=110,
                                ),
                                ft.Container(
                                    content=ft.Column(
                                        [
                                            ft.Text(f"{score}%", size=18, weight=ft.FontWeight.W_700, color=t.NAVY),
                                            ft.Text("Buena postura", size=9, color=t.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
                                        ],
                                        spacing=0,
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        alignment=ft.MainAxisAlignment.CENTER,
                                    ),
                                    width=110, height=110,
                                    alignment=ft.alignment.center,
                                ),
                            ],
                            width=110, height=110,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
        )
    )


def _metric_card(title: str, value: str, subtitle: str) -> ft.Control:
    return card(
        ft.Column(
            [
                card_label(title),
                ft.Container(height=2),
                ft.Text(value, size=24, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
                ft.Text(subtitle, size=11, color=t.TEXT_LIGHT),
            ],
            spacing=2,
        ),
        padding=14,
    )


def _legend_row(color: str, label: str, value: str) -> ft.Control:
    return ft.Row(
        [
            ft.Row([dot(color), ft.Text(label, size=13, color=t.TEXT_DARK)], spacing=8),
            ft.Text(value, size=13, color=t.TEXT_MUTED, weight=ft.FontWeight.W_500),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )


def _daily_summary_card() -> ft.Control:
    return card(
        ft.Column(
            [
                card_label("Resumen diario"),
                ft.Container(height=6),
                _legend_row(t.GOOD, "Buena postura", "2h 05m"),
                _legend_row(t.NEUTRAL, "Postura activa", "30m"),
                _legend_row(t.BAD, "Mala postura", "20m"),
            ],
            spacing=10,
        )
    )


def _calibration_card() -> ft.Control:
    return card(
        ft.Row(
            [
                ft.Column(
                    [
                        card_label("Última calibración"),
                        ft.Text("Hoy, 08:15", size=14, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
                        ft.Row(
                            [
                                ft.Icon(ft.icons.REFRESH, size=12, color=t.TEAL),
                                ft.Text("Calibración conectada", size=11, color=t.TEAL),
                            ],
                            spacing=4,
                        ),
                    ],
                    spacing=2, expand=True,
                ),
                ft.Container(
                    content=ft.Icon(ft.icons.CHECK, color=t.CARD, size=16),
                    bgcolor=t.GOOD, border_radius=14,
                    width=28, height=28, alignment=ft.alignment.center,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=14,
    )


def resumen_view(page: ft.Page) -> ft.Control:
    username = getattr(page, "username", None) or "Alex"
    return ft.Column(
        [
            section_header(f"Hola, {username}", "Resumen de hoy"),
            ft.Container(height=10),
            _device_card(),
            _score_card(score=82),
            ft.Row(
                [
                    ft.Container(content=_metric_card("Tiempo hoy", "2h 35m", "activos"), expand=True),
                    ft.Container(content=_metric_card("Alertas", "8", "hoy"), expand=True),
                ],
                spacing=12,
            ),
            _daily_summary_card(),
            _calibration_card(),
            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )