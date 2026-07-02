from __future__ import annotations

import hashlib
import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"

SAFETY_FLAGS: dict[str, Any] = {
    "app_mode": APP_MODE,
    "research_allowed": True,
    "hypothetical_only": True,
    "api_key_required": False,
    "api_key_present": False,
    "account_connection_required": False,
    "authenticated_connection_used": False,
    "orders_allowed": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "trading_signal_generated": False,
    "executable_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "portfolio_decision_generated": False,
    "operational_decision_allowed": False,
}

FORBIDDEN_RENDERED_PHRASES = (
    "position sizing",
    "use real capital",
    "execute trade",
    "trading signal:",
    "buy signal",
    "sell signal",
    "recommended allocation",
)


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip() for s in symbols.split(",") if s.strip()]
    return [str(s).strip() for s in symbols if str(s).strip()]


def _repo_root() -> Path:
    cwd = Path.cwd().resolve()
    if (cwd / "crypto_decision_lab").is_dir():
        return cwd
    if cwd.name == "crypto_decision_lab" and (cwd.parent / "crypto_decision_lab").is_dir():
        return cwd.parent
    return cwd


def _resolve_path(value: str | Path) -> Path:
    p = Path(value)
    if p.exists():
        return p
    root = _repo_root()
    candidates = [root / p, root / "crypto_decision_lab" / p]
    raw = str(p)
    if raw.startswith("crypto_decision_lab/"):
        stripped = Path(raw.split("/", 1)[1])
        candidates.append(root / "crypto_decision_lab" / stripped)
        candidates.append(root / stripped)
    for c in candidates:
        if c.exists():
            return c
    return p


def _load_json(path: str | Path) -> dict[str, Any]:
    p = _resolve_path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _file_sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "UNAVAILABLE"


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _discover_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not reports:
        return rows
    seen: set[str] = set()
    for item in reports:
        p = _resolve_path(item)
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        payload = _load_json(p)
        if payload:
            rows.append(
                {
                    "path": str(p),
                    "status": "REPORT_PRESENT",
                    "report_name": str(payload.get("report_name") or payload.get("schema") or p.stem),
                    "gate_answer": str(payload.get("gate_answer") or "UNKNOWN_RESEARCH_ONLY"),
                    "sha256": str(payload.get("report_payload_sha256") or _file_sha(p))[:16],
                    "dataset_row_count": _as_int(payload.get("dataset_row_count") or payload.get("row_count") or 0),
                    "split_count": _as_int(payload.get("split_count") or payload.get("walk_forward_split_count") or 0),
                    "score": _as_float(
                        payload.get("mean_coverage_score")
                        or payload.get("mean_quality_score")
                        or payload.get("mean_audit_score")
                        or payload.get("mean_research_readiness_score")
                        or payload.get("mean_symbol_evidence_score")
                        or payload.get("mean_risk_score")
                        or payload.get("mean_security_score")
                        or 0.0
                    ),
                }
            )
        else:
            rows.append(
                {
                    "path": str(p),
                    "status": "MISSING_OR_UNREADABLE",
                    "report_name": p.stem,
                    "gate_answer": "UNREADABLE_INPUT_REPORT_RESEARCH_ONLY",
                    "sha256": "UNREADABLE",
                    "dataset_row_count": 0,
                    "split_count": 0,
                    "score": 0.0,
                }
            )
    return rows


def _discover_symbol_files(symbol: str) -> list[dict[str, Any]]:
    root = _repo_root()
    safe = symbol.replace("-", "_").replace("/", "_").lower()
    patterns = [
        f"*{symbol}*.json",
        f"*{symbol}*.csv",
        f"*{safe}*.json",
        f"*{safe}*.csv",
    ]
    bases = [
        root / "crypto_decision_lab" / "fixtures",
        root / "crypto_decision_lab" / "data",
        root / "crypto_decision_lab" / "artifacts",
    ]
    found: list[dict[str, Any]] = []
    seen: set[str] = set()
    for base in bases:
        if not base.exists():
            continue
        for pattern in patterns:
            for p in base.rglob(pattern):
                if not p.is_file():
                    continue
                key = str(p)
                if key in seen:
                    continue
                seen.add(key)
                try:
                    size_bytes = p.stat().st_size
                except Exception:
                    size_bytes = 0
                found.append({"path": str(p), "size_bytes": size_bytes, "sha256": _file_sha(p)[:16]})
    return found[:25]


def _manifest_for_symbol(symbol: str, reports: list[dict[str, Any]]) -> dict[str, Any]:
    files = _discover_symbol_files(symbol)
    max_rows = max([r["dataset_row_count"] for r in reports] or [0])
    max_splits = max([r["split_count"] for r in reports] or [0])
    avg_score = sum(r["score"] for r in reports) / len(reports) if reports else 0.0
    criteria = [
        {"criterion_id": "manifest_created", "status": "PASS", "ready": True, "observed": True, "threshold": "true", "blocker": ""},
        {"criterion_id": "source_files_discovered", "status": "PASS" if files else "WARN", "ready": bool(files), "observed": len(files), "threshold": ">= 1 local fixture/cache/data file preferred", "blocker": "Need explicit local fixture/cache/data file lineage for this symbol." if not files else ""},
        {"criterion_id": "dataset_rows_declared", "status": "PASS" if max_rows >= 1000 else "WARN", "ready": max_rows >= 1000, "observed": max_rows, "threshold": ">= 1000 rows preferred", "blocker": "Need explicit row-count evidence from dataset export." if max_rows < 1000 else ""},
        {"criterion_id": "walk_forward_splits_declared", "status": "PASS" if max_splits >= 6 else "WARN", "ready": max_splits >= 6, "observed": max_splits, "threshold": ">= 6 splits preferred", "blocker": "Need explicit walk-forward split evidence." if max_splits < 6 else ""},
        {"criterion_id": "prior_stack_score", "status": "PASS" if avg_score >= 0.60 else "WARN", "ready": avg_score >= 0.60, "observed": round(avg_score, 4), "threshold": ">= 0.60 preferred", "blocker": "Need stronger upstream evidence score." if avg_score < 0.60 else ""},
    ]
    ready = sum(1 for c in criteria if c["ready"])
    score = round(ready / len(criteria), 4)
    return {
        "schema": "qrds.dataset_manifest.v1",
        "symbol": symbol,
        "manifest_status": "CREATED_WITH_PROFILE_GAPS_RESEARCH_ONLY",
        "ready": False,
        "readiness_score": score,
        "criteria_ready_count": ready,
        "criteria_total_count": len(criteria),
        "dataset_row_count": max_rows,
        "walk_forward_split_count": max_splits,
        "source_file_count": len(files),
        "source_files": files,
        "criteria": criteria,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for phrase in FORBIDDEN_RENDERED_PHRASES:
        if phrase in low:
            raise ValueError(f"Operational language is not allowed in Dataset Manifest Pack: {phrase}")


def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(v) for v in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Dataset Manifest Pack

Formal per-symbol dataset manifest packet for the research stack. This page records available lineage and missing profiling evidence; it cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Input reports: {payload['input_report_count']}
- Dataset manifests: {payload['manifest_count']}/{payload['symbol_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean manifest score: {payload['mean_manifest_score']}
- Symbols: {', '.join(payload['symbols'])}

Research-only guardrail: no execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.

## Manifest rows

{_md_table(['symbol', 'source_files', 'rows', 'splits', 'score', 'status'], [[m['symbol'], m['source_file_count'], m['dataset_row_count'], m['walk_forward_split_count'], m['readiness_score'], m['manifest_status']] for m in payload['manifests']])}

## Input reports

{_md_table(['report_name', 'status', 'gate_answer', 'sha256'], [[r['report_name'], r['status'], r['gate_answer'], r['sha256']] for r in payload['input_reports']] if payload['input_reports'] else [['NONE', 'MISSING', 'MISSING_INPUT_REPORT', 'MISSING']])}

## Safety flags

{_md_table(['flag', 'value'], [[k, v] for k, v in payload['safety_flags'].items()])}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(v: Any) -> str:
        return html.escape(str(v))

    manifest_rows = "\n".join(
        f"<tr><td><a href='manifests/{esc(m['symbol'])}.json'>{esc(m['symbol'])}</a></td><td>{esc(m['source_file_count'])}</td><td>{esc(m['dataset_row_count'])}</td><td>{esc(m['walk_forward_split_count'])}</td><td>{esc(m['readiness_score'])}</td><td>{esc(m['manifest_status'])}</td></tr>"
        for m in payload['manifests']
    )
    report_rows = "\n".join(
        f"<tr><td>{esc(r['report_name'])}</td><td>{esc(r['status'])}</td><td>{esc(r['gate_answer'])}</td><td>{esc(r['sha256'])}</td></tr>"
        for r in payload['input_reports']
    ) or "<tr><td>NONE</td><td>MISSING</td><td>MISSING_INPUT_REPORT</td><td>MISSING</td></tr>"
    flags = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in payload['safety_flags'].items())
    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Dataset Manifest Pack</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:#fff;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:#fff;margin:12px 0}} th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px}} th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#fee2e2;padding:6px 10px;font-weight:700}}
a{{color:#1d4ed8}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Dataset Manifest Pack</h2>
<p>Formal per-symbol dataset manifest packet for the research stack. This page records available lineage and missing profiling evidence; it cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Input reports</b><br>{esc(payload['input_report_count'])}</div>
<div class='kpi'><b>Dataset manifests</b><br>{esc(payload['manifest_count'])}/{esc(payload['symbol_count'])}</div>
<div class='kpi'><b>Criteria ready</b><br>{esc(payload['criteria_ready_count'])}/{esc(payload['criteria_total_count'])}</div>
<div class='kpi'><b>Mean manifest score</b><br>{esc(payload['mean_manifest_score'])}</div>
<div class='kpi'><b>Symbols</b><br>{esc(', '.join(payload['symbols']))}</div>
<p class='badge'>Research-only guardrail active</p>
<p>No execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.</p>
</div>
<h2>Manifest rows</h2>
<table><thead><tr><th>symbol</th><th>source files</th><th>rows</th><th>splits</th><th>score</th><th>status</th></tr></thead><tbody>{manifest_rows}</tbody></table>
<h2>Input reports</h2>
<table><thead><tr><th>report</th><th>status</th><th>gate answer</th><th>sha256</th></tr></thead><tbody>{report_rows}</tbody></table>
<h2>Safety flags</h2>
<table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flags}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_dataset_manifest_pack(
    output_dir: str | Path,
    symbols: str | Iterable[str],
    reports: Iterable[str | Path] | None = None,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_dir = out / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)

    symbol_list = _symbols(symbols)
    input_reports = _discover_reports(reports)
    manifests = [_manifest_for_symbol(symbol, input_reports) for symbol in symbol_list]

    for manifest in manifests:
        manifest_payload = dict(manifest)
        manifest_payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        manifest_payload["report_payload_sha256"] = _sha_payload(manifest_payload)
        (manifest_dir / f"{manifest['symbol']}.json").write_text(json.dumps(manifest_payload, indent=2, sort_keys=True), encoding="utf-8")

    criteria_ready = sum(m["criteria_ready_count"] for m in manifests)
    criteria_total = sum(m["criteria_total_count"] for m in manifests)
    mean_score = round(sum(m["readiness_score"] for m in manifests) / len(manifests), 4) if manifests else 0.0

    if not manifests:
        gate_answer = "NO_DATASET_MANIFEST_SYMBOLS_RESEARCH_ONLY"
    elif mean_score >= 0.75:
        gate_answer = "DATASET_MANIFESTS_CREATED_PARTIAL_PROFILE_GAPS_RESEARCH_ONLY"
    else:
        gate_answer = "DATASET_MANIFESTS_CREATED_WITH_PROFILE_GAPS_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.dataset_manifest_pack.v1",
        "report_name": "qrds-dataset-manifest-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "symbol_count": len(symbol_list),
        "manifest_count": len(manifests),
        "input_report_count": len(input_reports),
        "criteria_ready_count": criteria_ready,
        "criteria_total_count": criteria_total,
        "mean_manifest_score": mean_score,
        "manifests": manifests,
        "input_reports": input_reports,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "dataset_manifest_pack.json"
    markdown_path = out / "dataset_manifest_pack.md"
    html_path = out / "index.html"
    index_path = out / "dataset_manifest_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.dataset_manifest_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "symbols": payload["symbols"],
        "symbol_count": payload["symbol_count"],
        "manifest_count": payload["manifest_count"],
        "input_report_count": payload["input_report_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_manifest_score": payload["mean_manifest_score"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "manifest_dir": str(manifest_dir),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index
