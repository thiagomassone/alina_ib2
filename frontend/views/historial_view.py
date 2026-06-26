"""Tab 2 — Historial: gráfico de línea por período + sesiones recientes."""

from __future__ import annotations
from datetime import datetime, timedelta, date
from collections import defaultdict
import flet as ft
import theme as t
from .components import card, card_label, divider, section_header

# ── Mock de fallback ──────────────────────────────────────────────────────────
_MOCK_SESSIONS = [
    {"fecha": "Hoy, 14:30",  "duracion": "45 min", "score": 83, "min_buena": 30.0, "min_mala": 15.0, "alertas": 3},
    {"fecha": "Hoy, 08:15",  "duracion": "60 min", "score": 76, "min_buena": 42.0, "min_mala": 18.0, "alertas": 5},
    {"fecha": "Ayer, 18:20", "duracion": "35 min", "score": 74, "min_buena": 22.0, "min_mala": 13.0, "alertas": 4},
]


def _fmt_session(s: dict) -> dict:
    """Convierte un SessionOut del backend al formato que usa la UI."""
    try:
        dt = datetime.fromisoformat(s["started_at"])
        now = datetime.now()
        if dt.date() == now.date():
            fecha = f"Hoy, {dt.strftime('%H:%M')}"
        elif (now.date() - dt.date()).days == 1:
            fecha = f"Ayer, {dt.strftime('%H:%M')}"
        else:
            fecha = dt.strftime("%d/%m, %H:%M")
        mins = int(s["duracion_min"])
        duracion = f"{mins} min" if mins < 60 else f"{mins // 60}h {mins % 60:02d}m"
        return {
            "fecha": fecha,
            "duracion": duracion,
            "score": int(s["score"]),
            "min_buena": s.get("min_buena", 0.0),
            "min_mala": s.get("min_mala", 0.0),
            "alertas": s.get("alertas_hapticas", 0),
            "started_at": s["started_at"],
        }
    except Exception:
        return {"fecha": "—", "duracion": "—", "score": 0, "min_buena": 0.0, "min_mala": 0.0, "alertas": 0}


def _fmt_min(m: float) -> str:
    m = int(m)
    return f"{m // 60}h {m % 60:02d}m" if m >= 60 else f"{m}m"


# ── Score badge ───────────────────────────────────────────────────────────────

def _score_badge(score: int) -> ft.Control:
    color = t.GOOD if score >= 80 else (t.NEUTRAL if score >= 65 else t.BAD)
    return ft.Container(
        content=ft.Text(str(score), size=13, weight=ft.FontWeight.W_700, color=t.CARD),
        bgcolor=color, border_radius=8,
        padding=ft.padding.symmetric(horizontal=8, vertical=3),
        width=38, alignment=ft.alignment.center,
    )


# ── Session row (expandible) ──────────────────────────────────────────────────

def _session_row(session: dict, last: bool = False) -> ft.Control:
    detail = ft.Container(
        content=ft.Row(
            [
                ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE_OUTLINE, size=13, color=t.GOOD),
                    ft.Text(f"Buena: {_fmt_min(session['min_buena'])}", size=11, color=t.TEXT_MUTED),
                ], spacing=4),
                ft.Row([
                    ft.Icon(ft.icons.CANCEL_OUTLINED, size=13, color=t.BAD),
                    ft.Text(f"Mala: {_fmt_min(session['min_mala'])}", size=11, color=t.TEXT_MUTED),
                ], spacing=4),
                ft.Row([
                    ft.Icon(ft.icons.VIBRATION, size=13, color=t.NEUTRAL),
                    ft.Text(f"Alertas: {session['alertas']}", size=11, color=t.TEXT_MUTED),
                ], spacing=4),
            ],
            spacing=12,
        ),
        visible=False,
        padding=ft.padding.only(top=6, bottom=2),
    )

    def toggle(_):
        detail.visible = not detail.visible
        page_ref[0].update()

    # page_ref se inyecta desde afuera
    page_ref = [None]

    row = ft.GestureDetector(
        on_tap=toggle,
        content=ft.Column(
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
                        ft.Icon(ft.icons.EXPAND_MORE, size=16, color=t.TEXT_LIGHT),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                detail,
            ] + ([] if last else [ft.Container(height=2), divider(), ft.Container(height=2)]),
            spacing=0,
        ),
    )
    return row, page_ref


# ── Período helpers ───────────────────────────────────────────────────────────

def _week_range(offset: int) -> tuple[date, date]:
    """Lunes–Domingo de la semana actual + offset semanas."""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=offset)
    return monday, monday + timedelta(days=6)


def _month_range(offset: int) -> tuple[date, date]:
    today = date.today()
    # Primer día del mes actual + offset meses
    month = today.month + offset
    year = today.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    first = date(year, month, 1)
    # Último día del mes
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)
    return first, last


def _quarter_range(offset: int) -> tuple[date, date]:
    today = date.today()
    # Inicio del trimestre actual + offset trimestres
    q_start_month = ((today.month - 1) // 3) * 3 + 1
    total_months = (today.year * 12 + q_start_month - 1) + offset * 3
    year = total_months // 12
    month = total_months % 12 + 1
    first = date(year, month, 1)
    # 3 meses después
    end_month = month + 2
    end_year = year + (end_month - 1) // 12
    end_month = ((end_month - 1) % 12) + 1
    if end_month == 12:
        last = date(end_year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(end_year, end_month + 1, 1) - timedelta(days=1)
    return first, last


def _year_range(offset: int) -> tuple[date, date]:
    year = date.today().year + offset
    return date(year, 1, 1), date(year, 12, 31)


def _period_label(period: str, offset: int) -> str:
    MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    if period == "semana":
        s, e = _week_range(offset)
        return f"{s.day}/{s.month:02d} – {e.day}/{e.month:02d} {e.year}"
    elif period == "mes":
        s, _ = _month_range(offset)
        return f"{MESES[s.month-1]} {s.year}"
    elif period == "trimestre":
        s, e = _quarter_range(offset)
        return f"{MESES[s.month-1]} – {MESES[e.month-1]} {e.year}"
    else:  # año
        s, _ = _year_range(offset)
        return str(s.year)


# ── Agrupar sesiones en puntos del gráfico ────────────────────────────────────

def _sessions_to_chart_points(
    sessions_raw: list[dict],
    period: str,
    offset: int,
) -> tuple[list[tuple[str, float, float]], float, int]:
    """
    Devuelve (puntos_grafico, score_promedio, total_sesiones).
    puntos_grafico = lista de (label_eje_x, x_coord, score)
    - Para semana/mes/trimestre: x_coord = índice 0,1,2...
    - Para año: x_coord = número de mes (1-12) para que los gaps sean reales
    """
    MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
             "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    if period == "semana":
        start, end = _week_range(offset)
    elif period == "mes":
        start, end = _month_range(offset)
    elif period == "trimestre":
        start, end = _quarter_range(offset)
    else:
        start, end = _year_range(offset)

    # Filtrar sesiones dentro del rango
    in_range = []
    for s in sessions_raw:
        try:
            dt = datetime.fromisoformat(s["started_at"]).date()
            if start <= dt <= end:
                in_range.append((dt, float(s["score"])))
        except Exception:
            pass

    if not in_range:
        return [], 0.0, 0

    # Agrupar
    groups: dict = defaultdict(list)
    if period in ("semana", "mes"):
        for dt, score in in_range:
            groups[dt].append(score)
        points = []
        for i, d in enumerate(sorted(groups)):
            avg = sum(groups[d]) / len(groups[d])
            label = f"{d.day}/{d.month:02d}"
            points.append((label, float(i), float(int(avg))))
    elif period == "trimestre":
        # Agrupar por mes (no por día) y truncar hacia abajo
        for dt, score in in_range:
            groups[dt.month].append(score)
        MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                 "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        points = []
        for i, m in enumerate(sorted(groups)):
            avg = int(sum(groups[m]) / len(groups[m]))  # truncar hacia abajo
            points.append((MESES[m - 1], float(i), float(avg)))
    else:  # año — x_coord = número de mes (1-12) para respetar gaps
        for dt, score in in_range:
            groups[dt.month].append(score)
        points = []
        for m in sorted(groups):
            avg = sum(groups[m]) / len(groups[m])
            points.append((MESES[m - 1], float(m), float(int(avg))))

    all_scores = [s for _, _, s in points]
    promedio = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0
    return points, promedio, len(in_range)


# ── Comparación con período anterior ─────────────────────────────────────────

def _compare_delta(sessions_raw: list[dict], period: str, offset: int) -> float | None:
    """Retorna el delta % vs. período anterior, o None si no hay datos anteriores."""
    _, score_curr, n_curr = _sessions_to_chart_points(sessions_raw, period, offset)
    _, score_prev, n_prev = _sessions_to_chart_points(sessions_raw, period, offset - 1)
    if n_curr == 0 or n_prev == 0:
        return None
    return round(((score_curr - score_prev) / score_prev) * 100, 1)


# ── LineChart builder ─────────────────────────────────────────────────────────

def _point_color(score: float) -> str:
    if score >= 80:
        return t.GOOD
    elif score >= 65:
        return t.NEUTRAL
    return t.BAD


def _build_line_chart(points: list[tuple[str, float, float]], period: str = "semana", offset: int = 0) -> ft.Control:
    if not points:
        return ft.Container(
            content=ft.Text("Sin datos para este período", size=12, color=t.TEXT_MUTED),
            alignment=ft.alignment.center,
            height=140,
        )

    # points = (label, x_coord, score)
    data_points = [
        ft.LineChartDataPoint(
            x=x, y=score,
            point=ft.ChartCirclePoint(radius=5, color=_point_color(score)),
            selected_point=ft.ChartCirclePoint(radius=7, color=_point_color(score)),
        )
        for (_, x, score) in points
    ]

    if period == "año":
        MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                 "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        x_labels = [
            ft.ChartAxisLabel(value=float(m), label=ft.Text(MESES[m - 1], size=9, color=t.TEXT_MUTED))
            for m in range(1, 13)
        ]
        min_x, max_x = 1.0, 12.0
    elif period == "trimestre":
        # Eje X fijo: siempre los 3 meses del trimestre, haya o no datos
        MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                 "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        q_start, q_end = _quarter_range(offset)
        q_months = []
        m = q_start.month
        for i in range(3):
            month_idx = ((m - 1 + i) % 12)
            q_months.append((i, MESES[month_idx]))
        x_labels = [
            ft.ChartAxisLabel(value=float(i), label=ft.Text(label, size=9, color=t.TEXT_MUTED))
            for i, label in q_months
        ]
        min_x, max_x = 0.0, 2.0
    else:
        # Mostrar labels cada N puntos para no pisar fechas
        n = len(points)
        step = 1 if n <= 7 else (3 if n <= 15 else 5)
        x_labels = [
            ft.ChartAxisLabel(value=x, label=ft.Text(label, size=9, color=t.TEXT_MUTED))
            for i, (label, x, _) in enumerate(points)
            if i % step == 0
        ]
        min_x = 0.0
        max_x = max(points[-1][1], 1.0)

    series = ft.LineChartData(
        data_points=data_points,
        curved=True,
        color=t.TEAL,
        stroke_width=2.5,
        stroke_cap_round=True,
        below_line_bgcolor=f"{t.TEAL}18",
    )

    chart = ft.LineChart(
        data_series=[series],
        min_y=0,
        max_y=100,
        min_x=min_x,
        max_x=max_x,
        animate=ft.animation.Animation(400, ft.AnimationCurve.EASE_IN_OUT),
        interactive=True,
        left_axis=ft.ChartAxis(
            labels=[
                ft.ChartAxisLabel(value=0,   label=ft.Text("0",   size=9, color=t.TEXT_MUTED)),
                ft.ChartAxisLabel(value=50,  label=ft.Text("50",  size=9, color=t.TEXT_MUTED)),
                ft.ChartAxisLabel(value=100, label=ft.Text("100", size=9, color=t.TEXT_MUTED)),
            ],
            labels_size=28,
        ),
        bottom_axis=ft.ChartAxis(labels=x_labels, labels_size=32),
        horizontal_grid_lines=ft.ChartGridLines(interval=25, color=t.DIVIDER, width=1),
        tooltip_bgcolor=t.NAVY,
        expand=True,
    )
    return ft.Container(content=chart, height=200, expand=True)


# ── Period chip ───────────────────────────────────────────────────────────────

def _period_chip(label: str, selected: bool, on_click) -> ft.Control:
    return ft.GestureDetector(
        on_tap=on_click,
        content=ft.Container(
            content=ft.Text(
                label, size=13,
                weight=ft.FontWeight.W_600 if selected else ft.FontWeight.W_400,
                color=t.CARD if selected else t.TEXT_MUTED,
            ),
            bgcolor=t.TEAL if selected else t.CARD,
            border_radius=20,
            padding=ft.padding.symmetric(horizontal=16, vertical=6),
            border=ft.border.all(1, t.TEAL if selected else t.DIVIDER),
        ),
    )


# ── Entry point ───────────────────────────────────────────────────────────────

def historial_view(page: ft.Page) -> ft.Control:
    # ── Cargar datos ──────────────────────────────────────────────────────────
    try:
        sessions_raw = page.api.get_sessions(limit=200)
        usando_mock = len(sessions_raw) == 0
    except Exception:
        sessions_raw = []
        usando_mock = True

    sessions_fmt = [_fmt_session(s) for s in sessions_raw]
    recent = sessions_fmt[:5] if sessions_fmt else []

    # ── Estado reactivo ───────────────────────────────────────────────────────
    state = {"period": "semana", "offset": 0}

    # ── Controles mutables ────────────────────────────────────────────────────
    chips_row     = ft.Ref[ft.Row]()
    period_label  = ft.Ref[ft.Text]()
    score_text    = ft.Ref[ft.Text]()
    total_text    = ft.Ref[ft.Text]()
    delta_row     = ft.Ref[ft.Row]()
    chart_cont    = ft.Ref[ft.Container]()
    mock_note     = ft.Ref[ft.Text]()

    PERIOD_LABELS = {
        "semana": "Semana",
        "mes": "Mes",
        "trimestre": "3 meses",
        "año": "Año",
    }
    PERIOD_KEYS = list(PERIOD_LABELS.keys())

    def _rebuild_chart():
        p = state["period"]
        o = state["offset"]
        pts, promedio, total = _sessions_to_chart_points(sessions_raw, p, o)
        delta = _compare_delta(sessions_raw, p, o) if not usando_mock else None

        # Actualizar label de período
        period_label.current.value = _period_label(p, o)

        # Score y total
        score_text.current.value = str(int(promedio)) if total > 0 else "—"
        total_text.current.value = f"{total} sesión{'es' if total != 1 else ''}"

        # Delta
        if delta is not None:
            arrow = ft.icons.ARROW_UPWARD if delta >= 0 else ft.icons.ARROW_DOWNWARD
            color = t.GOOD if delta >= 0 else t.BAD
            prev_label = PERIOD_LABELS[p].lower()
            delta_row.current.controls = [
                ft.Icon(arrow, size=14, color=color),
                ft.Text(f"{abs(delta)}% vs. {prev_label} anterior", size=12, color=color, weight=ft.FontWeight.W_500),
            ]
            delta_row.current.visible = True
        else:
            delta_row.current.visible = False

        # Gráfico
        chart_cont.current.content = _build_line_chart(pts, p, o)

        # Chips — reconstruir con nuevo estado
        chips_row.current.controls = [
            _period_chip(PERIOD_LABELS[k], k == p, _make_period_handler(k))
            for k in PERIOD_KEYS
        ]

        mock_note.current.visible = usando_mock

    def _make_period_handler(period_key: str):
        def handler(_):
            state["period"] = period_key
            state["offset"] = 0
            _rebuild_chart()
            page.update()
        return handler

    def prev_period(_):
        state["offset"] -= 1
        _rebuild_chart()
        page.update()

    def next_period(_):
        if state["offset"] < 0:
            state["offset"] += 1
            _rebuild_chart()
            page.update()

    # ── Construcción inicial ──────────────────────────────────────────────────
    init_pts, init_score, init_total = _sessions_to_chart_points(sessions_raw, "semana", 0)
    init_delta = _compare_delta(sessions_raw, "semana", 0) if not usando_mock else None

    if init_delta is not None:
        arrow = ft.icons.ARROW_UPWARD if init_delta >= 0 else ft.icons.ARROW_DOWNWARD
        color = t.GOOD if init_delta >= 0 else t.BAD
        delta_controls = [
            ft.Icon(arrow, size=14, color=color),
            ft.Text(f"{abs(init_delta)}% vs. semana anterior", size=12, color=color, weight=ft.FontWeight.W_500),
        ]
        delta_visible = True
    else:
        delta_controls = []
        delta_visible = False

    # Construir rows de sesiones recientes (con page_ref inyectado)
    session_rows = []
    for i, s in enumerate(recent):
        row_widget, page_ref_list = _session_row(s, last=(i == len(recent) - 1))
        page_ref_list[0] = page
        session_rows.append(row_widget)

    col = ft.Column(
        [
            section_header("Historial", "Seguimiento de tus sesiones"),
            ft.Container(height=10),

            # ── Card del gráfico ──────────────────────────────────────────────
            card(
                ft.Column(
                    [
                        # Chips de período
                        ft.Row(
                            ref=chips_row,
                            controls=[
                                _period_chip(PERIOD_LABELS[k], k == "semana", _make_period_handler(k))
                                for k in PERIOD_KEYS
                            ],
                            spacing=8,
                        ),
                        ft.Container(height=10),

                        # Navegación de período
                        ft.Row(
                            [
                                ft.GestureDetector(
                                    on_tap=prev_period,
                                    content=ft.Icon(ft.icons.CHEVRON_LEFT, color=t.TEXT_MUTED, size=20),
                                ),
                                ft.Row(
                                    [
                                        ft.Icon(ft.icons.CALENDAR_TODAY_OUTLINED, size=14, color=t.TEXT_MUTED),
                                        ft.Text(
                                            ref=period_label,
                                            value=_period_label("semana", 0),
                                            size=13, color=t.TEXT_DARK, weight=ft.FontWeight.W_500,
                                        ),
                                    ],
                                    spacing=6,
                                ),
                                ft.GestureDetector(
                                    on_tap=next_period,
                                    content=ft.Icon(ft.icons.CHEVRON_RIGHT, color=t.TEXT_MUTED, size=20),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Container(height=12),

                        # Score + delta
                        card_label("Puntuación postural"),
                        ft.Container(height=4),
                        ft.Row(
                            [
                                ft.Row(
                                    [
                                        ft.Text(
                                            ref=score_text,
                                            value=str(int(init_score)) if init_total > 0 else "—",
                                            size=36, weight=ft.FontWeight.W_700, color=t.TEXT_DARK,
                                        ),
                                        ft.Container(
                                            content=ft.Text("/100", size=14, color=t.TEXT_MUTED),
                                            padding=ft.padding.only(bottom=6),
                                        ),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.END, spacing=4,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        ref=total_text,
                                        value=f"{init_total} sesión{'es' if init_total != 1 else ''}",
                                        size=11, color=t.TEXT_MUTED, weight=ft.FontWeight.W_500,
                                    ),
                                    bgcolor="#F3F5F8", border_radius=10,
                                    padding=ft.padding.symmetric(horizontal=8, vertical=4),
                                ),
                            ],
                            spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=4),
                        ft.Row(
                            ref=delta_row,
                            controls=delta_controls,
                            spacing=4,
                            visible=delta_visible,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        ft.Container(height=12),

                        # Gráfico
                        ft.Container(
                            ref=chart_cont,
                            content=_build_line_chart(init_pts, "semana", 0),
                        ),
                        ft.Container(height=4),

                        ft.Text(
                            ref=mock_note,
                            value="* Datos de ejemplo — completá tu primera sesión",
                            size=10, color=t.TEXT_LIGHT,
                            visible=usando_mock,
                        ),
                    ],
                    spacing=0,
                )
            ),

            # ── Card de sesiones recientes ────────────────────────────────────
            card(
                ft.Column(
                    [card_label("Sesiones recientes"), ft.Container(height=8)]
                    + session_rows,
                    spacing=0,
                )
            ),

            ft.Container(height=12),
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    def refresh():
        """Recargar sesiones y reconstruir gráfico y lista reciente."""
        nonlocal sessions_raw, sessions_fmt, recent
        try:
            sessions_raw = page.api.get_sessions(limit=200)
        except Exception:
            return
        sessions_fmt = [_fmt_session(s) for s in sessions_raw]
        recent = sessions_fmt[:5] if sessions_fmt else []
        # Reconstruir con el período/offset actuales
        _rebuild_chart()
        # Reconstruir sesiones recientes
        new_rows = []
        for i, s in enumerate(recent):
            row_widget, page_ref_list = _session_row(s, last=(i == len(recent) - 1))
            page_ref_list[0] = page
            new_rows.append(row_widget)
        # Encontrar la card de sesiones recientes (último card antes del Container final)
        # y reemplazar su contenido
        recent_card = col.controls[-2]
        recent_card.content.controls = [card_label("Sesiones recientes"), ft.Container(height=8)] + new_rows
        try:
            page.update()
        except Exception:
            pass

    col.refresh = refresh
    return col