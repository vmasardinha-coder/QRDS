#!/usr/bin/env python3
"""QRDS Phase 37 — Export Review Bundle + Single Portal Index.

Research-only export/review package for the Phase 36 unified portal.
It never creates trading signals, recommendations, allocations, orders, shadow decisions,
safe-apply artifacts, canonical writes, or operational decisions.
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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

PHASE = 37
PACK_NAME = "phase37_export_review_bundle_single_portal_index_pack"
GATE_READY = "PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX_READY_RESEARCH_ONLY"
GATE_NEEDS_REVIEW = "PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX_NEEDS_REVIEW_RESEARCH_ONLY"
PHASE36_READY = "PHASE36_UNIFIED_RISK_REGIME_RESEARCH_PORTAL_SHELL_READY_RESEARCH_ONLY"

REQUIRED_PHASE36_PAGES = [
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

REQUIRED_PHASE36_EXPORTS = [
    "unified_portal_manifest.csv",
    "unified_portal_navigation.json",
    "unified_portal_data.json",
    "unified_portal_exports_manifest.csv",
    "unified_portal_safety_status.json",
    "phase36_unified_risk_regime_research_portal_shell_pack.json",
    "phase36_unified_risk_regime_research_portal_shell_pack_index.json",
    "phase36_unified_risk_regime_research_portal_shell_pack.md",
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


def read_json(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def infer_root(raw_root: Optional[str]) -> Path:
    if raw_root:
        root = Path(raw_root).expanduser().resolve()
    else:
        cwd = Path.cwd().resolve()
        root = cwd.parent if cwd.name == "crypto_decision_lab" else cwd
    if root.name == "crypto_decision_lab":
        root = root.parent
    return root


def project_dir(root: Path) -> Path:
    return root / "crypto_decision_lab"


def phase36_score_for_dir(d: Path) -> int:
    score = 0
    for name in REQUIRED_PHASE36_PAGES + REQUIRED_PHASE36_EXPORTS:
        if (d / name).exists():
            score += 1
    # Prefer explicit Phase 36-ish paths.
    lowered = d.as_posix().lower()
    if "phase36" in lowered:
        score += 5
    if "unified" in lowered and "portal" in lowered:
        score += 3
    return score


def find_phase36_portal_dir(root: Path, explicit: Optional[str]) -> Optional[Path]:
    if explicit:
        d = Path(explicit).expanduser()
        if not d.is_absolute():
            d = (root / d).resolve()
        return d if d.exists() else d

    candidates: List[Path] = []
    for base in [root / "artifacts", project_dir(root) / "artifacts", root, project_dir(root)]:
        if not base.exists():
            continue
        # Limit expensive walks while still finding typical artifact folders.
        for d, dirnames, filenames in os.walk(base):
            p = Path(d)
            depth = len(p.relative_to(base).parts) if p != base else 0
            if depth > 5:
                dirnames[:] = []
                continue
            fn = set(filenames)
            if any(name in fn for name in REQUIRED_PHASE36_PAGES) or "unified_portal_data.json" in fn:
                candidates.append(p)
    if not candidates:
        return None
    candidates = sorted(set(candidates), key=phase36_score_for_dir, reverse=True)
    return candidates[0]


def collect_files(portal_dir: Path) -> List[Path]:
    if not portal_dir.exists() or not portal_dir.is_dir():
        return []
    files: List[Path] = []
    for p in portal_dir.rglob("*"):
        if p.is_file():
            if p.name.startswith("."):
                continue
            if "__pycache__" in p.parts:
                continue
            files.append(p)
    return sorted(files)


def classify_kind(path: Path) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix == ".html":
        return "html_page"
    if suffix == ".csv":
        return "csv_export"
    if suffix == ".json":
        if "safety" in name:
            return "safety_json"
        if "manifest" in name:
            return "manifest_json"
        return "json_export"
    if suffix == ".md":
        return "markdown_report"
    if suffix in {".png", ".jpg", ".jpeg", ".svg", ".webp"}:
        return "image_asset"
    return "artifact"


def build_manifest_rows(portal_dir: Path, files: List[Path]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for p in files:
        stat = p.stat()
        rows.append({
            "source_phase": "36",
            "source_relative_path": safe_rel(p, portal_dir),
            "file_name": p.name,
            "kind": classify_kind(p),
            "size_bytes": stat.st_size,
            "mtime_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).replace(microsecond=0).isoformat(),
            "sha256": sha256_file(p),
            "research_only": True,
            "canonical_write": False,
        })
    return rows


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else [
        "source_phase", "source_relative_path", "file_name", "kind", "size_bytes",
        "mtime_utc", "sha256", "research_only", "canonical_write",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def copy_review_sources(output_dir: Path, portal_dir: Path, files: List[Path]) -> List[Dict[str, Any]]:
    copied: List[Dict[str, Any]] = []
    dest_base = output_dir / "source_phase36_portal"
    if dest_base.exists():
        shutil.rmtree(dest_base)
    dest_base.mkdir(parents=True, exist_ok=True)
    for src in files:
        rel = src.relative_to(portal_dir)
        dest = dest_base / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append({
            "source": safe_rel(src, portal_dir),
            "bundle_path": safe_rel(dest, output_dir),
            "sha256": sha256_file(dest),
            "size_bytes": dest.stat().st_size,
        })
    return copied


def parse_phase36_evidence(portal_dir: Optional[Path]) -> Tuple[Dict[str, Any], List[str]]:
    if not portal_dir or not portal_dir.exists():
        return {}, []
    evidence: Dict[str, Any] = {}
    gates: List[str] = []
    for name in [
        "phase36_unified_risk_regime_research_portal_shell_pack.json",
        "unified_portal_data.json",
        "unified_portal_safety_status.json",
    ]:
        p = portal_dir / name
        if p.exists():
            data = read_json(p)
            evidence[name] = data
            # Try common gate/status fields.
            for key in ["gate", "status", "phase_gate", "readiness_gate"]:
                value = data.get(key)
                if isinstance(value, str):
                    gates.append(value)
            text = json.dumps(data, ensure_ascii=False)
            if PHASE36_READY in text:
                gates.append(PHASE36_READY)
    # Also check markdown/html text in a lightweight way.
    for name in ["phase36_unified_risk_regime_research_portal_shell_pack.md", "index.html"]:
        p = portal_dir / name
        if p.exists():
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
                if PHASE36_READY in text:
                    gates.append(PHASE36_READY)
            except Exception:
                pass
    return evidence, sorted(set(gates))


def safety_is_locked(payload: Dict[str, Any]) -> bool:
    for key, expected in SAFETY_LOCK.items():
        if payload.get(key, expected) != expected:
            return False
    for key in FORBIDDEN_TRUE_FLAGS:
        if payload.get(key) is not False:
            return False
    return payload.get("canonical_data_writes") == 0


def merged_safety_from_phase36(evidence: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(SAFETY_LOCK)
    for data in evidence.values():
        if not isinstance(data, dict):
            continue
        # Common direct and nested locations.
        for key, value in data.items():
            if key in merged:
                merged[key] = value
        for nested_key in ["safety", "safety_lock", "policy", "flags"]:
            nested = data.get(nested_key)
            if isinstance(nested, dict):
                for key, value in nested.items():
                    if key in merged:
                        merged[key] = value
    # Phase 37 remains locked even when source evidence is sparse; source deviations are recorded separately.
    return merged


def html_page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang=\"pt-BR\">
<head>
  <meta charset=\"utf-8\">
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ font-family: system-ui, -apple-system, Segoe UI, sans-serif; margin: 0; line-height: 1.45; }}
    header {{ padding: 24px; border-bottom: 1px solid #9994; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 12px; }}
    .card {{ border: 1px solid #9995; border-radius: 14px; padding: 16px; background: #9991; }}
    .ok {{ font-weight: 700; }}
    .warn {{ font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
    th, td {{ border-bottom: 1px solid #9994; padding: 8px; text-align: left; vertical-align: top; }}
    code {{ background: #9992; padding: 2px 5px; border-radius: 6px; }}
    a {{ text-decoration: none; }}
    .small {{ font-size: 0.92rem; opacity: 0.85; }}
  </style>
</head>
<body>
<header>
  <h1>{html.escape(title)}</h1>
  <p class=\"small\">QRDS Gate BTC • research-only • sem sinal, recomendação, alocação, shadow decision, safe-apply ou decisão operacional.</p>
</header>
<main>
{body}
</main>
</body>
</html>
"""


def write_review_html(output_dir: Path, summary: Dict[str, Any], manifest_rows: List[Dict[str, Any]]) -> None:
    gate = summary.get("gate", GATE_NEEDS_REVIEW)
    ready = summary.get("review_bundle_ready") is True
    missing_pages = summary.get("missing_phase36_pages", [])
    missing_exports = summary.get("missing_phase36_exports", [])
    top_rows = manifest_rows[:120]
    rows_html = "\n".join(
        f"<tr><td>{html.escape(str(r['kind']))}</td><td><a href=\"source_phase36_portal/{html.escape(str(r['source_relative_path']))}\">{html.escape(str(r['source_relative_path']))}</a></td><td><code>{html.escape(str(r['sha256'])[:16])}…</code></td><td>{html.escape(str(r['size_bytes']))}</td></tr>"
        for r in top_rows
    ) or "<tr><td colspan='4'>Nenhum artefato de origem coletado.</td></tr>"
    missing_block = ""
    if missing_pages or missing_exports:
        missing_block = "<div class='card'><h2>Pendências</h2>" + \
            f"<p>Pages faltantes: <code>{html.escape(', '.join(missing_pages) or 'nenhuma')}</code></p>" + \
            f"<p>Exports faltantes: <code>{html.escape(', '.join(missing_exports) or 'nenhum')}</code></p></div>"
    body = f"""
<section class=\"grid\">
  <div class=\"card\"><h2>Gate</h2><p><code>{html.escape(str(gate))}</code></p></div>
  <div class=\"card\"><h2>Review bundle</h2><p class=\"{'ok' if ready else 'warn'}\">{html.escape(str(ready))}</p></div>
  <div class=\"card\"><h2>Phase 36 pages</h2><p>{summary.get('present_phase36_page_count', 0)} / {summary.get('required_phase36_page_count', 11)}</p></div>
  <div class=\"card\"><h2>Arquivos com checksum</h2><p>{summary.get('source_file_count', 0)}</p></div>
  <div class=\"card\"><h2>Operacional</h2><p><code>{html.escape(str(summary.get('operational_status')))}</code></p></div>
  <div class=\"card\"><h2>Edge</h2><p><code>{html.escape(str(summary.get('edge_validated')))}</code></p></div>
</section>
{missing_block}
<section class=\"card\">
  <h2>Índice de revisão</h2>
  <ul>
    <li><a href=\"review_bundle_index.json\">review_bundle_index.json</a></li>
    <li><a href=\"review_bundle_manifest.csv\">review_bundle_manifest.csv</a></li>
    <li><a href=\"review_bundle_checksums.json\">review_bundle_checksums.json</a></li>
    <li><a href=\"review_bundle_safety_status.json\">review_bundle_safety_status.json</a></li>
    <li><a href=\"phase37_export_review_bundle_single_portal_index_pack.md\">phase37_export_review_bundle_single_portal_index_pack.md</a></li>
  </ul>
</section>
<section class=\"card\">
  <h2>Artefatos Phase 36 copiados para revisão</h2>
  <table>
    <thead><tr><th>Tipo</th><th>Arquivo</th><th>SHA-256</th><th>Bytes</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
  <p class=\"small\">Tabela limitada visualmente aos primeiros 120 arquivos; o CSV/JSON contém o manifesto completo.</p>
</section>
"""
    html_text = html_page("QRDS Phase 37 • Export Review Bundle", body)
    (output_dir / "review_bundle.html").write_text(html_text, encoding="utf-8")
    # Single portal index: intentionally same stable landing so serving output_dir opens review bundle.
    (output_dir / "index.html").write_text(html_text, encoding="utf-8")


def write_markdown(output_dir: Path, summary: Dict[str, Any]) -> None:
    missing_pages = summary.get("missing_phase36_pages", [])
    missing_exports = summary.get("missing_phase36_exports", [])
    lines = [
        "# QRDS Phase 37 — Export Review Bundle + Single Portal Index",
        "",
        f"Gate: `{summary.get('gate')}`",
        f"Generated at UTC: `{summary.get('generated_at_utc')}`",
        "",
        "## Safety",
        "",
        "This package is research-only. It generates no trading signals, recommendations, allocations, orders, shadow decisions, safe-apply artifacts, canonical writes, or operational decisions.",
        "",
        f"- app_mode: `{summary.get('app_mode')}`",
        f"- policy_lock: `{summary.get('policy_lock')}`",
        f"- operational_status: `{summary.get('operational_status')}`",
        f"- edge_validated: `{summary.get('edge_validated')}`",
        f"- shadow_decision_allowed: `{summary.get('shadow_decision_allowed')}`",
        f"- decision_layer_allowed: `{summary.get('decision_layer_allowed')}`",
        f"- canonical_data_writes: `{summary.get('canonical_data_writes')}`",
        "",
        "## Bundle",
        "",
        f"- review_bundle_ready: `{summary.get('review_bundle_ready')}`",
        f"- required_phase36_page_count: `{summary.get('required_phase36_page_count')}`",
        f"- present_phase36_page_count: `{summary.get('present_phase36_page_count')}`",
        f"- source_file_count: `{summary.get('source_file_count')}`",
        f"- checksum_file_count: `{summary.get('checksum_file_count')}`",
        f"- zip_created: `{summary.get('zip_created')}`",
        "",
        "## Missing inputs",
        "",
        f"- missing_phase36_pages: `{', '.join(missing_pages) if missing_pages else 'none'}`",
        f"- missing_phase36_exports: `{', '.join(missing_exports) if missing_exports else 'none'}`",
        "",
        "## Main outputs",
        "",
        "- `index.html`",
        "- `review_bundle.html`",
        "- `review_bundle_manifest.csv`",
        "- `review_bundle_index.json`",
        "- `review_bundle_checksums.json`",
        "- `review_bundle_safety_status.json`",
        "- `QRDS_PHASE37_EXPORT_REVIEW_BUNDLE_RESEARCH_ONLY.zip` when ready and zip is enabled",
    ]
    (output_dir / f"{PACK_NAME}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def update_project_status(root: Path, summary: Dict[str, Any]) -> None:
    status_path = project_dir(root) / "docs" / "reports" / "PROJECT_STATUS_QRDS_GATE_BTC.md"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    old = status_path.read_text(encoding="utf-8") if status_path.exists() else "# PROJECT STATUS — QRDS Gate BTC\n"
    start = "<!-- PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX:START -->"
    end = "<!-- PHASE37_EXPORT_REVIEW_BUNDLE_SINGLE_PORTAL_INDEX:END -->"
    block = f"""{start}

## Phase 37 — Export Review Bundle + Single Portal Index

Gate: `{summary.get('gate')}`

Generated at UTC: `{summary.get('generated_at_utc')}`

Research-only safety state:

- app_mode: `{summary.get('app_mode')}`
- policy_lock: `{summary.get('policy_lock')}`
- operational_status: `{summary.get('operational_status')}`
- edge_validated: `{summary.get('edge_validated')}`
- edge_operationally_validated: `{summary.get('edge_operationally_validated')}`
- shadow_decision_allowed: `{summary.get('shadow_decision_allowed')}`
- decision_layer_allowed: `{summary.get('decision_layer_allowed')}`
- trading_signal_generated: `{summary.get('trading_signal_generated')}`
- recommendation_generated: `{summary.get('recommendation_generated')}`
- allocation_generated: `{summary.get('allocation_generated')}`
- operational_decision_allowed: `{summary.get('operational_decision_allowed')}`
- safe_apply_allowed: `{summary.get('safe_apply_allowed')}`
- promotion_allowed: `{summary.get('promotion_allowed')}`
- canonical_data_writes: `{summary.get('canonical_data_writes')}`

Review bundle:

- review_bundle_ready: `{summary.get('review_bundle_ready')}`
- required_phase36_page_count: `{summary.get('required_phase36_page_count')}`
- present_phase36_page_count: `{summary.get('present_phase36_page_count')}`
- source_file_count: `{summary.get('source_file_count')}`
- checksum_file_count: `{summary.get('checksum_file_count')}`
- zip_created: `{summary.get('zip_created')}`
- output_dir: `{summary.get('output_dir')}`

Interpretation:

Phase 37 only packages and indexes the Phase 36 unified research portal for review. It does not validate edge, does not create a shadow decision layer, and does not permit operational use.

{end}
"""
    if start in old and end in old:
        before = old.split(start)[0]
        after = old.split(end)[1]
        new = before.rstrip() + "\n\n" + block + "\n" + after.lstrip()
    else:
        new = old.rstrip() + "\n\n" + block + "\n"
    status_path.write_text(new, encoding="utf-8")


def create_zip(output_dir: Path, zip_path: Path) -> None:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(output_dir.rglob("*")):
            if p.is_file() and p.resolve() != zip_path.resolve():
                zf.write(p, p.relative_to(output_dir).as_posix())


def run(args: argparse.Namespace) -> Dict[str, Any]:
    root = infer_root(args.root)
    proj = project_dir(root)
    output_dir = Path(args.output_dir or args.out or (root / "artifacts" / "phase37_export_review_bundle_single_portal_index")).expanduser()
    if not output_dir.is_absolute():
        output_dir = (root / output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    portal_dir = find_phase36_portal_dir(root, args.portal_dir)
    files = collect_files(portal_dir) if portal_dir else []
    evidence, phase36_gates = parse_phase36_evidence(portal_dir)

    phase36_pages_present = [name for name in REQUIRED_PHASE36_PAGES if portal_dir and (portal_dir / name).exists()]
    phase36_exports_present = [name for name in REQUIRED_PHASE36_EXPORTS if portal_dir and (portal_dir / name).exists()]
    missing_pages = [name for name in REQUIRED_PHASE36_PAGES if name not in phase36_pages_present]
    missing_exports = [name for name in REQUIRED_PHASE36_EXPORTS if name not in phase36_exports_present]

    manifest_rows = build_manifest_rows(portal_dir, files) if portal_dir and portal_dir.exists() else []
    copied = copy_review_sources(output_dir, portal_dir, files) if portal_dir and portal_dir.exists() else []

    phase36_ready_evidence = PHASE36_READY in phase36_gates or not args.require_phase36_gate_text
    source_safety = merged_safety_from_phase36(evidence)
    source_safety_locked = safety_is_locked(source_safety)

    ready = (
        portal_dir is not None
        and portal_dir.exists()
        and len(missing_pages) == 0
        and len(missing_exports) == 0
        and phase36_ready_evidence
        and source_safety_locked
    )
    gate = GATE_READY if ready else GATE_NEEDS_REVIEW

    summary: Dict[str, Any] = {
        "phase": PHASE,
        "pack_name": PACK_NAME,
        "gate": gate,
        "generated_at_utc": utc_now_iso(),
        "root": root.as_posix(),
        "project_dir": proj.as_posix(),
        "output_dir": output_dir.as_posix(),
        "phase36_portal_dir": portal_dir.as_posix() if portal_dir else None,
        "phase36_gates_detected": phase36_gates,
        "phase36_ready_evidence": phase36_ready_evidence,
        "review_bundle_ready": ready,
        "required_phase36_page_count": len(REQUIRED_PHASE36_PAGES),
        "present_phase36_page_count": len(phase36_pages_present),
        "missing_phase36_pages": missing_pages,
        "required_phase36_export_count": len(REQUIRED_PHASE36_EXPORTS),
        "present_phase36_export_count": len(phase36_exports_present),
        "missing_phase36_exports": missing_exports,
        "source_file_count": len(files),
        "copied_source_file_count": len(copied),
        "checksum_file_count": len(manifest_rows),
        "zip_created": False,
        "zip_path": None,
        "mean_portal_score": 1.0 if ready else 0.0,
        "notes": [
            "Research-only review/export bundle for Phase 36 unified portal.",
            "No trading signals, recommendations, allocations, orders, shadow decisions, safe-apply artifacts, canonical writes, or operational decisions were generated.",
        ],
        **SAFETY_LOCK,
        "source_phase36_safety_locked": source_safety_locked,
        "source_phase36_safety_observed": source_safety,
    }

    write_csv(output_dir / "review_bundle_manifest.csv", manifest_rows)
    write_json(output_dir / "review_bundle_index.json", summary)
    write_json(output_dir / "review_bundle_checksums.json", {"files": manifest_rows, "generated_at_utc": summary["generated_at_utc"]})
    write_json(output_dir / "review_bundle_safety_status.json", {**SAFETY_LOCK, "gate": gate, "generated_at_utc": summary["generated_at_utc"]})
    write_json(output_dir / f"{PACK_NAME}.json", summary)
    write_json(output_dir / f"{PACK_NAME}_index.json", {"gate": gate, "outputs": sorted([p.name for p in output_dir.iterdir() if p.is_file()])})
    write_review_html(output_dir, summary, manifest_rows)
    write_markdown(output_dir, summary)

    # Re-read output file list after writing core outputs.
    output_manifest_rows = build_manifest_rows(output_dir, [p for p in output_dir.rglob("*") if p.is_file() and p.name != "QRDS_PHASE37_EXPORT_REVIEW_BUNDLE_RESEARCH_ONLY.zip"])
    write_csv(output_dir / "phase37_output_manifest.csv", output_manifest_rows)

    if ready and not args.no_zip:
        zip_path = output_dir / "QRDS_PHASE37_EXPORT_REVIEW_BUNDLE_RESEARCH_ONLY.zip"
        create_zip(output_dir, zip_path)
        summary["zip_created"] = True
        summary["zip_path"] = zip_path.as_posix()
        # Update summary files with zip info.
        write_json(output_dir / "review_bundle_index.json", summary)
        write_json(output_dir / f"{PACK_NAME}.json", summary)
        write_markdown(output_dir, summary)

    update_project_status(root, summary)

    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate QRDS Phase 37 research-only export/review bundle.")
    parser.add_argument("--root", default=None, help="QRDS repository root. Default: current directory or parent if inside crypto_decision_lab.")
    parser.add_argument("--portal-dir", default=None, help="Phase 36 unified portal directory. Auto-detected if omitted.")
    parser.add_argument("--output-dir", default=None, help="Phase 37 output directory.")
    parser.add_argument("--out", default=None, help="Alias for --output-dir.")
    parser.add_argument("--no-zip", action="store_true", help="Skip zip creation even when ready.")
    parser.add_argument("--allow-missing-phase36-gate-text", dest="require_phase36_gate_text", action="store_false", help="Do not require explicit Phase 36 gate text in source evidence.")
    parser.set_defaults(require_phase36_gate_text=True)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    summary = run(args)
    # Missing input is a review state, not a Python crash.
    return 0 if summary.get("gate") in {GATE_READY, GATE_NEEDS_REVIEW} else 1


if __name__ == "__main__":
    raise SystemExit(main())
