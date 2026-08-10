"""Grafico do historico: SVG autonomo, sem dependencias externas.

Small multiples — um painel por carteira — com a carteira e os seus benchmarks
indexados a base 100 na data de inicio. Indexar e o que permite pos os quatro
mandatos (USD e BRL, escalas diferentes) no mesmo eixo: comparar niveis brutos
exigiria dois eixos, que distorcem a leitura.

Paleta validada em ambos os modos (scripts/validate_palette.js, --pairs all):
slots 1-3 do tema categorico de referencia. O aqua fica abaixo de 3:1 no fundo
claro, por isso cada serie leva rotulo direto no fim da linha — a identidade
nunca depende so da cor.
"""

from __future__ import annotations

from pathlib import Path

# slots categoricos 1-3 (claro / escuro)
SERIES_COLORS = [
    ("--series-1", "#2a78d6", "#3987e5"),   # carteira
    ("--series-2", "#eb6834", "#d95926"),   # benchmark de mercado
    ("--series-3", "#1baf7a", "#199e70"),   # CDI
]

PANEL_W, PANEL_H = 400, 190
COL_GAP, ROW_GAP = 56, 78
# margem esquerda folgada para os rotulos do eixo ("100.8" cabe inteiro)
MARGIN_X, MARGIN_TOP, MARGIN_BOTTOM = 52, 112, 34
LABEL_W = 58          # espaco a direita do painel para o rotulo direto
MIN_LABEL_GAP = 13    # separacao vertical minima entre rotulos diretos


def _esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _series_for(state: dict, benchmark_name: str,
                benchmark2_name: str | None) -> list[dict]:
    """Extrai as series indexadas a base 100 a partir do historico."""
    initial = state["initial_capital"]
    history = state.get("history", [])
    if not initial or not history:
        return []

    def index_of(key: str) -> list[float | None]:
        return [(point[key] / initial * 100.0) if key in point else None
                for point in history]

    series = [{"name": "Carteira", "values": index_of("nav")},
              {"name": benchmark_name, "values": index_of("benchmark_nav")}]
    if benchmark2_name and any("benchmark2_nav" in p for p in history):
        series.append({"name": benchmark2_name,
                       "values": index_of("benchmark2_nav")})
    return series


def _panel(x0: float, y0: float, title: str, dates: list[str],
           series: list[dict]) -> str:
    """Um painel do small multiple."""
    parts = [f'<g transform="translate({x0},{y0})">',
             f'<text class="panel-title" x="0" y="-12">{_esc(title)}</text>']

    values = [v for s in series for v in s["values"] if v is not None]
    if not values:
        parts.append('<text class="muted" x="0" y="40">sem historico ainda</text>')
        return "\n".join(parts) + "\n</g>"

    lo, hi = min(values + [100.0]), max(values + [100.0])
    pad = max((hi - lo) * 0.18, 0.35)
    lo, hi = lo - pad, hi + pad
    span = hi - lo

    def sy(value: float) -> float:
        return PANEL_H - (value - lo) / span * PANEL_H

    n = len(dates)
    def sx(i: int) -> float:
        return 0.0 if n <= 1 else i / (n - 1) * PANEL_W

    # grelha recessiva: base 100 marcada, extremos como referencia
    for level in (lo + span * 0.5, hi - pad * 0.35, lo + pad * 0.35):
        parts.append(f'<line class="grid" x1="0" y1="{sy(level):.1f}" '
                     f'x2="{PANEL_W}" y2="{sy(level):.1f}"/>')
    parts.append(f'<line class="baseline" x1="0" y1="{sy(100.0):.1f}" '
                 f'x2="{PANEL_W}" y2="{sy(100.0):.1f}"/>')
    parts.append(f'<text class="axis" x="-8" y="10" text-anchor="end">{hi:.1f}</text>')
    parts.append(f'<text class="axis" x="-8" y="{PANEL_H:.0f}" text-anchor="end">{lo:.1f}</text>')
    # o "100" fica na calha esquerda, fora da area dos dados; omite-se quando
    # colidiria com os rotulos dos extremos (a linha tracejada ja o denuncia)
    base_y = sy(100.0) + 3
    if abs(base_y - 10) > 14 and abs(base_y - PANEL_H) > 14:
        parts.append(f'<text class="axis base" x="-8" y="{base_y:.1f}" '
                     f'text-anchor="end">100</text>')

    # datas: so a primeira e a ultima, para nao poluir
    parts.append(f'<text class="axis" x="0" y="{PANEL_H + 16}">{_esc(dates[0])}</text>')
    if n > 1:
        parts.append(f'<text class="axis" x="{PANEL_W}" y="{PANEL_H + 16}" '
                     f'text-anchor="end">{_esc(dates[-1])}</text>')

    direct_labels: list[dict] = []
    for slot, item in enumerate(series):
        var = SERIES_COLORS[slot % len(SERIES_COLORS)][0]
        points = [(sx(i), sy(v), i, v) for i, v in enumerate(item["values"])
                  if v is not None]
        if not points:
            continue
        path = " ".join(f"{'M' if k == 0 else 'L'}{px:.1f},{py:.1f}"
                        for k, (px, py, _, _) in enumerate(points))
        parts.append(f'<path class="line" style="stroke:var({var})" d="{path}"/>')
        # marcadores >=8px so quando a serie e curta (evita ruido quando cresce)
        if len(points) <= 30:
            for px, py, i, v in points:
                parts.append(f'<circle class="dot" style="fill:var({var})" '
                             f'cx="{px:.1f}" cy="{py:.1f}" r="4"/>')
        # area de hover com tooltip nativo
        for px, py, i, v in points:
            parts.append(f'<circle class="hit" cx="{px:.1f}" cy="{py:.1f}" r="10">'
                         f'<title>{_esc(item["name"])} — {_esc(dates[i])}: '
                         f'{v:.2f} (base 100)</title></circle>')
        # rotulo direto recolhido agora, posicionado depois de resolver colisoes
        lx, ly, _, _ = points[-1]
        direct_labels.append({"x": lx, "y": ly, "var": var,
                              "name": item["name"]})

    # identidade nunca depende so da cor: cada serie leva rotulo, e rotulos
    # de linhas que convergem sao afastados para continuarem legiveis
    direct_labels.sort(key=lambda item: item["y"])
    for k in range(1, len(direct_labels)):
        gap = direct_labels[k]["y"] - direct_labels[k - 1]["y"]
        if gap < MIN_LABEL_GAP:
            direct_labels[k]["y"] = direct_labels[k - 1]["y"] + MIN_LABEL_GAP
    for label in direct_labels:
        parts.append(f'<text class="direct" style="fill:var({label["var"]})" '
                     f'x="{label["x"] + 9:.1f}" y="{label["y"] + 3:.1f}">'
                     f'{_esc(label["name"])}</text>')

    return "\n".join(parts) + "\n</g>"


def build_svg(date: str, panels: list[tuple[str, dict, str, str | None]]) -> str:
    """panels: [(titulo, state, benchmark_name, benchmark2_name)]"""
    cols = 2 if len(panels) > 1 else 1
    rows = (len(panels) + cols - 1) // cols
    width = MARGIN_X * 2 + cols * (PANEL_W + LABEL_W) + (cols - 1) * COL_GAP
    height = MARGIN_TOP + rows * (PANEL_H + ROW_GAP) + MARGIN_BOTTOM

    body: list[str] = []
    for idx, (title, state, bench, bench2) in enumerate(panels):
        col, row = idx % cols, idx // cols
        x0 = MARGIN_X + col * (PANEL_W + LABEL_W + COL_GAP)
        y0 = MARGIN_TOP + row * (PANEL_H + ROW_GAP)
        series = _series_for(state, bench, bench2)
        dates = [p["date"] for p in state.get("history", [])]
        body.append(_panel(x0, y0, title, dates, series))

    # legenda (sempre presente com >= 2 series)
    legend = ['<g transform="translate(%d,76)">' % MARGIN_X]
    for slot, name in enumerate(("Carteira", "Benchmark de mercado", "CDI")):
        var = SERIES_COLORS[slot][0]
        lx = slot * 190
        legend.append(f'<line class="legend-mark" style="stroke:var({var})" '
                      f'x1="{lx}" y1="-4" x2="{lx + 18}" y2="-4"/>')
        legend.append(f'<circle style="fill:var({var})" cx="{lx + 9}" cy="-4" r="4"/>')
        legend.append(f'<text class="legend" x="{lx + 25}" y="0">{name}</text>')
    legend.append("</g>")

    light = "".join(f"{var}:{lightv};" for var, lightv, _ in SERIES_COLORS)
    dark = "".join(f"{var}:{darkv};" for var, _, darkv in SERIES_COLORS)

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}"
     viewBox="0 0 {width} {height}" role="img"
     aria-label="Historico das carteiras indexado a base 100, por carteira">
<style>
  svg {{ color-scheme: light; {light}
        --surface-1:#fcfcfb; --text-primary:#0b0b0b; --text-secondary:#52514e;
        --grid:#e6e5e1; --baseline:#b9b8b2;
        background:var(--surface-1); }}
  @media (prefers-color-scheme: dark) {{
    svg {{ color-scheme: dark; {dark}
          --surface-1:#1a1a19; --text-primary:#ffffff; --text-secondary:#c3c2b7;
          --grid:#2f2f2d; --baseline:#4d4c48; }}
  }}
  text {{ font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI",
          Roboto, Helvetica, Arial, sans-serif; }}
  .title {{ font-size: 17px; font-weight: 600; fill: var(--text-primary); }}
  .subtitle {{ font-size: 12px; fill: var(--text-secondary); }}
  .panel-title {{ font-size: 13px; font-weight: 600; fill: var(--text-primary); }}
  .axis {{ font-size: 10px; fill: var(--text-secondary); }}
  .muted {{ font-size: 12px; fill: var(--text-secondary); }}
  .legend {{ font-size: 12px; fill: var(--text-secondary); }}
  .legend-mark {{ stroke-width: 2; }}
  .grid {{ stroke: var(--grid); stroke-width: 1; }}
  .baseline {{ stroke: var(--baseline); stroke-width: 1; stroke-dasharray: 3 3; }}
  .line {{ fill: none; stroke-width: 2; stroke-linecap: round;
           stroke-linejoin: round; }}
  .dot {{ stroke: var(--surface-1); stroke-width: 2; }}
  .hit {{ fill: transparent; }}
  .direct {{ font-size: 11px; font-weight: 600; }}
  .base {{ font-size: 9px; }}
</style>
<rect width="100%" height="100%" fill="var(--surface-1)"/>
<text class="title" x="{MARGIN_X}" y="28">Historico das carteiras — {_esc(date)}</text>
<text class="subtitle" x="{MARGIN_X}" y="46">Base 100 na data de inicio de cada carteira. Paper trading.</text>
{chr(10).join(legend)}
{chr(10).join(body)}
</svg>
'''


def write_chart(date: str, panels: list[tuple[str, dict, str, str | None]],
                reports_dir: Path) -> Path:
    svg = build_svg(date, panels)
    daily_dir = reports_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)
    path = daily_dir / f"{date}-grafico.svg"
    path.write_text(svg, encoding="utf-8")
    (reports_dir / "GRAFICO_ATUAL.svg").write_text(svg, encoding="utf-8")
    return path
