#!/usr/bin/env python3
"""QRDS Phase 38 — Modern Research Portal Layout / UX Polish.

Moderniza a camada visual do portal QRDS Gate BTC sem criar sinal, recomendação,
alocação, shadow decision, safe-apply, promoção canônica ou decisão operacional.
A fase é estritamente research-only e depende do bundle/index da Phase 37.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import os
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PHASE = 38
PACK_NAME = "phase38_modern_research_portal_layout_ux_polish"
TITLE = "QRDS Gate BTC Research Portal"
SUBTITLE = "Modern layout / UX polish • research-only"
GATE_READY = "PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_READY_RESEARCH_ONLY"
GATE_NEEDS_REVIEW = "PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_NEEDS_REVIEW_RESEARCH_ONLY"
PHASE37_READY = "PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX_READY_RESEARCH_ONLY"

SECTION_DEFS: List[Dict[str, str]] = [
    {"slug": "overview", "file": "index.html", "title": "Overview", "nav": "Overview", "kind": "research_dashboard", "priority": "P0", "summary": "Resumo visual do portal unificado, gates e estado research-only."},
    {"slug": "data_trust", "file": "data_trust.html", "title": "Data Trust", "nav": "Data Trust", "kind": "evidence", "priority": "P0", "summary": "Fontes certificadas, pendências externas e trilha de confiança dos dados."},
    {"slug": "market_snapshot", "file": "market_snapshot.html", "title": "Market Snapshot", "nav": "Market Snapshot", "kind": "diagnostic", "priority": "P1", "summary": "Últimas observações por ativo como diagnóstico, sem recomendação."},
    {"slug": "regime_map", "file": "regime_map.html", "title": "Regime Map", "nav": "Regime Map", "kind": "diagnostic", "priority": "P1", "summary": "Mapa de regimes de pesquisa; labels não são sinais."},
    {"slug": "volatility_risk", "file": "volatility_risk.html", "title": "Volatility Risk", "nav": "Volatility Risk", "kind": "risk", "priority": "P1", "summary": "Painéis de volatilidade e risco, ainda sem edge operacional."},
    {"slug": "recent_history", "file": "recent_history.html", "title": "Recent History", "nav": "Recent History", "kind": "timeline", "priority": "P2", "summary": "Histórico recente do consenso para leitura e auditoria."},
    {"slug": "sparklines", "file": "sparklines.html", "title": "Sparklines", "nav": "Sparklines", "kind": "visual", "priority": "P2", "summary": "Sparklines compactos para navegação visual do estado recente."},
    {"slug": "edge_ledger", "file": "edge_ledger.html", "title": "Edge Evidence Ledger", "nav": "Edge Ledger", "kind": "evidence", "priority": "P0", "summary": "Evidência de edge, candidatos reprovados e bloqueios de promoção."},
    {"slug": "freshness_audit", "file": "freshness_audit.html", "title": "Freshness / Audit", "nav": "Freshness / Audit", "kind": "audit", "priority": "P1", "summary": "Freshness, checks, manifesto e rastreabilidade do portal."},
    {"slug": "safety_lock", "file": "safety_lock.html", "title": "Safety Lock", "nav": "Safety Lock", "kind": "safety", "priority": "P0", "summary": "Travas obrigatórias research-only sempre visíveis."},
    {"slug": "exports_reports", "file": "exports_reports.html", "title": "Exports / Reports", "nav": "Exports / Reports", "kind": "exports", "priority": "P2", "summary": "Arquivos exportáveis, bundles, manifestos e relatórios."},
]

SAFETY_LOCK: Dict[str, Any] = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

FORBIDDEN_TRUE_FLAGS = [
    "edge_validated",
    "edge_operationally_validated",
    "shadow_decision_allowed",
    "decision_layer_allowed",
    "trading_signal_generated",
    "recommendation_generated",
    "allocation_generated",
    "operational_decision_allowed",
    "safe_apply_allowed",
    "promotion_allowed",
]

TEXT_EXTS = {".html", ".json", ".csv", ".md", ".txt", ".css", ".js"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def infer_root(raw_root: Optional[str]) -> Path:
    root = Path(raw_root).expanduser().resolve() if raw_root else Path.cwd().resolve()
    if root.name == "crypto_decision_lab":
        root = root.parent
    return root


def project_dir(root: Path) -> Path:
    return root / "crypto_decision_lab"


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_rel(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except Exception:
        return path.name


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTS


def phase37_score_for_dir(d: Path) -> int:
    names = {p.name for p in d.iterdir()} if d.exists() and d.is_dir() else set()
    score = 0
    if "review_bundle_index.json" in names:
        score += 12
    if "review_bundle.html" in names:
        score += 10
    if "phase37_export_review_bundle_single_portal_index_pack.json" in names:
        score += 8
    if "index.html" in names:
        score += 4
    lowered = d.as_posix().lower()
    if "phase37" in lowered:
        score += 6
    if "review" in lowered and "bundle" in lowered:
        score += 3
    return score


def find_phase37_dir(root: Path, explicit: Optional[str]) -> Optional[Path]:
    if explicit:
        candidate = Path(explicit).expanduser()
        if not candidate.is_absolute():
            candidate = (root / candidate).resolve()
        return candidate

    candidates: List[Path] = []
    bases = [root / "artifacts", project_dir(root) / "artifacts", root, project_dir(root)]
    for base in bases:
        if not base.exists():
            continue
        for d, dirnames, filenames in os.walk(base):
            p = Path(d)
            try:
                depth = len(p.relative_to(base).parts) if p != base else 0
            except Exception:
                depth = 0
            if depth > 5:
                dirnames[:] = []
                continue
            fn = set(filenames)
            if {"review_bundle_index.json", "review_bundle.html", "phase37_export_review_bundle_single_portal_index_pack.json"} & fn:
                candidates.append(p)
    if not candidates:
        return None
    return sorted(set(candidates), key=phase37_score_for_dir, reverse=True)[0]


def text_contains_gate(path: Path, gate: str) -> bool:
    if not path.exists() or not is_text_file(path):
        return False
    try:
        return gate in path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return False


def phase37_gate_seen(phase37_dir: Optional[Path]) -> bool:
    if phase37_dir is None or not phase37_dir.exists():
        return False
    for p in phase37_dir.rglob("*"):
        if p.is_file() and is_text_file(p) and text_contains_gate(p, PHASE37_READY):
            return True
    return False


def infer_phase36_pages_from_phase37(phase37_dir: Optional[Path]) -> Tuple[int, List[str]]:
    if phase37_dir is None or not phase37_dir.exists():
        return 0, []
    expected = [section["file"] for section in SECTION_DEFS]
    found = set()
    for file_name in expected:
        if (phase37_dir / file_name).exists():
            found.add(file_name)
        if (phase37_dir / "source_phase36_portal" / file_name).exists():
            found.add(file_name)
        if (phase37_dir / "source_phase37_review_bundle" / file_name).exists():
            found.add(file_name)
    # Use Phase 37 index if it has the explicit count from the approved run.
    for index_name in ["review_bundle_index.json", "phase37_export_review_bundle_single_portal_index_pack.json"]:
        data = read_json(phase37_dir / index_name)
        for key in ["phase36_pages_present", "phase36_page_count", "required_pages_present", "phase36_pages"]:
            value = data.get(key)
            if isinstance(value, int) and value >= len(expected):
                return len(expected), expected
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, str) and Path(item).name in expected:
                        found.add(Path(item).name)
                    if isinstance(item, dict):
                        name = Path(str(item.get("file") or item.get("path") or "")).name
                        if name in expected:
                            found.add(name)
    return len(found), sorted(found)


def collect_copyable_files(src: Path, max_files: int = 400) -> List[Path]:
    if not src.exists() or not src.is_dir():
        return []
    files: List[Path] = []
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src).as_posix()
        if any(part.startswith(".") for part in p.relative_to(src).parts):
            continue
        if "__pycache__" in rel or rel.endswith(".pyc"):
            continue
        if p.name.endswith(".bak"):
            continue
        if p.stat().st_size > 15 * 1024 * 1024:
            continue
        if p.suffix.lower() in TEXT_EXTS or p.suffix.lower() == ".zip":
            files.append(p)
        if len(files) >= max_files:
            break
    return files


def copy_source_bundle(phase37_dir: Optional[Path], out_dir: Path) -> int:
    if phase37_dir is None or not phase37_dir.exists():
        return 0
    dest = out_dir / "source_phase37_review_bundle"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for p in collect_copyable_files(phase37_dir):
        rel = p.relative_to(phase37_dir)
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        count += 1
    return count


def status_badge(value: Any) -> str:
    text = html.escape(str(value))
    cls = "badge"
    lowered = str(value).lower()
    if lowered in {"false", "0", "blocked_research_only"} or "blocked" in lowered:
        cls += " badge-safe"
    elif lowered in {"true", "ready", "active"} or "ready" in lowered:
        cls += " badge-ready"
    elif "needs" in lowered or "pending" in lowered:
        cls += " badge-review"
    return f'<span class="{cls}">{text}</span>'


def css_text() -> str:
    return """
:root{
  --bg:#090d18; --panel:#111827; --panel2:#0f172a; --text:#e5e7eb; --muted:#94a3b8;
  --line:rgba(148,163,184,.22); --strong:#f8fafc; --accent:#60a5fa; --ok:#34d399;
  --warn:#fbbf24; --danger:#fb7185; --shadow:0 24px 80px rgba(0,0,0,.35);
  --radius:22px; --radius2:14px; --font:Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
}
*{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at top left,#172554 0,#090d18 34%,#030712 100%);color:var(--text);font-family:var(--font);line-height:1.55}
a{color:inherit;text-decoration:none}.layout{display:grid;grid-template-columns:300px 1fr;min-height:100vh}.sidebar{position:sticky;top:0;height:100vh;padding:24px;background:rgba(3,7,18,.74);border-right:1px solid var(--line);backdrop-filter:blur(16px);overflow:auto}.brand{display:flex;gap:12px;align-items:center;margin-bottom:22px}.brand-mark{width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,var(--accent),#22c55e);box-shadow:0 0 40px rgba(96,165,250,.45)}.brand h1{font-size:18px;line-height:1.1;margin:0}.brand p{margin:4px 0 0;color:var(--muted);font-size:12px}.nav{display:flex;flex-direction:column;gap:7px}.nav a{padding:10px 12px;border:1px solid transparent;border-radius:13px;color:#cbd5e1;font-size:14px}.nav a:hover,.nav a.active{background:rgba(96,165,250,.12);border-color:rgba(96,165,250,.28);color:#fff}.main{padding:34px 40px 60px;max-width:1420px;width:100%;margin:0 auto}.hero{position:relative;overflow:hidden;border:1px solid var(--line);border-radius:var(--radius);background:linear-gradient(135deg,rgba(15,23,42,.96),rgba(30,41,59,.74));box-shadow:var(--shadow);padding:30px;margin-bottom:22px}.hero:after{content:"";position:absolute;inset:auto -80px -120px auto;width:360px;height:360px;background:radial-gradient(circle,rgba(96,165,250,.22),transparent 58%)}.eyebrow{letter-spacing:.14em;text-transform:uppercase;color:var(--accent);font-weight:800;font-size:12px}.hero h2{font-size:34px;line-height:1.06;margin:10px 0 12px}.hero p{color:#cbd5e1;max-width:900px}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:16px}.card{grid-column:span 4;border:1px solid var(--line);border-radius:var(--radius);background:rgba(15,23,42,.82);padding:18px;box-shadow:0 10px 34px rgba(0,0,0,.18)}.card.wide{grid-column:span 8}.card.full{grid-column:1/-1}.card h3{margin:0 0 8px;font-size:17px}.card p,.muted{color:var(--muted)}.metric{font-size:30px;font-weight:850;letter-spacing:-.04em}.kpi-row{display:flex;gap:10px;flex-wrap:wrap}.badge{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:12px;font-weight:800;background:rgba(148,163,184,.10);color:#e5e7eb}.badge-ready{border-color:rgba(52,211,153,.35);background:rgba(52,211,153,.11);color:#bbf7d0}.badge-safe{border-color:rgba(96,165,250,.35);background:rgba(96,165,250,.11);color:#bfdbfe}.badge-review{border-color:rgba(251,191,36,.38);background:rgba(251,191,36,.12);color:#fde68a}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:var(--radius2)}table{border-collapse:collapse;width:100%;font-size:13px}th,td{border-bottom:1px solid var(--line);padding:11px 12px;text-align:left;vertical-align:top}th{color:#cbd5e1;background:rgba(148,163,184,.08)}code{background:rgba(148,163,184,.13);border:1px solid var(--line);border-radius:8px;padding:2px 6px}.footer{margin-top:28px;color:var(--muted);font-size:12px}.callout{border-left:4px solid var(--accent);padding:12px 14px;background:rgba(96,165,250,.09);border-radius:12px}.danger-note{border-left-color:var(--danger);background:rgba(251,113,133,.08)}.source-frame{width:100%;min-height:560px;border:1px solid var(--line);border-radius:18px;background:#fff}.section-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.section-link{display:block;border:1px solid var(--line);border-radius:16px;padding:14px;background:rgba(148,163,184,.07)}.section-link:hover{border-color:rgba(96,165,250,.45);background:rgba(96,165,250,.10)}@media(max-width:980px){.layout{grid-template-columns:1fr}.sidebar{position:relative;height:auto}.main{padding:22px}.card,.card.wide{grid-column:1/-1}.section-list{grid-template-columns:1fr}.hero h2{font-size:27px}}
""".strip() + "\n"


def js_text() -> str:
    return """
(function(){
  const path = location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav a').forEach(a => {
    if ((a.getAttribute('href') || '').split('/').pop() === path) a.classList.add('active');
  });
})();
""".strip() + "\n"


def nav_html(active_file: str) -> str:
    items = []
    for section in SECTION_DEFS:
        active = " active" if section["file"] == active_file else ""
        items.append(f'<a class="{active.strip()}" href="{section["file"]}">{html.escape(section["nav"])}</a>')
    return "\n".join(items)


def layout_page(active_file: str, title: str, body: str, generated_at: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)} • QRDS Gate BTC</title>
  <link rel="stylesheet" href="assets/qrds_modern.css">
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand"><div class="brand-mark"></div><div><h1>QRDS Gate BTC</h1><p>Research-only portal</p></div></div>
      <nav class="nav">{nav_html(active_file)}</nav>
      <div class="footer">
        <p>{status_badge('INTERACTIVE_RESEARCH_ONLY')} {status_badge('BLOCKED_RESEARCH_ONLY')}</p>
        <p>Edge, decisão e operação permanecem bloqueados.</p>
      </div>
    </aside>
    <main class="main">{body}<div class="footer">Gerado em UTC: {html.escape(generated_at)} • Phase 38 • sem sinal, recomendação, alocação, shadow decision, safe-apply ou decisão operacional.</div></main>
  </div>
  <script src="assets/qrds_modern.js"></script>
</body>
</html>
"""


def source_link_for(section_file: str) -> Optional[str]:
    return f"source_phase37_review_bundle/source_phase36_portal/{section_file}"


def section_body(section: Dict[str, str], result: Dict[str, Any], generated_at: str) -> str:
    is_overview = section["file"] == "index.html"
    if is_overview:
        section_cards = "\n".join(
            f'<a class="section-link" href="{s["file"]}"><strong>{html.escape(s["title"])}</strong><br><span class="muted">{html.escape(s["summary"])}</span></a>'
            for s in SECTION_DEFS if s["file"] != "index.html"
        )
        return f"""
<section class="hero">
  <div class="eyebrow">{html.escape(SUBTITLE)}</div>
  <h2>{html.escape(TITLE)}</h2>
  <p>Portal unificado modernizado para leitura, auditoria e navegação visual. Esta camada melhora o layout e a hierarquia das informações, mas não interpreta como decisão operacional.</p>
  <div class="kpi-row">{status_badge(result['gate'])}{status_badge(result['operational_status'])}{status_badge('edge_validated: False')}</div>
</section>
<section class="grid">
  <div class="card"><h3>Modern pages</h3><div class="metric">{result['modern_pages_present']} / {result['required_section_count']}</div><p>Páginas principais com layout moderno.</p></div>
  <div class="card"><h3>Phase 37 ready</h3><div class="metric">{str(result['phase37_ready'])}</div><p>Bundle de revisão/export detectado como base.</p></div>
  <div class="card"><h3>Safety lock</h3><div class="metric">ACTIVE</div><p>Pesquisa interativa; operação bloqueada.</p></div>
  <div class="card wide"><h3>Seções</h3><div class="section-list">{section_cards}</div></div>
  <div class="card"><h3>O que esta fase faz</h3><p>Polimento visual, sidebar, badges, cards, guia de estilo e índice moderno.</p></div>
  <div class="card full"><h3>Trava decisória</h3><div class="callout danger-note">Nenhuma informação desta página deve ser usada como sinal, recomendação, alocação, ordem, safe-apply, shadow decision ou decisão operacional.</div></div>
</section>
"""
    source = source_link_for(section["file"])
    rows = "".join(
        f"<tr><td>{html.escape(k)}</td><td>{status_badge(v) if isinstance(v, bool) or 'status' in k or 'allowed' in k or 'generated' in k else html.escape(str(v))}</td></tr>"
        for k, v in SAFETY_LOCK.items()
    ) if section["slug"] == "safety_lock" else ""
    source_frame = f'<iframe class="source-frame" src="{html.escape(source)}" title="Fonte Phase 37 / Phase 36"></iframe>' if source else ""
    extra = ""
    if section["slug"] == "edge_ledger":
        extra = '<div class="callout danger-note"><strong>Estado dos candidatos:</strong> os 4 candidatos de pesquisa vistos na Phase 26 foram reprovados nas Phases 27–29. Não há edge operacional validado.</div>'
    elif section["slug"] == "safety_lock":
        extra = f'<div class="table-wrap"><table><thead><tr><th>Flag</th><th>Valor</th></tr></thead><tbody>{rows}</tbody></table></div>'
    elif section["slug"] == "exports_reports":
        extra = '<p>Arquivos desta fase: <code>modern_portal_manifest.csv</code>, <code>modern_portal_navigation.json</code>, <code>modern_portal_style_guide.json</code>, <code>phase38_output_manifest.csv</code>, <code>phase38_modern_research_portal_layout_ux_polish.zip</code>.</p>'
    return f"""
<section class="hero">
  <div class="eyebrow">{html.escape(section['kind'])} • {html.escape(section['priority'])}</div>
  <h2>{html.escape(section['title'])}</h2>
  <p>{html.escape(section['summary'])}</p>
  <div class="kpi-row">{status_badge('RESEARCH_ONLY')}{status_badge('BLOCKED_RESEARCH_ONLY')}{status_badge('NO_SIGNAL')}</div>
</section>
<section class="grid">
  <div class="card full"><h3>Leitura desta seção</h3><p>Esta página é uma camada visual moderna sobre o material do portal/bundle anterior. Ela melhora consumo e auditoria, não muda metodologia nem cria decisão.</p>{extra}</div>
  <div class="card full"><h3>Fonte herdada</h3><p class="muted">Renderização embutida do artefato correspondente, quando disponível.</p>{source_frame}</div>
</section>
"""


def write_modern_pages(out_dir: Path, result: Dict[str, Any]) -> int:
    generated_at = result["generated_at_utc"]
    (out_dir / "assets").mkdir(parents=True, exist_ok=True)
    (out_dir / "assets" / "qrds_modern.css").write_text(css_text(), encoding="utf-8")
    (out_dir / "assets" / "qrds_modern.js").write_text(js_text(), encoding="utf-8")
    count = 0
    for section in SECTION_DEFS:
        body = section_body(section, result, generated_at)
        (out_dir / section["file"]).write_text(layout_page(section["file"], section["title"], body, generated_at), encoding="utf-8")
        count += 1
    return count


def write_manifest_csv(path: Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fieldnames})


def build_checksums(out_dir: Path) -> Dict[str, str]:
    checksums: Dict[str, str] = {}
    for p in sorted(out_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = safe_rel(p, out_dir)
        if rel == "phase38_modern_research_portal_layout_ux_polish.zip":
            continue
        if "__pycache__" in rel or p.name.endswith(".pyc"):
            continue
        checksums[rel] = sha256_file(p)
    return checksums


def make_zip(out_dir: Path) -> Optional[Path]:
    zip_path = out_dir / "phase38_modern_research_portal_layout_ux_polish.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(out_dir.rglob("*")):
            if not p.is_file() or p == zip_path:
                continue
            rel = safe_rel(p, out_dir)
            if "__pycache__" in rel or p.name.endswith(".pyc"):
                continue
            zf.write(p, rel)
    return zip_path


def update_project_status(root: Path, result: Dict[str, Any]) -> None:
    report = project_dir(root) / "docs" / "reports" / "PROJECT_STATUS_QRDS_GATE_BTC.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    old = report.read_text(encoding="utf-8") if report.exists() else "# PROJECT STATUS — QRDS Gate BTC\n\n"
    marker_start = "<!-- PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_START -->"
    marker_end = "<!-- PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_END -->"
    block = f"""{marker_start}

## Phase 38 — Modern Research Portal Layout / UX Polish

- Gate: `{result['gate']}`
- Modern portal ready: `{result['modern_portal_ready']}`
- Phase 37 ready: `{result['phase37_ready']}`
- Required sections present: `{result['modern_pages_present']} / {result['required_section_count']}`
- Source files copied: `{result['source_files_copied']}`
- Operational status: `{result['operational_status']}`
- Edge validated: `{result['edge_validated']}`
- Shadow decision allowed: `False`
- Decision layer allowed: `False`
- Trading signal generated: `False`
- Recommendation generated: `False`
- Allocation generated: `False`
- Canonical data writes: `0`
- Generated at UTC: `{result['generated_at_utc']}`

Interpretação: a Phase 38 moderniza layout e UX do portal de pesquisa. Não cria interpretação operacional, recomendação, sinal, alocação, ordem, safe-apply ou promoção canônica.

{marker_end}
"""
    if marker_start in old and marker_end in old:
        before = old.split(marker_start)[0]
        after = old.split(marker_end, 1)[1]
        new = before + block + after
    else:
        new = old.rstrip() + "\n\n" + block + "\n"
    report.write_text(new, encoding="utf-8")


def validate_safety(payload: Dict[str, Any]) -> List[str]:
    issues: List[str] = []
    if payload.get("operational_status") != "BLOCKED_RESEARCH_ONLY":
        issues.append("operational_status_not_blocked")
    if payload.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        issues.append("app_mode_not_research_only")
    if payload.get("policy_lock") != "ACTIVE":
        issues.append("policy_lock_not_active")
    if payload.get("canonical_data_writes") != 0:
        issues.append("canonical_data_writes_not_zero")
    for flag in FORBIDDEN_TRUE_FLAGS:
        if payload.get(flag) is not False:
            issues.append(f"{flag}_not_false")
    return issues


def run(root: Path, output_dir: Optional[Path], phase37_dir_arg: Optional[str]) -> Dict[str, Any]:
    out_dir = output_dir or (root / "artifacts" / PACK_NAME)
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    phase37_dir = find_phase37_dir(root, phase37_dir_arg)
    gate_seen = phase37_gate_seen(phase37_dir)
    phase36_pages_count, phase36_pages_found = infer_phase36_pages_from_phase37(phase37_dir)
    source_files_copied = copy_source_bundle(phase37_dir, out_dir)

    base_result: Dict[str, Any] = {
        **SAFETY_LOCK,
        "phase": PHASE,
        "pack_name": PACK_NAME,
        "title": "QRDS Phase 38 • Modern Research Portal Layout / UX Polish",
        "generated_at_utc": utc_now_iso(),
        "source_phase37_dir": str(phase37_dir) if phase37_dir else None,
        "source_phase37_gate_seen": gate_seen,
        "phase37_ready": bool(gate_seen),
        "phase36_pages_detected_from_phase37": phase36_pages_count,
        "phase36_pages_found": phase36_pages_found,
        "required_section_count": len(SECTION_DEFS),
        "source_files_copied": source_files_copied,
        "layout_system": "modern_sidebar_cards_badges_embedded_source_frames",
        "interpretation_layer_generated": False,
        "decision_interpretation_generated": False,
        "candidate_pool_promoted": False,
        "research_candidate_count_promoted": 0,
        "modern_portal_ready": False,
        "mean_portal_score": 0.0,
    }

    modern_pages_written = write_modern_pages(out_dir, {**base_result, "gate": GATE_NEEDS_REVIEW, "modern_pages_present": len(SECTION_DEFS)})
    modern_pages_present = sum(1 for s in SECTION_DEFS if (out_dir / s["file"]).exists())

    safety_issues = validate_safety(base_result)
    ready = bool(gate_seen and modern_pages_present == len(SECTION_DEFS) and not safety_issues)
    gate = GATE_READY if ready else GATE_NEEDS_REVIEW
    mean_score = 1.0 if ready else round((modern_pages_present / max(1, len(SECTION_DEFS))) * (0.5 if not gate_seen else 0.9), 6)

    result = {
        **base_result,
        "gate": gate,
        "phase37_ready": bool(gate_seen),
        "modern_pages_written": modern_pages_written,
        "modern_pages_present": modern_pages_present,
        "modern_portal_ready": ready,
        "safety_issues": safety_issues,
        "mean_portal_score": mean_score,
    }

    # Rewrite pages with final READY/NEEDS_REVIEW state.
    write_modern_pages(out_dir, result)

    nav_rows = []
    for pos, section in enumerate(SECTION_DEFS, start=1):
        nav_rows.append({
            "position": pos,
            "slug": section["slug"],
            "title": section["title"],
            "file": section["file"],
            "kind": section["kind"],
            "priority": section["priority"],
            "research_only": True,
            "decision_allowed": False,
            "summary": section["summary"],
        })

    write_json(out_dir / "modern_portal_navigation.json", {"sections": nav_rows, "safety_lock": SAFETY_LOCK, "gate": gate})
    write_json(out_dir / "modern_portal_style_guide.json", {
        "phase": PHASE,
        "gate": gate,
        "design_system": "dark_modern_sidebar_card_layout",
        "tokens": ["sidebar", "hero", "cards", "badges", "source_iframe", "safety_callout"],
        "visual_goal": "melhorar leitura e navegação do portal sem interpretação operacional",
        "research_only": True,
    })
    write_json(out_dir / "modern_portal_safety_status.json", {**SAFETY_LOCK, "gate": gate, "safety_issues": safety_issues})
    write_json(out_dir / "phase38_modern_research_portal_layout_ux_polish.json", result)
    write_json(out_dir / "phase38_modern_research_portal_layout_ux_polish_index.json", {
        "gate": gate,
        "output_dir": str(out_dir),
        "entrypoint": "index.html",
        "navigation": "modern_portal_navigation.json",
        "style_guide": "modern_portal_style_guide.json",
        "safety": "modern_portal_safety_status.json",
        "phase37_source": str(phase37_dir) if phase37_dir else None,
        "sections": nav_rows,
    })

    write_manifest_csv(out_dir / "modern_portal_manifest.csv", nav_rows, ["position", "slug", "title", "file", "kind", "priority", "research_only", "decision_allowed", "summary"])

    md = f"""# QRDS Phase 38 — Modern Research Portal Layout / UX Polish

Gate: `{gate}`

- Modern portal ready: `{ready}`
- Phase 37 ready: `{bool(gate_seen)}`
- Modern pages: `{modern_pages_present} / {len(SECTION_DEFS)}`
- Source files copied: `{source_files_copied}`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Edge validated: `False`
- Shadow decision allowed: `False`
- Decision layer allowed: `False`
- Trading signal generated: `False`
- Recommendation generated: `False`
- Allocation generated: `False`
- Canonical data writes: `0`

Esta fase é somente polimento visual/UX do portal de pesquisa. Ela não cria interpretação operacional, sinal, recomendação, alocação, ordem, safe-apply ou decisão.
"""
    (out_dir / "phase38_modern_research_portal_layout_ux_polish.md").write_text(md, encoding="utf-8")

    checksums = build_checksums(out_dir)
    write_json(out_dir / "phase38_checksums.json", {"checksums": checksums, "file_count": len(checksums), "gate": gate})
    manifest_rows = []
    for rel, digest in sorted(checksums.items()):
        p = out_dir / rel
        manifest_rows.append({"path": rel, "bytes": p.stat().st_size if p.exists() else 0, "sha256": digest, "phase": PHASE, "research_only": True})
    write_manifest_csv(out_dir / "phase38_output_manifest.csv", manifest_rows, ["path", "bytes", "sha256", "phase", "research_only"])

    zip_path = make_zip(out_dir)
    result["zip_path"] = str(zip_path) if zip_path else None
    # Store final result after ZIP path is known and checksums exist.
    write_json(out_dir / "phase38_modern_research_portal_layout_ux_polish.json", result)
    update_project_status(root, result)

    print("QRDS Phase 38 • Modern Research Portal Layout / UX Polish")
    print("QRDS Gate BTC • research-only • sem sinal, recomendação, alocação, shadow decision, safe-apply ou decisão operacional.")
    print("")
    print("Gate")
    print(gate)
    print("")
    print("Modern portal")
    print(str(ready))
    print("")
    print("Phase 37 ready")
    print(str(bool(gate_seen)))
    print("")
    print("Modern pages")
    print(f"{modern_pages_present} / {len(SECTION_DEFS)}")
    print("")
    print("Arquivos com checksum")
    print(str(len(checksums)))
    print("")
    print("Operacional")
    print("BLOCKED_RESEARCH_ONLY")
    print("")
    print("Edge")
    print("False")
    if not ready:
        print("")
        print("NEEDS_REVIEW")
        if not gate_seen:
            print("- Phase 37 READY gate não detectado no diretório fonte.")
        for issue in safety_issues:
            print(f"- {issue}")
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate QRDS Phase 38 modern research portal UX polish.")
    parser.add_argument("--root", default=None, help="QRDS repository root. Default: cwd or parent if cwd is crypto_decision_lab.")
    parser.add_argument("--output-dir", "--out", dest="output_dir", default=None, help="Output artifact directory.")
    parser.add_argument("--phase37-dir", "--portal-dir", dest="phase37_dir", default=None, help="Explicit Phase 37 review bundle directory.")
    args = parser.parse_args(argv)

    root = infer_root(args.root)
    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else None
    try:
        run(root, output_dir, args.phase37_dir)
        return 0
    except Exception as exc:
        # Missing/dirty input should not masquerade as certification. Emit NEEDS_REVIEW payload if possible.
        out_dir = output_dir or (root / "artifacts" / PACK_NAME)
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {**SAFETY_LOCK, "phase": PHASE, "gate": GATE_NEEDS_REVIEW, "modern_portal_ready": False, "error": repr(exc), "generated_at_utc": utc_now_iso()}
        write_json(out_dir / "phase38_modern_research_portal_layout_ux_polish.json", payload)
        (out_dir / "index.html").write_text("<!doctype html><html lang='pt-BR'><meta charset='utf-8'><title>QRDS Phase 38 NEEDS_REVIEW</title><body><h1>QRDS Phase 38 NEEDS_REVIEW_RESEARCH_ONLY</h1><p>Falha segura; ver JSON da fase.</p></body></html>", encoding="utf-8")
        print("QRDS Phase 38 • Modern Research Portal Layout / UX Polish")
        print("Gate")
        print(GATE_NEEDS_REVIEW)
        print("NEEDS_REVIEW_SAFE_FAILURE")
        print(repr(exc))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
