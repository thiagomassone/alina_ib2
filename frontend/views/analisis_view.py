"""Tab Análisis — métricas de progreso postural.

Complementa a Historial (que ya tiene la tendencia de score con selector de
período). Acá mostramos lo que no está en otro lado:

  - Tendencia semanal (mini): score promedio por día, últimos 7 días.
  - Semana vs semana pasada: score, minutos de uso y alertas/min con flechas.
  - Distribución por calidad postural: donut buena / neutra / mala.
  - Densidad de alertas (alertas/min) en el tiempo: la curva "estás mejorando".
  - Récords: mejor score, sesión más larga, racha más larga.
  - Insight: una frase auto-generada sobre los datos.

Todo se calcula en el cliente desde /sessions (+ /sessions/racha para el récord).
No pega a ningún endpoint nuevo ni toca la base.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, date, timedelta

import flet as ft
import theme as t
from i18n import tr
from .components import card, card_label, section_header, dot

_DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]


# ── Carga de datos ────────────────────────────────────────────────────────────
def _load_sessions(page: ft.Page) -> list[dict]:
    try:
        return page.api.get_sessions(limit=300)
    except Exception:
        return []


def _load_record(page: ft.Page) -> int:
    try:
        return int(page.api.get_racha().get("racha_record", 0))
    except Exception:
        return 0


def _dt(s: dict) -> date | None:
    try:
        return datetime.fromisoformat(s["started_at"]).date()
    except Exception:
        return None


def _window(sessions: list[dict], start: date, end: date) -> list[dict]:
    out = []
    for s in sessions:
        d = _dt(s)
        if d is not None and start <= d <= end:
            out.append(s)
    return out


def _agg(sessions: list[dict]) -> dict:
    """Agrega una lista de sesiones: score prom, minutos de uso, alertas/min."""
    if not sessions:
        return {"score": None, "uso": 0.0, "apm": None, "n": 0}
    scores = [float(s.get("score", 0)) for s in sessions]
    uso = sum(float(s.get("duracion_min", 0)) for s in sessions)
    alertas = sum(int(s.get("alertas_hapticas", 0)) for s in sessions)
    apm = (alertas / uso) if uso > 0 else None
    return {"score": sum(scores) / len(scores), "uso": uso, "apm": apm, "n": len(sessions)}


# ── Tendencia semanal (mini line) ─────────────────────────────────────────────
def _tendencia_card(sessions: list[dict]) -> ft.Control:
    hoy = date.today()
    dias = [hoy - timedelta(days=i) for i in range(6, -1, -1)]  # 7 días, viejo→hoy
    por_dia = defaultdict(list)
    for s in sessions:
        d = _dt(s)
        if d in dias:
            por_dia[d].append(float(s.get("score", 0)))

    puntos = []
    for i, d in enumerate(dias):
        if por_dia[d]:
            avg = sum(por_dia[d]) / len(por_dia[d])
            puntos.append((i, round(avg)))

    x_labels = [
        ft.ChartAxisLabel(value=float(i), label=ft.Text(_DIAS[d.weekday()], size=9, color=t.TEXT_MUTED))
        for i, d in enumerate(dias)
    ]

    if len(puntos) < 2:
        chart = ft.Container(
            content=ft.Text(tr("Necesitás sesiones en al menos 2 días de esta semana."),
                            size=12, color=t.TEXT_MUTED, text_align=ft.TextAlign.CENTER),
            alignment=ft.alignment.center, height=170,
        )
    else:
        data_points = [
            ft.LineChartDataPoint(
                x=float(x), y=float(y),
                point=ft.ChartCirclePoint(radius=4, color=_score_color(y)),
            )
            for (x, y) in puntos
        ]
        series = ft.LineChartData(
            data_points=data_points, curved=True, color=t.TEAL,
            stroke_width=2.5, stroke_cap_round=True, below_line_bgcolor=f"{t.TEAL}18",
        )
        chart = ft.Container(
            content=ft.LineChart(
                data_series=[series], min_y=0, max_y=100, min_x=0.0, max_x=6.0,
                animate=ft.animation.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
                left_axis=ft.ChartAxis(labels=[
                    ft.ChartAxisLabel(value=0,   label=ft.Text("0",   size=9, color=t.TEXT_MUTED)),
                    ft.ChartAxisLabel(value=50,  label=ft.Text("50",  size=9, color=t.TEXT_MUTED)),
                    ft.ChartAxisLabel(value=100, label=ft.Text("100", size=9, color=t.TEXT_MUTED)),
                ], labels_size=28),
                bottom_axis=ft.ChartAxis(labels=x_labels, labels_size=28),
                horizontal_grid_lines=ft.ChartGridLines(interval=25, color=t.DIVIDER, width=1),
                tooltip_bgcolor=t.NAVY,
            ),
            height=180,
        )
    return card(ft.Column([card_label(tr("Tendencia semanal")),
                           ft.Text(tr("Score promedio por día"), size=11, color=t.TEXT_LIGHT),
                           ft.Container(height=6), chart], spacing=2))


def _score_color(score: float) -> str:
    return t.GOOD if score >= 80 else (t.NEUTRAL if score >= 65 else t.BAD)


# ── Semana vs semana ──────────────────────────────────────────────────────────
def _comparativa_card(sessions: list[dict]) -> ft.Control:
    hoy = date.today()
    act = _agg(_window(sessions, hoy - timedelta(days=6), hoy))
    prev = _agg(_window(sessions, hoy - timedelta(days=13), hoy - timedelta(days=7)))

    filas = [
        _cmp_row("Score promedio", act["score"], prev["score"], lambda v: f"{v:.0f}", higher_better=True),
        _cmp_row("Minutos de uso", act["uso"], prev["uso"], lambda v: f"{v:.0f} min", higher_better=True),
        _cmp_row("Alertas por min", act["apm"], prev["apm"], lambda v: f"{v:.2f}", higher_better=False),
    ]
    return card(ft.Column([
        card_label(tr("Semana vs semana pasada")),
        ft.Container(height=8),
        ft.Column(filas, spacing=12),
    ], spacing=2))


def _cmp_row(label, cur, prev, fmt, higher_better: bool) -> ft.Control:
    val_txt = fmt(cur) if cur is not None else "—"
    if cur is None or prev is None or prev == 0:
        delta_ctrl = ft.Text(tr("sin comparación"), size=11, color=t.TEXT_LIGHT)
    else:
        pct = (cur - prev) / prev * 100
        subio = cur > prev
        mejora = subio if higher_better else (not subio)
        color = t.GOOD if mejora else t.BAD
        icon = ft.icons.ARROW_UPWARD if subio else ft.icons.ARROW_DOWNWARD
        delta_ctrl = ft.Row(
            [ft.Icon(icon, size=13, color=color),
             ft.Text(f"{abs(pct):.0f}%", size=12, weight=ft.FontWeight.W_600, color=color)],
            spacing=2, tight=True,
        )
    return ft.Row(
        [ft.Text(tr(label), size=13, color=t.TEXT_MUTED, expand=True),
         ft.Text(val_txt, size=15, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
         ft.Container(width=8), delta_ctrl],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ── Distribución por calidad postural (donut) ─────────────────────────────────
def _distribucion_card(sessions: list[dict]) -> ft.Control:
    buena = sum(float(s.get("min_buena", 0)) for s in sessions)
    mala  = sum(float(s.get("min_mala", 0)) for s in sessions)
    uso   = sum(float(s.get("duracion_min", 0)) for s in sessions)
    neutra = max(0.0, uso - buena - mala)
    total = buena + neutra + mala

    if total <= 0:
        body = ft.Container(
            content=ft.Text(tr("Todavía no hay minutos registrados."), size=12, color=t.TEXT_MUTED),
            alignment=ft.alignment.center, height=140,
        )
    else:
        def pct(x): return x / total * 100
        pie = ft.PieChart(
            sections=[
                ft.PieChartSection(buena,  color=t.GOOD,    radius=22),
                ft.PieChartSection(neutra, color=t.NEUTRAL, radius=22),
                ft.PieChartSection(mala,   color=t.BAD,     radius=22),
            ],
            sections_space=2, center_space_radius=34,
        )
        leyenda = ft.Column([
            _leg_row(t.GOOD,    "Buena",  pct(buena)),
            _leg_row(t.NEUTRAL, "Neutra", pct(neutra)),
            _leg_row(t.BAD,     "Mala",   pct(mala)),
        ], spacing=10)
        body = ft.Row(
            [ft.Container(content=pie, width=130, height=130),
             ft.Container(width=16),
             ft.Container(content=leyenda, expand=True)],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
    return card(ft.Column([card_label(tr("Distribución por calidad postural")),
                           ft.Text(tr("Porcentaje del tiempo en cada estado"), size=11, color=t.TEXT_LIGHT),
                           ft.Container(height=10), body], spacing=2))


def _leg_row(color: str, label: str, pct: float) -> ft.Control:
    return ft.Row(
        [dot(color, 10), ft.Text(tr(label), size=13, color=t.TEXT_DARK, expand=True),
         ft.Text(f"{pct:.0f}%", size=13, weight=ft.FontWeight.W_700, color=t.TEXT_MUTED)],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )


# ── Densidad de alertas (alertas/min por día) ─────────────────────────────────
def _densidad_card(sessions: list[dict]) -> ft.Control:
    hoy = date.today()
    dias = [hoy - timedelta(days=i) for i in range(13, -1, -1)]  # 14 días
    alertas = defaultdict(float)
    uso = defaultdict(float)
    for s in sessions:
        d = _dt(s)
        if d in dias:
            alertas[d] += int(s.get("alertas_hapticas", 0))
            uso[d] += float(s.get("duracion_min", 0))

    puntos = []
    for i, d in enumerate(dias):
        if uso[d] > 0:
            puntos.append((i, alertas[d] / uso[d]))

    if len(puntos) < 2:
        body = ft.Container(
            content=ft.Text(tr("Necesitás sesiones en al menos 2 días."), size=12, color=t.TEXT_MUTED),
            alignment=ft.alignment.center, height=160,
        )
    else:
        max_y = max(0.5, max(y for _, y in puntos) * 1.25)
        data_points = [ft.LineChartDataPoint(x=float(x), y=float(y),
                       point=ft.ChartCirclePoint(radius=3, color=t.TEAL)) for x, y in puntos]
        series = ft.LineChartData(data_points=data_points, curved=True, color=t.TEAL,
                                  stroke_width=2.5, stroke_cap_round=True, below_line_bgcolor=f"{t.TEAL}18")
        step = 1 if len(dias) <= 7 else 3
        x_labels = [ft.ChartAxisLabel(value=float(i), label=ft.Text(f"{d.day}/{d.month}", size=9, color=t.TEXT_MUTED))
                    for i, d in enumerate(dias) if i % step == 0]
        body = ft.Container(
            content=ft.LineChart(
                data_series=[series], min_y=0, max_y=max_y, min_x=0.0, max_x=13.0,
                animate=ft.animation.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
                left_axis=ft.ChartAxis(labels=[
                    ft.ChartAxisLabel(value=0, label=ft.Text("0", size=9, color=t.TEXT_MUTED)),
                    ft.ChartAxisLabel(value=round(max_y, 1), label=ft.Text(f"{max_y:.1f}", size=9, color=t.TEXT_MUTED)),
                ], labels_size=28),
                bottom_axis=ft.ChartAxis(labels=x_labels, labels_size=28),
                horizontal_grid_lines=ft.ChartGridLines(interval=max_y / 2, color=t.DIVIDER, width=1),
                tooltip_bgcolor=t.NAVY,
            ),
            height=170,
        )
    return card(ft.Column([card_label(tr("Densidad de alertas")),
                           ft.Text(tr("Alertas por minuto · menos es mejor"), size=11, color=t.TEXT_LIGHT),
                           ft.Container(height=6), body], spacing=2))


# ── Récords ───────────────────────────────────────────────────────────────────
def _records_card(sessions: list[dict], record_racha: int) -> ft.Control:
    mejor_score = max((int(s.get("score", 0)) for s in sessions), default=0)
    mas_larga = max((float(s.get("duracion_min", 0)) for s in sessions), default=0.0)
    tiles = ft.Row([
        _tile(f"{mejor_score}", "Mejor score"),
        _tile(f"{int(mas_larga)} min", "Sesión más larga"),
        _tile(f"{record_racha}", "Racha más larga"),
    ], spacing=10)
    return card(ft.Column([card_label(tr("Récords")), ft.Container(height=10), tiles], spacing=2))


def _tile(value: str, label: str) -> ft.Control:
    return ft.Container(
        expand=True, bgcolor=t.BG, border_radius=12, padding=14,
        content=ft.Column([
            ft.Text(value, size=22, weight=ft.FontWeight.W_700, color=t.TEXT_DARK),
            ft.Text(tr(label), size=11, color=t.TEXT_LIGHT),
        ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.START),
    )


# ── Insight auto-generado ─────────────────────────────────────────────────────
def _insight(sessions: list[dict]) -> str | None:
    hoy = date.today()
    act = _agg(_window(sessions, hoy - timedelta(days=6), hoy))
    prev = _agg(_window(sessions, hoy - timedelta(days=13), hoy - timedelta(days=7)))
    if act["apm"] is not None and prev["apm"] is not None and prev["apm"] > 0:
        if act["apm"] < prev["apm"]:
            return "Vas mejorando: esta semana corregís menos que la anterior."
        if act["apm"] > prev["apm"]:
            return "Esta semana necesitaste más correcciones que la anterior."
    largas = [float(s["score"]) for s in sessions if float(s.get("duracion_min", 0)) >= 20]
    cortas = [float(s["score"]) for s in sessions if float(s.get("duracion_min", 0)) < 20]
    if largas and cortas:
        dl, dc = sum(largas) / len(largas), sum(cortas) / len(cortas)
        if dl - dc >= 3:
            return f"Tu postura es mejor en sesiones largas (+{dl - dc:.0f} pts vs. las cortas)."
    return None


def _insight_card(text: str) -> ft.Control:
    return card(ft.Row(
        [ft.Icon(ft.icons.LIGHTBULB_OUTLINE, size=20, color=t.TEAL),
         ft.Container(width=10),
         ft.Text(text, size=13, color=t.TEXT_DARK, expand=True)],
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    ))


# ── Vista ─────────────────────────────────────────────────────────────────────
def analisis_view(page: ft.Page) -> ft.Control:
    sessions = _load_sessions(page)
    record_racha = _load_record(page)

    if not sessions:
        return ft.Column([
            section_header(tr("Análisis"), tr("Tu progreso postural")),
            ft.Container(height=40),
            ft.Column([
                ft.Icon(ft.icons.INSIGHTS, size=48, color=t.TEXT_LIGHT),
                ft.Container(height=8),
                ft.Text(tr("Todavía no hay sesiones"), size=16, weight=ft.FontWeight.W_600, color=t.TEXT_DARK),
                ft.Text(tr("Completá tu primera sesión para ver tu análisis."), size=13, color=t.TEXT_MUTED),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
        ], expand=True)

    bloques = [
        section_header(tr("Análisis"), tr("Tu progreso postural")),
        ft.Container(height=10),
        _tendencia_card(sessions),
        _comparativa_card(sessions),
        _distribucion_card(sessions),
        _densidad_card(sessions),
        _records_card(sessions, record_racha),
    ]
    ins = _insight(sessions)
    if ins:
        bloques.append(_insight_card(ins))
    bloques.append(ft.Container(height=8))

    return ft.Column(bloques, spacing=14, scroll=ft.ScrollMode.AUTO, expand=True)
