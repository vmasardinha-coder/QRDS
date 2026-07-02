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
    "buy signal",
    "sell signal",
    "trading signal:",
)


def _symbols(symbols: str | Iterable[str]) -> list[str]:
    if isinstance(symbols, str):
        return [s.strip() for s in symbols.split(",") if s.strip()]
    return [str(s).strip() for s in symbols if str(s).strip()]


def _repo_candidates(path: str | Path) -> list[Path]:
    p = Path(path)
    raw = str(p)
    candidates = [p, Path.cwd() / p, Path.cwd().parent / p]
    if raw.startswith("crypto_decision_lab/"):
        stripped = Path(raw.split("/", 1)[1])
        candidates.extend([Path.cwd() / stripped, Path.cwd().parent / stripped])
    candidates.extend([
        Path.cwd() / "crypto_decision_lab" / p,
        Path.cwd().parent / "crypto_decision_lab" / p,
    ])
    return candidates


def _resolve_path(path: str | Path) -> Path:
    for candidate in _repo_candidates(path):
        if candidate.exists():
            return candidate
    return Path(path)


def _load_json(path: str | Path) -> dict[str, Any]:
    p = _resolve_path(path)
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {
            "report_name": p.stem,
            "gate_answer": "UNREADABLE_INPUT_REPORT_RESEARCH_ONLY",
            "ready": False,
            "report_payload_sha256": "UNREADABLE",
        }


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


def _kind_from_payload(payload: dict[str, Any], path: str | Path) -> str:
    base = str(payload.get("report_name") or payload.get("schema") or Path(path).stem)
    low = base.lower().replace("-", "_").replace(".", "_")
    mapping = {
        "evidence_quality": "evidence_quality",
        "evidence_drilldown": "evidence_drilldown",
        "evidence_timeline": "evidence_timeline",
        "research_promotion": "research_promotion",
        "human_review": "human_review",
        "oos_validation": "oos_validation",
        "paper_trading": "paper_trading",
        "risk_model": "risk_model",
        "operational_security": "operational_security",
        "data_coverage": "data_coverage",
        "data_quality": "data_quality",
        "data_audit": "data_audit",
        "dataset_manifest": "dataset_manifest",
        "evidence_stack": "evidence_stack",
    }
    for needle, kind in mapping.items():
        if needle in low:
            return kind
    fallback = Path(path).stem.lower().replace("-", "_").replace(".", "_")
    for needle, kind in mapping.items():
        if needle in fallback:
            return kind
    return fallback


def normalize_reports(reports: Iterable[str | Path] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not reports:
        return rows
    seen: set[str] = set()
    for report in reports:
        p = _resolve_path(report)
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        payload = _load_json(p)
        rows.append({
            "kind": _kind_from_payload(payload, p),
            "path": str(p),
            "status": "REPORT_PRESENT" if p.exists() else "MISSING_FILE",
            "ready": bool(payload.get("ready") or payload.get("formal_data_coverage_ready") == "YES"),
            "gate_answer": str(payload.get("gate_answer") or "UNKNOWN_RESEARCH_ONLY"),
            "score": _as_float(
                payload.get("mean_profile_score")
                or payload.get("mean_manifest_score")
                or payload.get("mean_audit_score")
                or payload.get("mean_quality_score")
                or payload.get("mean_coverage_score")
                or payload.get("mean_research_readiness_score")
                or payload.get("mean_symbol_evidence_score")
                or payload.get("mean_latest_score")
                or payload.get("mean_risk_score")
                or payload.get("mean_security_score")
                or payload.get("mean_oos_score")
                or payload.get("mean_paper_score")
                or payload.get("mean_score")
                or 0.0
            ),
            "dataset_manifest_count": _as_int(payload.get("dataset_manifest_count") or payload.get("manifest_count") or 0),
            "dataset_row_count": _as_int(payload.get("dataset_row_count") or payload.get("row_count") or 0),
            "split_count": _as_int(payload.get("split_count") or payload.get("walk_forward_split_count") or 0),
            "sha256": str(payload.get("report_payload_sha256") or payload.get("sha256") or "MISSING")[:16],
        })
    return rows


def _manifest_for_symbol(symbol: str, manifest_payloads: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    for payload in manifest_payloads:
        for key in ("manifest_rows", "symbol_manifest_rows", "dataset_manifests", "symbol_rows", "manifests"):
            rows = payload.get(key)
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, dict):
                        candidates.append(row)
        # Some packs store symbol keys directly.
        symbols_obj = payload.get("symbols")
        if isinstance(symbols_obj, dict):
            row = symbols_obj.get(symbol)
            if isinstance(row, dict):
                candidates.append({"symbol": symbol, **row})

    normalized_symbol = symbol.upper().replace("_", "-")
    for row in candidates:
        row_symbol = str(row.get("symbol") or row.get("asset") or row.get("pair") or "").upper().replace("_", "-")
        if row_symbol == normalized_symbol:
            return row
    return {}


def _profile_rows(symbols: list[str], reports: list[dict[str, Any]], manifest_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    max_rows = max([r["dataset_row_count"] for r in reports] or [0])
    max_splits = max([r["split_count"] for r in reports] or [0])
    rows: list[dict[str, Any]] = []
    for symbol in symbols:
        manifest = _manifest_for_symbol(symbol, manifest_payloads)
        row_count = _as_int(manifest.get("row_count") or manifest.get("dataset_row_count") or max_rows)
        split_count = _as_int(manifest.get("split_count") or manifest.get("walk_forward_split_count") or max_splits)
        null_check = bool(manifest.get("null_check_present") or manifest.get("null_profile_present") or False)
        duplicate_check = bool(manifest.get("duplicate_check_present") or manifest.get("duplicate_profile_present") or False)
        temporal_check = bool(manifest.get("temporal_gap_check_present") or manifest.get("gap_check_present") or False)
        lineage = bool(manifest.get("sha256") or manifest.get("source_hash") or manifest.get("lineage_hash") or any(r["sha256"] != "MISSING" for r in reports))
        ready_points = sum([
            bool(manifest),
            row_count >= 1000,
            split_count >= 6,
            null_check,
            duplicate_check,
            temporal_check,
            lineage,
        ])
        score = round(ready_points / 7, 4)
        rows.append({
            "symbol": symbol,
            "manifest_present": bool(manifest),
            "row_count": row_count,
            "split_count": split_count,
            "null_check_present": null_check,
            "duplicate_check_present": duplicate_check,
            "temporal_gap_check_present": temporal_check,
            "lineage_present": lineage,
            "profile_score": score,
            "status": "DATA_PROFILE_GAPS_REMAIN_RESEARCH_ONLY" if score < 0.75 else "DATA_PROFILE_PARTIAL_RESEARCH_ONLY",
            "ready": score >= 0.75,
            "blocker": "Need explicit row, split, null, duplicate, and temporal-gap profiling evidence." if score < 0.75 else "",
        })
    return rows


def _criterion(criterion_id: str, ready: bool, observed: Any, threshold: str, blocker: str = "") -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": "PASS" if ready else "WARN",
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": blocker,
    }


def _criteria(reports: list[dict[str, Any]], profile_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kinds = {r["kind"] for r in reports}
    report_count = len(reports)
    manifests = sum(1 for row in profile_rows if row["manifest_present"])
    profile_count = len(profile_rows)
    row_ready = sum(1 for row in profile_rows if row["row_count"] >= 1000)
    split_ready = sum(1 for row in profile_rows if row["split_count"] >= 6)
    null_ready = sum(1 for row in profile_rows if row["null_check_present"])
    duplicate_ready = sum(1 for row in profile_rows if row["duplicate_check_present"])
    temporal_ready = sum(1 for row in profile_rows if row["temporal_gap_check_present"])
    lineage_ready = sum(1 for row in profile_rows if row["lineage_present"])

    return [
        _criterion("input_evidence_stack", report_count >= 10, f"{report_count}/10", ">= 10 upstream reports preferred", "Need upstream gate stack." if report_count < 10 else ""),
        _criterion("dataset_manifest_pack", "dataset_manifest" in kinds, "present" if "dataset_manifest" in kinds else "missing", "dataset manifest report present", "Need Dataset Manifest Pack." if "dataset_manifest" not in kinds else ""),
        _criterion("data_audit_pack", "data_audit" in kinds, "present" if "data_audit" in kinds else "missing", "data audit report present", "Need Data Audit Evidence Pack." if "data_audit" not in kinds else ""),
        _criterion("per_symbol_profiles", manifests == profile_count and profile_count > 0, f"{manifests}/{profile_count}", "profile row for every symbol", "Need manifest/profile evidence for every symbol." if manifests != profile_count else ""),
        _criterion("row_volume_profile", row_ready == profile_count and profile_count > 0, f"{row_ready}/{profile_count}", ">= 1000 rows per symbol preferred", "Need explicit row-count evidence." if row_ready != profile_count else ""),
        _criterion("split_profile", split_ready == profile_count and profile_count > 0, f"{split_ready}/{profile_count}", ">= 6 walk-forward splits per symbol preferred", "Need explicit split-count evidence." if split_ready != profile_count else ""),
        _criterion("null_profile", null_ready == profile_count and profile_count > 0, f"{null_ready}/{profile_count}", "null profile per symbol", "Need null/missing-value profile evidence." if null_ready != profile_count else ""),
        _criterion("duplicate_profile", duplicate_ready == profile_count and profile_count > 0, f"{duplicate_ready}/{profile_count}", "duplicate profile per symbol", "Need duplicate-row profile evidence." if duplicate_ready != profile_count else ""),
        _criterion("temporal_gap_profile", temporal_ready == profile_count and profile_count > 0, f"{temporal_ready}/{profile_count}", "temporal continuity profile per symbol", "Need temporal gap profile evidence." if temporal_ready != profile_count else ""),
        _criterion("lineage_profile", lineage_ready == profile_count and profile_count > 0, f"{lineage_ready}/{profile_count}", "lineage hash per symbol or upstream artifact hash", "Need lineage evidence." if lineage_ready != profile_count else ""),
    ]


def _sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in Data Profile Pack: {term}")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(item) for item in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    profile_rows = payload["profile_rows"]
    criteria = payload["criteria"]
    reports = payload["input_reports"]
    md = f"""# QRDS/QOS • Gate BTC • Research-only
## Data Profile Pack

Formal per-symbol data-profile packet for the research stack. This page records row coverage, split coverage, data profiling, lineage, and blockers; it cannot unlock operational use.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Input reports: {payload['input_report_count']}
- Dataset profiles: {payload['dataset_profile_count']}/{len(payload['symbols'])}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean profile score: {payload['mean_profile_score']}
- Symbols: {', '.join(payload['symbols'])}

Research-only guardrail: no execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.

## Symbol profile rows

{_table(['symbol','manifest_present','row_count','split_count','null_check','duplicate_check','temporal_gap_check','lineage','score','ready','blocker'], [[r['symbol'], r['manifest_present'], r['row_count'], r['split_count'], r['null_check_present'], r['duplicate_check_present'], r['temporal_gap_check_present'], r['lineage_present'], r['profile_score'], r['ready'], r['blocker']] for r in profile_rows])}

## Criteria

{_table(['criterion_id','status','ready','observed','threshold','blocker'], [[c['criterion_id'], c['status'], c['ready'], c['observed'], c['threshold'], c['blocker']] for c in criteria])}

## Input reports

{_table(['kind','status','gate_answer','sha256'], [[r['kind'], r['status'], r['gate_answer'], r['sha256']] for r in reports] if reports else [['NONE','MISSING','MISSING_INPUT_REPORT','MISSING']])}

## Safety flags

{_table(['flag','value'], [[k, v] for k, v in SAFETY_FLAGS.items()])}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(value: Any) -> str:
        return html.escape(str(value))

    profiles = "\n".join(
        f"<tr><td>{esc(r['symbol'])}</td><td>{esc(r['manifest_present'])}</td><td>{esc(r['row_count'])}</td><td>{esc(r['split_count'])}</td><td>{esc(r['null_check_present'])}</td><td>{esc(r['duplicate_check_present'])}</td><td>{esc(r['temporal_gap_check_present'])}</td><td>{esc(r['lineage_present'])}</td><td>{esc(r['profile_score'])}</td><td>{esc(r['ready'])}</td><td>{esc(r['blocker'])}</td></tr>"
        for r in payload["profile_rows"]
    )
    criteria = "\n".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )
    reports = "\n".join(
        f"<tr><td>{esc(r['kind'])}</td><td>{esc(r['status'])}</td><td>{esc(r['gate_answer'])}</td><td>{esc(r['sha256'])}</td></tr>"
        for r in payload["input_reports"]
    ) or "<tr><td>NONE</td><td>MISSING</td><td>MISSING_INPUT_REPORT</td><td>MISSING</td></tr>"
    flags = "\n".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>" for k, v in SAFETY_FLAGS.items())

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Data Profile Pack</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0}}
table{{border-collapse:collapse;width:100%;background:white;margin:12px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px}}
th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#fee2e2;padding:6px 10px;font-weight:700}}
</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Data Profile Pack</h2>
<p>Formal per-symbol data-profile packet for the research stack. This page records row coverage, split coverage, data profiling, lineage, and blockers; it cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
<div class='kpi'><b>Input reports</b><br>{esc(payload['input_report_count'])}</div>
<div class='kpi'><b>Dataset profiles</b><br>{esc(payload['dataset_profile_count'])}/{esc(len(payload['symbols']))}</div>
<div class='kpi'><b>Criteria ready</b><br>{esc(payload['criteria_ready_count'])}/{esc(payload['criteria_total_count'])}</div>
<div class='kpi'><b>Mean profile score</b><br>{esc(payload['mean_profile_score'])}</div>
<p class='badge'>Research-only guardrail active</p>
<p>No execution, no exchange account, no portfolio allocation output, no trade instruction, no live-fund workflow.</p>
</div>
<h2>Symbol profile rows</h2><table><thead><tr><th>symbol</th><th>manifest</th><th>rows</th><th>splits</th><th>null</th><th>duplicates</th><th>temporal gaps</th><th>lineage</th><th>score</th><th>ready</th><th>blocker</th></tr></thead><tbody>{profiles}</tbody></table>
<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria}</tbody></table>
<h2>Input reports</h2><table><thead><tr><th>kind</th><th>status</th><th>gate_answer</th><th>sha256</th></tr></thead><tbody>{reports}</tbody></table>
<h2>Safety flags</h2><table><thead><tr><th>flag</th><th>value</th></tr></thead><tbody>{flags}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_data_profile_pack(
    output_dir: str | Path,
    symbols: str | Iterable[str],
    reports: Iterable[str | Path] | None = None,
    manifest_reports: Iterable[str | Path] | None = None,
) -> dict[str, Any]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    symbol_list = _symbols(symbols)
    input_reports = normalize_reports(reports)
    manifest_payloads = [_load_json(p) for p in (manifest_reports or [])]
    # Include manifest-like input reports as payloads too.
    for row in input_reports:
        if row["kind"] == "dataset_manifest":
            manifest_payloads.append(_load_json(row["path"]))

    profile_rows = _profile_rows(symbol_list, input_reports, manifest_payloads)
    criteria = _criteria(input_reports, profile_rows)
    ready_count = sum(1 for c in criteria if c["ready"])
    total_count = len(criteria)
    mean_score = round(sum(r["profile_score"] for r in profile_rows) / len(profile_rows), 4) if profile_rows else 0.0
    dataset_profile_count = sum(1 for r in profile_rows if r["manifest_present"])

    if not input_reports:
        gate_answer = "NO_DATA_PROFILE_NO_INPUT_REPORTS_RESEARCH_ONLY"
    elif dataset_profile_count < len(symbol_list):
        gate_answer = "DATA_PROFILE_PACK_INCOMPLETE_MANIFESTS_REQUIRED_RESEARCH_ONLY"
    elif mean_score < 0.75:
        gate_answer = "DATA_PROFILE_PACK_CREATED_WITH_PROFILE_GAPS_RESEARCH_ONLY"
    else:
        gate_answer = "DATA_PROFILE_PACK_PARTIAL_MORE_AUDIT_REQUIRED_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.data_profile_pack.v1",
        "report_name": "qrds-data-profile-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "symbols": symbol_list,
        "input_report_count": len(input_reports),
        "dataset_profile_count": dataset_profile_count,
        "criteria_ready_count": ready_count,
        "criteria_total_count": total_count,
        "mean_profile_score": mean_score,
        "profile_rows": profile_rows,
        "criteria": criteria,
        "input_reports": input_reports,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha(payload)

    report_path = out / "data_profile_pack.json"
    markdown_path = out / "data_profile_pack.md"
    html_path = out / "index.html"
    index_path = out / "data_profile_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.data_profile_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "symbols": payload["symbols"],
        "input_report_count": payload["input_report_count"],
        "dataset_profile_count": payload["dataset_profile_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_profile_score": payload["mean_profile_score"],
        "report_path": str(report_path),
        "markdown_path": str(markdown_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index
