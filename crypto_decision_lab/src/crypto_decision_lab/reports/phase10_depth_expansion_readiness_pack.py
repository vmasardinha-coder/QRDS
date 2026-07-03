from __future__ import annotations

import hashlib
import html
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
TARGET_ROWS = 5000
BATCH_SIZE = 1000
REQUIRED_FIELDS = ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"]

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
    "buy now", "sell now", "go long", "go short", "open a position", "close the position",
    "place a trade", "execute a trade", "submit an order", "send an order", "use real money",
    "use live capital", "connect exchange account", "api key required", "authenticated exchange used",
    "orders_generated: true", "real_capital_used: true", "trading_signal_generated: true",
    "executable_signal_generated: true", "operational_decision_allowed: true",
)


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _load_json(root: Path, rel_path: str) -> dict[str, Any]:
    p = root / rel_path
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        d["_present"] = True
        return d
    except Exception:
        return {"_present": False, "gate_answer": "MISSING_RESEARCH_ONLY"}


def _payload(d: dict[str, Any]) -> dict[str, Any]:
    return d.get("payload") if isinstance(d.get("payload"), dict) else {}


def _field(d: dict[str, Any], name: str, default: Any = None) -> Any:
    p = _payload(d)
    if name in d:
        return d[name]
    if name in p:
        return p[name]
    return default


def _as_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def _git_status(root: Path) -> list[str]:
    try:
        proc = subprocess.run(["git", "status", "--short"], cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [x for x in proc.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _criterion(cid: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str = "") -> dict[str, Any]:
    return {"criterion_id": cid, "status": status, "ready": bool(ready), "observed": observed, "threshold": threshold, "blocker": blocker}


def _assert_research_only(text: str) -> None:
    low = text.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language not allowed: {term}")


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def _symbol_rows(root: Path, quality: dict[str, Any]) -> list[dict[str, Any]]:
    qm = _field(quality, "quality_metrics", default={})
    per = qm.get("per_symbol") if isinstance(qm, dict) else None
    out: list[dict[str, Any]] = []
    if isinstance(per, list) and per:
        for row in per:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "UNKNOWN")
            interval = "1h"
            intervals = row.get("intervals")
            if isinstance(intervals, list) and intervals:
                interval = str(intervals[0])
            current = _as_int(row.get("rows"), 0)
            out.append({"symbol": symbol, "interval": interval, "current_rows": current, "target_rows": TARGET_ROWS, "gap_rows": max(TARGET_ROWS - current, 0)})
    if out:
        return out

    collection = _load_json(root, "crypto_decision_lab/artifacts/canonical_data_collection_dry_run/canonical_data_collection_dry_run_index.json")
    jobs = _field(collection, "collection_jobs", default=[])
    if isinstance(jobs, list):
        for job in jobs:
            if not isinstance(job, dict):
                continue
            symbol = str(job.get("symbol") or "UNKNOWN")
            interval = str(job.get("interval") or "1h")
            current = _as_int(job.get("observed_rows"), 0)
            target = _as_int(job.get("target_rows"), TARGET_ROWS)
            out.append({"symbol": symbol, "interval": interval, "current_rows": current, "target_rows": target, "gap_rows": max(target - current, 0)})
    return out


def _build_batches(symbol_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    batches: list[dict[str, Any]] = []
    for row in symbol_rows:
        gap = _as_int(row["gap_rows"], 0)
        n = 1
        while gap > 0:
            rows_requested = min(BATCH_SIZE, gap)
            batches.append({
                "batch_id": f"{row['symbol'].lower().replace('-', '_')}_{row['interval']}_batch_{n:02d}",
                "symbol": row["symbol"],
                "interval": row["interval"],
                "rows_requested": rows_requested,
                "source_mode": "MANUAL_OR_OFFLINE_FILE",
                "accepted_formats": ["jsonl", "csv"],
                "required_fields": REQUIRED_FIELDS,
                "destination": "manual_intake/inbox",
                "canonical_write_allowed": False,
                "network_required": False,
                "auth_required": False,
                "status": "REQUEST_READY_RESEARCH_ONLY",
            })
            gap -= rows_requested
            n += 1
    return batches


def _write_source_requests(root: Path, out: Path, batches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    repo_dir = root / "crypto_decision_lab" / "manual_intake" / "source_requests"
    art_dir = out / "source_requests"
    repo_dir.mkdir(parents=True, exist_ok=True)
    art_dir.mkdir(parents=True, exist_ok=True)

    by_symbol: dict[str, list[dict[str, Any]]] = {}
    for batch in batches:
        by_symbol.setdefault(batch["symbol"], []).append(batch)

    written: list[dict[str, Any]] = []
    for symbol, items in sorted(by_symbol.items()):
        safe = symbol.lower().replace("-", "_")
        payload = {
            "schema": "qrds.phase10_source_request.v1",
            "symbol": symbol,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "REQUEST_READY_RESEARCH_ONLY",
            "destination": "crypto_decision_lab/manual_intake/inbox",
            "required_fields": REQUIRED_FIELDS,
            "batches": items,
            "canonical_write_allowed": False,
            "network_required": False,
            "auth_required": False,
        }
        text = json.dumps(payload, indent=2, sort_keys=True)
        art = art_dir / f"{safe}_source_request.json"
        repo = repo_dir / f"{safe}_source_request.json"
        art.write_text(text, encoding="utf-8")
        repo.write_text(text, encoding="utf-8")
        written.append({"symbol": symbol, "batches": len(items), "artifact_path": str(art), "repo_path": str(repo), "sha256": _sha_text(text)[:16]})
    return written


def _inbox(root: Path) -> dict[str, Any]:
    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    files = [p for p in inbox.glob("*") if p.is_file() and p.suffix.lower() in {".jsonl", ".csv"}]
    return {"inbox_ready": inbox.exists(), "inbox_file_count": len(files), "inbox_path": str(inbox)}


def _station(symbols: list[dict[str, Any]], batches: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "where_we_are": "PHASE_10_DEPTH_EXPANSION_READINESS",
        "main_blocker": "Full-depth dataset remains missing; the system is ready to accept manual/offline files but not to promote them automatically.",
        "next_best_step": "Place real offline JSONL/CSV source files in manual_intake/inbox and rerun the sample intake and quality packs.",
        "symbols": len(symbols),
        "batches": len(batches),
    }


def render_markdown(payload: dict[str, Any]) -> str:
    symbol_rows = [[s["symbol"], s["interval"], s["current_rows"], s["target_rows"], s["gap_rows"]] for s in payload["symbol_depth_plan"]]
    batch_rows = [[b["batch_id"], b["symbol"], b["rows_requested"], b["destination"], b["status"]] for b in payload["batches"][:160]]
    request_rows = [[r["symbol"], r["batches"], r["sha256"], r["repo_path"]] for r in payload["request_files"]]
    criteria_rows = [[c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]] for c in payload["criteria"]]

    md = f"""# QRDS/QOS Phase 10 Depth Expansion Readiness Pack

This bundled pack turns the remaining depth gap into manual/offline source requests and batch plans. It performs no collection and no canonical promotion.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Station

- Where we are: {payload['station']['where_we_are']}
- Main blocker: {payload['station']['main_blocker']}
- Next best step: {payload['station']['next_best_step']}

## Summary

- Prior quality pack present: {payload['prior_quality_pack_present']}
- Inbox ready: {payload['inbox_ready']}
- Inbox files observed: {payload['inbox_file_count']}
- Symbols planned: {payload['symbols_planned']}
- Batches planned: {payload['batches_planned']}
- Source requests written: {payload['source_requests_written']}
- Total current rows: {payload['total_current_rows']}
- Total target rows: {payload['total_target_rows']}
- Total gap rows: {payload['total_gap_rows']}
- Canonical data writes: {payload['canonical_data_writes']}
- Promotion allowed: {payload['promotion_allowed']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean readiness score: {payload['mean_readiness_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Symbol depth plan

{_table(['symbol', 'interval', 'current_rows', 'target_rows', 'gap_rows'], symbol_rows or [['NONE', 'NONE', 0, 0, 0]])}

## Batch plan

{_table(['batch_id', 'symbol', 'rows_requested', 'destination', 'status'], batch_rows or [['NONE', 'NONE', 0, 'MISSING', 'MISSING']])}

## Source request files

{_table(['symbol', 'batches', 'sha256', 'repo_path'], request_rows or [['NONE', 0, 'MISSING', 'MISSING']])}

## Criteria

{_table(['criterion_id', 'status', 'ready', 'observed', 'threshold', 'blocker'], criteria_rows)}

Generated at {payload['generated_at']} • SHA256 {payload['report_payload_sha256']}
"""
    _assert_research_only(md)
    return md


def render_html(payload: dict[str, Any]) -> str:
    def esc(x: Any) -> str:
        return html.escape(str(x))
    cards = [
        ("Station", payload["station"]["where_we_are"]),
        ("Inbox ready", payload["inbox_ready"]),
        ("Symbols", payload["symbols_planned"]),
        ("Batches", payload["batches_planned"]),
        ("Source requests", payload["source_requests_written"]),
        ("Current rows", payload["total_current_rows"]),
        ("Target rows", payload["total_target_rows"]),
        ("Gap rows", payload["total_gap_rows"]),
        ("Promotion allowed", payload["promotion_allowed"]),
        ("Canonical writes", payload["canonical_data_writes"]),
        ("Mean score", payload["mean_readiness_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    symbol_rows = "".join(f"<tr><td>{esc(s['symbol'])}</td><td>{esc(s['interval'])}</td><td>{esc(s['current_rows'])}</td><td>{esc(s['target_rows'])}</td><td>{esc(s['gap_rows'])}</td></tr>" for s in payload["symbol_depth_plan"])
    batch_rows = "".join(f"<tr><td>{esc(b['batch_id'])}</td><td>{esc(b['symbol'])}</td><td>{esc(b['rows_requested'])}</td><td>{esc(b['destination'])}</td><td>{esc(b['status'])}</td></tr>" for b in payload["batches"][:180])
    criteria_rows = "".join(f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>" for c in payload["criteria"])

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Phase 10 Depth Expansion Readiness Pack</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.station{{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0;min-width:150px}}
table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px;vertical-align:top}}
th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#e0f2fe;padding:6px 10px;font-weight:700}}
.blocked{{display:inline-block;border-radius:999px;background:#fee2e2;padding:6px 10px;font-weight:700}}
</style></head>
<body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Phase 10 Depth Expansion Readiness Pack</h2>
<p>This bundled page turns the depth gap into manual/offline source requests and batch plans. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
{card_html}
<p class='badge'>Research-only guardrail active</p>
<p class='blocked'>Canonical promotion remains blocked</p>
<p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p>
</div>
<div class='station'>
<h2>Where we are</h2>
<p><b>{esc(payload['station']['where_we_are'])}</b></p>
<p>Main blocker: {esc(payload['station']['main_blocker'])}</p>
<p>Next best step: {esc(payload['station']['next_best_step'])}</p>
</div>
<h2>Symbol depth plan</h2>
<table><thead><tr><th>symbol</th><th>interval</th><th>current_rows</th><th>target_rows</th><th>gap_rows</th></tr></thead><tbody>{symbol_rows}</tbody></table>
<h2>Batch plan</h2>
<table><thead><tr><th>batch_id</th><th>symbol</th><th>rows_requested</th><th>destination</th><th>status</th></tr></thead><tbody>{batch_rows}</tbody></table>
<h2>Criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_phase10_depth_expansion_readiness_pack(output_dir: str | Path, repo_root: str | Path | None = None, **_: Any) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    quality = _load_json(root, "crypto_decision_lab/artifacts/phase10_sample_quality_promotion_gate_pack/phase10_sample_quality_promotion_gate_pack_index.json")
    symbols = _symbol_rows(root, quality)
    batches = _build_batches(symbols)
    requests = _write_source_requests(root, out, batches)
    inbox = _inbox(root)
    station = _station(symbols, batches)
    git_status = _git_status(root)

    total_current = sum(_as_int(s["current_rows"], 0) for s in symbols)
    total_target = sum(_as_int(s["target_rows"], 0) for s in symbols)
    total_gap = sum(_as_int(s["gap_rows"], 0) for s in symbols)
    canonical_data_writes = 0
    promotion_allowed = False

    criteria = [
        _criterion("prior_quality_pack_present", "PASS" if quality.get("_present") else "FAIL", bool(quality.get("_present")), quality.get("gate_answer", "MISSING"), "10O-10T quality pack present", ""),
        _criterion("inbox_ready", "PASS" if inbox["inbox_ready"] else "FAIL", inbox["inbox_ready"], inbox["inbox_path"], "manual intake inbox exists", ""),
        _criterion("symbols_planned", "PASS" if symbols else "FAIL", bool(symbols), len(symbols), "> 0 symbols", ""),
        _criterion("depth_gap_explicit", "PASS" if total_gap > 0 else "WARN", total_gap > 0, total_gap, "> 0 gap rows", ""),
        _criterion("batches_planned", "PASS" if batches else "FAIL", bool(batches), len(batches), "> 0 batches", ""),
        _criterion("source_requests_written", "PASS" if len(requests) == len(symbols) else "FAIL", len(requests) == len(symbols), len(requests), "one source request per symbol", ""),
        _criterion("offline_only", "PASS", True, "network_required=false; auth_required=false", "offline/manual only", ""),
        _criterion("promotion_blocked", "PASS" if not promotion_allowed else "FAIL", not promotion_allowed, promotion_allowed, "promotion false", ""),
        _criterion("artifact_and_request_only", "PASS" if canonical_data_writes == 0 else "FAIL", canonical_data_writes == 0, canonical_data_writes, "0 canonical writes", ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]
    ready = sum(1 for c in criteria if c["ready"])
    mean = round(ready / len(criteria), 4)

    if quality.get("_present") and symbols and batches and len(requests) == len(symbols) and total_gap > 0:
        gate_answer = "PHASE10_DEPTH_EXPANSION_READINESS_PACK_READY_RESEARCH_ONLY"
    else:
        gate_answer = "PHASE10_DEPTH_EXPANSION_READINESS_PACK_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase10_depth_expansion_readiness_pack.v1",
        "report_name": "qrds-phase10-depth-expansion-readiness-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": station,
        "prior_quality_pack_present": bool(quality.get("_present")),
        "prior_quality_gate_answer": quality.get("gate_answer", "MISSING"),
        "inbox_ready": inbox["inbox_ready"],
        "inbox_file_count": inbox["inbox_file_count"],
        "symbols_planned": len(symbols),
        "batches_planned": len(batches),
        "source_requests_written": len(requests),
        "total_current_rows": total_current,
        "total_target_rows": total_target,
        "total_gap_rows": total_gap,
        "canonical_data_writes": canonical_data_writes,
        "promotion_allowed": promotion_allowed,
        "symbol_depth_plan": symbols,
        "batches": batches,
        "request_files": requests,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready,
        "criteria_total_count": len(criteria),
        "mean_readiness_score": mean,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "phase10_depth_expansion_readiness_pack.json"
    md_path = out / "phase10_depth_expansion_readiness_pack.md"
    html_path = out / "index.html"
    index_path = out / "phase10_depth_expansion_readiness_pack_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.phase10_depth_expansion_readiness_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"]["where_we_are"],
        "prior_quality_pack_present": payload["prior_quality_pack_present"],
        "inbox_ready": payload["inbox_ready"],
        "inbox_file_count": payload["inbox_file_count"],
        "symbols_planned": payload["symbols_planned"],
        "batches_planned": payload["batches_planned"],
        "source_requests_written": payload["source_requests_written"],
        "total_current_rows": payload["total_current_rows"],
        "total_target_rows": payload["total_target_rows"],
        "total_gap_rows": payload["total_gap_rows"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "promotion_allowed": payload["promotion_allowed"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_readiness_score": payload["mean_readiness_score"],
        "report_path": str(report_path),
        "markdown_path": str(md_path),
        "html_path": str(html_path),
        "index_path": str(index_path),
        "serve_entrypoint": str(html_path),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index


build_depth_expansion_pack = build_phase10_depth_expansion_readiness_pack
