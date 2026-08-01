#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

READY_GATE = "PHASE40_PORTAL_VISUAL_QA_ACCESSIBILITY_LINK_AUDIT_READY_RESEARCH_ONLY"
NEEDS_REVIEW_GATE = "PHASE40_PORTAL_VISUAL_QA_ACCESSIBILITY_LINK_AUDIT_NEEDS_REVIEW_RESEARCH_ONLY"
PHASE39_GATE = "PHASE39_INTERPRETATION_READINESS_INFORMATION_ARCHITECTURE_READY_RESEARCH_ONLY"
PHASE39_HOTFIX_GATE = "PHASE39_HOTFIX_FULL_SUITE_CWD_FIXTURE_PATH_BRIDGE_READY_RESEARCH_ONLY"
PHASE38_GATE = "PHASE38_MODERN_RESEARCH_PORTAL_LAYOUT_UX_POLISH_READY_RESEARCH_ONLY"
PHASE37_GATE = "PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX_READY_RESEARCH_ONLY"

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

QA_PAGES = [
    ("index.html", "Overview"),
    ("page_health.html", "Page Health"),
    ("navigation_audit.html", "Navigation Audit"),
    ("accessibility_checklist.html", "Accessibility Checklist"),
    ("content_density.html", "Content Density"),
    ("source_portal_map.html", "Source Portal Map"),
    ("safety_lock.html", "Safety Lock"),
    ("exports_reports.html", "Exports / Reports"),
]

EXPECTED_SOURCE_PAGES = [
    "index.html",
    "data_trust.html",
    "market_snapshot.html",
    "regime_map.html",
    "volatility_risk.html",
    "recent_history.html",
    "sparklines.html",
    "edge_ledger.html",
    "freshness_audit.html",
    "safety_lock.html",
    "exports_reports.html",
]

FORBIDDEN_DECISION_TERMS = [
    "trading_signal_generated: True",
    "recommendation_generated: True",
    "allocation_generated: True",
    "shadow_decision_allowed: True",
    "decision_layer_allowed: True",
    "safe_apply_allowed: True",
    "operational_decision_allowed: True",
    "edge_validated: True",
]


def repo_root_from_file() -> Path:
    here = Path(__file__).resolve()
    return here.parents[2]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def write_json(path: Path, obj: Any) -> None:
    atomic_write(path, json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_csv(path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    tmp.replace(path)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def find_latest_existing(paths: Iterable[Path]) -> Path | None:
    candidates = [p for p in paths if p.exists() and p.is_dir()]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def detect_source_portal(repo_root: Path, explicit: Path | None = None) -> Tuple[Path | None, str, Dict[str, Any]]:
    project_dir = repo_root / "crypto_decision_lab"
    artifacts = project_dir / "artifacts"
    candidates: List[Tuple[str, Path]] = []
    if explicit:
        candidates.append(("explicit", explicit))
    candidates.extend(
        [
            ("phase39", artifacts / "phase39_interpretation_readiness_information_architecture"),
            ("phase38", artifacts / "phase38_modern_research_portal_layout_ux_polish"),
            ("phase37", artifacts / "phase37_export_review_bundle_single_portal_index"),
            ("phase36", artifacts / "phase36_unified_risk_regime_research_portal_shell_pack"),
        ]
    )
    for label, path in candidates:
        if path.exists() and path.is_dir() and (path / "index.html").exists():
            info = {
                "source_label": label,
                "source_path": safe_rel(path, repo_root),
                "index_exists": True,
            }
            return path, label, info
    latest = find_latest_existing(artifacts.glob("phase3*_*/")) if artifacts.exists() else None
    if latest and (latest / "index.html").exists():
        return latest, "latest_phase3x", {
            "source_label": "latest_phase3x",
            "source_path": safe_rel(latest, repo_root),
            "index_exists": True,
        }
    return None, "missing", {"source_label": "missing", "index_exists": False}


def extract_local_links(text: str) -> List[str]:
    links = re.findall(r"(?:href|src)=[\"']([^\"'#?]+)", text, flags=re.IGNORECASE)
    return [link for link in links if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", link) and not link.startswith("/")]


def page_metrics(page: Path, base: Path) -> Dict[str, Any]:
    text = read_text(page)
    title_match = re.search(r"<title>(.*?)</title>", text, flags=re.IGNORECASE | re.DOTALL)
    h1_count = len(re.findall(r"<h1\b", text, flags=re.IGNORECASE))
    nav_count = len(re.findall(r"<nav\b", text, flags=re.IGNORECASE))
    main_count = len(re.findall(r"<main\b", text, flags=re.IGNORECASE))
    safety_mentions = text.count("BLOCKED_RESEARCH_ONLY") + text.count("research-only") + text.count("RESEARCH_ONLY")
    forbidden_hits = [term for term in FORBIDDEN_DECISION_TERMS if term in text]
    local_links = extract_local_links(text)
    broken_links: List[str] = []
    for link in local_links:
        candidate = (page.parent / link).resolve()
        try:
            candidate.relative_to(base.resolve())
        except ValueError:
            broken_links.append(link)
            continue
        if not candidate.exists():
            broken_links.append(link)
    html_weight = len(text.encode("utf-8"))
    word_count = len(re.findall(r"[A-Za-zÀ-ÿ0-9_\-]+", re.sub(r"<[^>]+>", " ", text)))
    has_title = bool(title_match and title_match.group(1).strip())
    accessibility_score = sum(
        [
            has_title,
            h1_count >= 1,
            nav_count >= 1,
            main_count >= 1,
            safety_mentions >= 1,
            len(broken_links) == 0,
        ]
    ) / 6.0
    return {
        "page": safe_rel(page, base),
        "title": title_match.group(1).strip() if title_match else "",
        "exists": page.exists(),
        "html_bytes": html_weight,
        "approx_word_count": word_count,
        "h1_count": h1_count,
        "nav_count": nav_count,
        "main_count": main_count,
        "local_link_count": len(local_links),
        "broken_link_count": len(broken_links),
        "broken_links": ";".join(broken_links),
        "safety_mentions": safety_mentions,
        "forbidden_decision_hits": ";".join(forbidden_hits),
        "accessibility_score": round(accessibility_score, 4),
        "status": "PASS" if len(broken_links) == 0 and not forbidden_hits and has_title and main_count >= 1 else "NEEDS_REVIEW",
    }


def copy_source_portal(source: Path, destination: Path) -> List[Dict[str, Any]]:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    copied: List[Dict[str, Any]] = []
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(source)
        if any(part.startswith(".git") for part in rel.parts):
            continue
        target = destination / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied.append({"source": rel.as_posix(), "target": target.relative_to(destination).as_posix(), "bytes": target.stat().st_size})
    return copied


def shell_html(title: str, body: str, active: str = "") -> str:
    nav_items = []
    for filename, label in QA_PAGES:
        cls = "active" if filename == active else ""
        nav_items.append(f'<a class="{cls}" href="{filename}">{html.escape(label)}</a>')
    nav = "\n".join(nav_items)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(title)} • QRDS Gate BTC</title>
  <link rel="stylesheet" href="assets/phase40.css" />
</head>
<body>
  <aside class="sidebar">
    <div class="brand">QRDS Gate BTC</div>
    <div class="subbrand">Phase 40 • Visual QA</div>
    <nav>{nav}</nav>
    <div class="lock">Safety Lock: ACTIVE<br/>Operational: BLOCKED_RESEARCH_ONLY</div>
  </aside>
  <main class="content">
    {body}
  </main>
</body>
</html>
"""


def badge(value: str, kind: str = "neutral") -> str:
    return f'<span class="badge {kind}">{html.escape(value)}</span>'


def render_table(rows: List[Dict[str, Any]], fields: List[str]) -> str:
    head = "".join(f"<th>{html.escape(field)}</th>" for field in fields)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(row.get(field, '')))}</td>" for field in fields)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<div class='table-wrap'><table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table></div>"


def write_assets(output_dir: Path) -> None:
    css = """
:root { color-scheme: dark; --bg:#09111f; --panel:#111c2f; --panel2:#16243b; --text:#eef4ff; --muted:#9fb2cf; --line:#263a59; --good:#3ddc97; --warn:#ffd166; --bad:#ff6b6b; --accent:#8ab4ff; }
* { box-sizing: border-box; }
body { margin:0; background: radial-gradient(circle at top left, #13284a 0, #09111f 34rem, #060a13 100%); color:var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; }
a { color: var(--accent); text-decoration: none; }
.sidebar { position: fixed; inset:0 auto 0 0; width: 290px; padding: 28px 22px; background: rgba(7,13,24,.88); border-right: 1px solid var(--line); backdrop-filter: blur(14px); overflow:auto; }
.brand { font-size: 22px; font-weight: 800; letter-spacing:.02em; }
.subbrand { color:var(--muted); margin:6px 0 24px; font-size: 13px; }
nav { display:flex; flex-direction:column; gap:8px; }
nav a { display:block; padding:10px 12px; border:1px solid transparent; border-radius:12px; color:var(--muted); }
nav a.active, nav a:hover { background:var(--panel2); color:var(--text); border-color:var(--line); }
.lock { margin-top:24px; padding:14px; border:1px solid var(--line); border-radius:16px; color:var(--muted); font-size:12px; line-height:1.5; }
.content { margin-left:290px; padding:34px; max-width: 1440px; }
.hero { border:1px solid var(--line); border-radius:28px; padding:28px; background: linear-gradient(135deg, rgba(22,36,59,.96), rgba(12,22,39,.92)); box-shadow: 0 24px 60px rgba(0,0,0,.22); }
.hero h1 { margin:0 0 10px; font-size: clamp(30px, 4vw, 52px); line-height: 1; }
.hero p { color:var(--muted); max-width: 900px; line-height:1.6; }
.grid { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap:16px; margin:22px 0; }
.card { border:1px solid var(--line); border-radius:22px; padding:18px; background:rgba(17,28,47,.82); min-height:118px; }
.card h3 { margin:0 0 8px; font-size:15px; color:var(--muted); font-weight:650; }
.metric { font-size:30px; font-weight:800; }
.badge { display:inline-flex; align-items:center; padding:5px 10px; border-radius:999px; border:1px solid var(--line); font-size:12px; margin:2px; }
.badge.good { color:var(--good); border-color:rgba(61,220,151,.35); background:rgba(61,220,151,.08); }
.badge.warn { color:var(--warn); border-color:rgba(255,209,102,.35); background:rgba(255,209,102,.08); }
.badge.bad { color:var(--bad); border-color:rgba(255,107,107,.35); background:rgba(255,107,107,.08); }
.badge.neutral { color:var(--accent); border-color:rgba(138,180,255,.35); background:rgba(138,180,255,.08); }
.section { margin-top:22px; border:1px solid var(--line); border-radius:24px; padding:22px; background:rgba(9,17,31,.74); }
.section h2 { margin-top:0; }
.table-wrap { overflow:auto; border:1px solid var(--line); border-radius:18px; }
table { width:100%; border-collapse: collapse; font-size:13px; }
th, td { padding:11px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { color:var(--muted); background:rgba(255,255,255,.03); position: sticky; top:0; }
.kv { display:grid; grid-template-columns: 280px 1fr; gap:10px; color:var(--muted); }
.kv strong { color:var(--text); }
.callout { border-left:4px solid var(--accent); background:rgba(138,180,255,.08); padding:14px 16px; border-radius:14px; color:var(--muted); line-height:1.6; }
@media (max-width: 980px) { .sidebar { position:relative; width:auto; } .content { margin-left:0; padding:18px; } .grid { grid-template-columns: repeat(2, minmax(0,1fr)); } .kv { grid-template-columns: 1fr; } }
@media (max-width: 620px) { .grid { grid-template-columns: 1fr; } }
""".strip() + "\n"
    atomic_write(output_dir / "assets" / "phase40.css", css)


def create_zip(output_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(output_dir.rglob("*")):
            if path == zip_path or path.is_dir():
                continue
            zf.write(path, path.relative_to(output_dir).as_posix())


def update_project_status(project_dir: Path, status: Dict[str, Any]) -> None:
    report = project_dir / "docs" / "reports" / "PROJECT_STATUS_QRDS_GATE_BTC.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    block = f"""

---

## Phase 40 — Portal Visual QA + Accessibility + Link Audit

- Gate: `{status['gate']}`
- Generated at: `{status['generated_at']}`
- Source portal: `{status.get('source_label')}` / `{status.get('source_path')}`
- QA pages: `{status['qa_page_count']}`
- Source pages found: `{status['source_pages_found']}` / `{status['source_pages_expected']}`
- Broken links detected: `{status['broken_link_count']}`
- Safety lock: `ACTIVE`
- Operational status: `BLOCKED_RESEARCH_ONLY`
- Edge validated: `False`
- canonical_data_writes: `0`
- Notes: visual/readability/accessibility QA only; no signal, recommendation, allocation, shadow decision, safe-apply or operational decision.
""".rstrip() + "\n"
    current = report.read_text(encoding="utf-8", errors="replace") if report.exists() else "# QRDS Gate BTC Project Status\n"
    if "## Phase 40 — Portal Visual QA + Accessibility + Link Audit" not in current:
        atomic_write(report, current.rstrip() + block)


def build_phase40(output_dir: Path, source_portal: Path | None, repo_root: Path) -> Dict[str, Any]:
    project_dir = repo_root / "crypto_decision_lab"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_assets(output_dir)

    source_label = "missing"
    source_info: Dict[str, Any] = {"source_label": "missing", "index_exists": False}
    source_copy_rows: List[Dict[str, Any]] = []
    if source_portal is None:
        source_portal, source_label, source_info = detect_source_portal(repo_root)
    else:
        source_portal, source_label, source_info = detect_source_portal(repo_root, source_portal)

    source_dest = output_dir / "source_portal"
    source_page_rows: List[Dict[str, Any]] = []
    if source_portal and source_portal.exists():
        source_copy_rows = copy_source_portal(source_portal, source_dest)
        html_pages = sorted(source_dest.glob("*.html"))
        for page in html_pages:
            source_page_rows.append(page_metrics(page, source_dest))
    else:
        source_dest.mkdir(parents=True, exist_ok=True)

    expected_rows = []
    for page in EXPECTED_SOURCE_PAGES:
        exists = (source_dest / page).exists()
        expected_rows.append({"page": page, "exists": exists, "status": "FOUND" if exists else "MISSING"})

    generated_at = utc_now()
    source_pages_found = sum(1 for row in expected_rows if row["exists"])
    broken_link_count = sum(int(row.get("broken_link_count", 0)) for row in source_page_rows)
    forbidden_count = sum(1 for row in source_page_rows if row.get("forbidden_decision_hits"))
    source_ready = bool(source_portal and source_portal.exists() and source_pages_found >= 1)
    gate = READY_GATE if source_ready and forbidden_count == 0 else NEEDS_REVIEW_GATE

    qa_summary = {
        **SAFETY_LOCK,
        "phase": 40,
        "slug": "portal_visual_qa_accessibility_link_audit",
        "gate": gate,
        "generated_at": generated_at,
        "source_ready": source_ready,
        "source_label": source_label,
        "source_path": source_info.get("source_path", ""),
        "qa_page_count": len(QA_PAGES),
        "source_pages_expected": len(EXPECTED_SOURCE_PAGES),
        "source_pages_found": source_pages_found,
        "source_html_pages_detected": len(source_page_rows),
        "broken_link_count": broken_link_count,
        "forbidden_decision_hit_count": forbidden_count,
        "visual_qa_ready": gate == READY_GATE,
        "accessibility_review_ready": gate == READY_GATE,
        "link_audit_ready": gate == READY_GATE,
        "interpretation_generated": False,
        "decision_interpretation_generated": False,
    }

    write_csv(output_dir / "phase40_source_expected_pages.csv", expected_rows, ["page", "exists", "status"])
    write_csv(
        output_dir / "phase40_source_page_health.csv",
        source_page_rows,
        [
            "page",
            "title",
            "exists",
            "html_bytes",
            "approx_word_count",
            "h1_count",
            "nav_count",
            "main_count",
            "local_link_count",
            "broken_link_count",
            "broken_links",
            "safety_mentions",
            "forbidden_decision_hits",
            "accessibility_score",
            "status",
        ],
    )
    write_csv(output_dir / "phase40_source_copy_manifest.csv", source_copy_rows, ["source", "target", "bytes"])
    write_json(output_dir / "phase40_source_page_health.json", source_page_rows)
    write_json(output_dir / "phase40_visual_qa_summary.json", qa_summary)
    write_json(output_dir / "phase40_safety_status.json", SAFETY_LOCK | {"gate": gate, "phase": 40})

    checklist = [
        {"check": "Portal base detectado", "status": "PASS" if source_ready else "NEEDS_REVIEW", "notes": source_info.get("source_path", "")},
        {"check": "Páginas fonte esperadas", "status": "PASS" if source_pages_found == len(EXPECTED_SOURCE_PAGES) else "WARN", "notes": f"{source_pages_found}/{len(EXPECTED_SOURCE_PAGES)}"},
        {"check": "Links locais", "status": "PASS" if broken_link_count == 0 else "NEEDS_REVIEW", "notes": f"broken_link_count={broken_link_count}"},
        {"check": "Termos decisórios proibidos", "status": "PASS" if forbidden_count == 0 else "NEEDS_REVIEW", "notes": f"forbidden_decision_hit_count={forbidden_count}"},
        {"check": "Safety lock", "status": "PASS", "notes": "ACTIVE / BLOCKED_RESEARCH_ONLY"},
        {"check": "Canonical writes", "status": "PASS", "notes": "canonical_data_writes=0"},
    ]
    write_json(output_dir / "phase40_accessibility_checklist.json", checklist)
    write_csv(output_dir / "phase40_accessibility_checklist.csv", checklist, ["check", "status", "notes"])

    overview_body = f"""
<section class="hero">
  <h1>Portal Visual QA + Accessibility + Link Audit</h1>
  <p>Camada de acabamento e auditoria visual do QRDS Gate BTC Research Portal. Esta fase valida leitura, navegação, links, densidade de conteúdo e presença explícita do safety lock. Não interpreta como decisão operacional.</p>
  <div>{badge(gate, 'good' if gate == READY_GATE else 'warn')} {badge('BLOCKED_RESEARCH_ONLY', 'warn')} {badge('edge_validated: False', 'neutral')}</div>
</section>
<section class="grid">
  <div class="card"><h3>QA pages</h3><div class="metric">{len(QA_PAGES)}</div></div>
  <div class="card"><h3>Source pages</h3><div class="metric">{source_pages_found}/{len(EXPECTED_SOURCE_PAGES)}</div></div>
  <div class="card"><h3>Broken links</h3><div class="metric">{broken_link_count}</div></div>
  <div class="card"><h3>Forbidden decision hits</h3><div class="metric">{forbidden_count}</div></div>
</section>
<section class="section">
  <h2>Escopo</h2>
  <p class="callout">Phase 40 é QA visual e navegacional. Ela não cria candidato, não faz leitura decisória, não gera sinal, não recomenda compra/venda, não calcula alocação e não promove dados para camada canônica.</p>
</section>
<section class="section"><h2>Checklist</h2>{render_table(checklist, ['check','status','notes'])}</section>
"""
    atomic_write(output_dir / "index.html", shell_html("Phase 40 Overview", overview_body, "index.html"))

    health_body = f"""
<section class="hero"><h1>Page Health</h1><p>Resumo técnico das páginas HTML copiadas do portal fonte.</p></section>
<section class="section">{render_table(source_page_rows, ['page','title','html_bytes','approx_word_count','local_link_count','broken_link_count','safety_mentions','accessibility_score','status'])}</section>
"""
    atomic_write(output_dir / "page_health.html", shell_html("Page Health", health_body, "page_health.html"))

    nav_body = f"""
<section class="hero"><h1>Navigation Audit</h1><p>Auditoria de presença das páginas esperadas do portal unificado moderno.</p></section>
<section class="section">{render_table(expected_rows, ['page','exists','status'])}</section>
"""
    atomic_write(output_dir / "navigation_audit.html", shell_html("Navigation Audit", nav_body, "navigation_audit.html"))

    acc_body = f"""
<section class="hero"><h1>Accessibility Checklist</h1><p>Checklist mínimo de legibilidade: title, H1, main, navegação, safety lock e links locais.</p></section>
<section class="section">{render_table(checklist, ['check','status','notes'])}</section>
"""
    atomic_write(output_dir / "accessibility_checklist.html", shell_html("Accessibility Checklist", acc_body, "accessibility_checklist.html"))

    density_rows = [
        {
            "page": row.get("page"),
            "approx_word_count": row.get("approx_word_count"),
            "html_bytes": row.get("html_bytes"),
            "density_note": "heavy" if int(row.get("approx_word_count", 0) or 0) > 1600 else "normal",
        }
        for row in source_page_rows
    ]
    write_csv(output_dir / "phase40_content_density.csv", density_rows, ["page", "approx_word_count", "html_bytes", "density_note"])
    density_body = f"""
<section class="hero"><h1>Content Density</h1><p>Mapa simples para identificar páginas pesadas que podem precisar de divisão visual futura.</p></section>
<section class="section">{render_table(density_rows, ['page','approx_word_count','html_bytes','density_note'])}</section>
"""
    atomic_write(output_dir / "content_density.html", shell_html("Content Density", density_body, "content_density.html"))

    source_map_rows = [
        {"artifact": row.get("target"), "bytes": row.get("bytes"), "source": row.get("source")}
        for row in source_copy_rows
    ]
    source_map_body = f"""
<section class="hero"><h1>Source Portal Map</h1><p>Mapa de arquivos herdados da fase anterior para revisão visual.</p></section>
<section class="section">{render_table(source_map_rows[:250], ['artifact','bytes','source'])}</section>
"""
    atomic_write(output_dir / "source_portal_map.html", shell_html("Source Portal Map", source_map_body, "source_portal_map.html"))

    safety_rows = [{"flag": k, "value": v} for k, v in (SAFETY_LOCK | {"gate": gate}).items()]
    safety_body = f"""
<section class="hero"><h1>Safety Lock</h1><p>Travas permanentes da camada research-only.</p></section>
<section class="section">{render_table(safety_rows, ['flag','value'])}</section>
"""
    atomic_write(output_dir / "safety_lock.html", shell_html("Safety Lock", safety_body, "safety_lock.html"))

    export_rows = [
        {"artifact": "phase40_visual_qa_summary.json", "kind": "summary", "purpose": "estado consolidado"},
        {"artifact": "phase40_source_page_health.csv", "kind": "csv", "purpose": "saúde das páginas"},
        {"artifact": "phase40_source_expected_pages.csv", "kind": "csv", "purpose": "presença das páginas esperadas"},
        {"artifact": "phase40_accessibility_checklist.csv", "kind": "csv", "purpose": "checklist de acessibilidade"},
        {"artifact": "phase40_content_density.csv", "kind": "csv", "purpose": "densidade de conteúdo"},
        {"artifact": "QRDS_PHASE40_PORTAL_VISUAL_QA_RESEARCH_ONLY.zip", "kind": "zip", "purpose": "bundle de revisão"},
    ]
    exports_body = f"""
<section class="hero"><h1>Exports / Reports</h1><p>Artefatos exportáveis desta fase.</p></section>
<section class="section">{render_table(export_rows, ['artifact','kind','purpose'])}</section>
"""
    atomic_write(output_dir / "exports_reports.html", shell_html("Exports / Reports", exports_body, "exports_reports.html"))

    manifest_rows: List[Dict[str, Any]] = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            manifest_rows.append(
                {
                    "path": safe_rel(path, output_dir),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )
    write_csv(output_dir / "phase40_output_manifest.csv", manifest_rows, ["path", "bytes", "sha256"])
    write_json(output_dir / "phase40_output_manifest.json", manifest_rows)

    checksums = {row["path"]: row["sha256"] for row in manifest_rows}
    write_json(output_dir / "phase40_checksums.json", checksums)

    md = f"""# QRDS Phase 40 — Portal Visual QA + Accessibility + Link Audit

Gate: `{gate}`

Operational status: `BLOCKED_RESEARCH_ONLY`

Edge validated: `False`

canonical_data_writes: `0`

## Resultado

- Source portal: `{source_label}` / `{source_info.get('source_path', '')}`
- QA pages: `{len(QA_PAGES)}`
- Source pages found: `{source_pages_found}` / `{len(EXPECTED_SOURCE_PAGES)}`
- Broken links: `{broken_link_count}`
- Forbidden decision hits: `{forbidden_count}`

## Segurança

Esta fase é apenas acabamento visual, auditoria de navegação, acessibilidade mínima e revisão de links. Não gera sinal, recomendação, alocação, shadow decision, safe-apply ou decisão operacional.
"""
    atomic_write(output_dir / "phase40_portal_visual_qa_accessibility_link_audit.md", md)

    create_zip(output_dir, output_dir / "QRDS_PHASE40_PORTAL_VISUAL_QA_RESEARCH_ONLY.zip")
    # Refresh manifest/checksums after ZIP.
    manifest_rows = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file():
            manifest_rows.append({"path": safe_rel(path, output_dir), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    write_csv(output_dir / "phase40_output_manifest.csv", manifest_rows, ["path", "bytes", "sha256"])
    write_json(output_dir / "phase40_output_manifest.json", manifest_rows)
    write_json(output_dir / "phase40_checksums.json", {row["path"]: row["sha256"] for row in manifest_rows})

    qa_summary["checksum_file_count"] = len(manifest_rows)
    qa_summary["zip_created"] = (output_dir / "QRDS_PHASE40_PORTAL_VISUAL_QA_RESEARCH_ONLY.zip").exists()
    write_json(output_dir / "phase40_visual_qa_summary.json", qa_summary)
    update_project_status(project_dir, qa_summary)
    return qa_summary


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build QRDS Phase 40 visual QA/accessibility/link audit portal.")
    parser.add_argument("--output-dir", "--out", default=None)
    parser.add_argument("--source-portal", "--portal-dir", default=None)
    args = parser.parse_args(argv)
    repo_root = repo_root_from_file()
    project_dir = repo_root / "crypto_decision_lab"
    output_dir = Path(args.output_dir) if args.output_dir else project_dir / "artifacts" / "phase40_portal_visual_qa_accessibility_link_audit"
    if not output_dir.is_absolute():
        output_dir = repo_root / output_dir
    source_portal = Path(args.source_portal) if args.source_portal else None
    if source_portal and not source_portal.is_absolute():
        source_portal = repo_root / source_portal
    summary = build_phase40(output_dir=output_dir, source_portal=source_portal, repo_root=repo_root)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    print(summary["gate"])
    return 0 if summary["gate"] == READY_GATE else 3


if __name__ == "__main__":
    raise SystemExit(main())
