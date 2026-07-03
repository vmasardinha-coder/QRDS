from __future__ import annotations

import hashlib
import html
import json
import subprocess
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
    "buy now",
    "sell now",
    "go long",
    "go short",
    "open a position",
    "close the position",
    "place a trade",
    "execute a trade",
    "submit an order",
    "send an order",
    "use real money",
    "use live capital",
    "connect exchange account",
    "api key required",
    "authenticated exchange used",
    "real orders generated: true",
    "orders_generated: true",
    "real_capital_used: true",
    "executable_signal_generated: true",
    "trading_signal_generated: true",
    "operational_decision_allowed: true",
)

DEFAULT_SYMBOLS = ["BTC-USDT", "ETH-USDT", "SOL-USDT"]


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _symbols(symbols: str | Iterable[str] | None) -> list[str]:
    if symbols is None:
        return list(DEFAULT_SYMBOLS)
    if isinstance(symbols, str):
        out = [s.strip() for s in symbols.split(",") if s.strip()]
        return out or list(DEFAULT_SYMBOLS)
    out = [str(s).strip() for s in symbols if str(s).strip()]
    return out or list(DEFAULT_SYMBOLS)


def _git_status(root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=str(root),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return [line for line in proc.stdout.splitlines() if line.strip()]
    except Exception:
        return []


def _load_json(root: Path, rel_path: str) -> dict[str, Any]:
    p = root / rel_path
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        d["_present"] = True
        d["_path"] = rel_path
        return d
    except Exception:
        return {"_present": False, "_path": rel_path}


def _payload(d: dict[str, Any]) -> dict[str, Any]:
    return d.get("payload") if isinstance(d.get("payload"), dict) else {}


def _field(d: dict[str, Any], *names: str, default: Any = 0) -> Any:
    p = _payload(d)
    for name in names:
        if name in d:
            return d.get(name)
        if name in p:
            return p.get(name)
    return default


def _as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _scan_existing_rows(root: Path, symbols: list[str]) -> dict[str, int]:
    data_root = root / "crypto_decision_lab" / "data"
    rows = {s: 0 for s in symbols}
    if not data_root.exists():
        return rows

    def count_payload(obj: Any) -> int:
        if isinstance(obj, list):
            return len(obj)
        if isinstance(obj, dict):
            for key in ("candles", "klines", "rows", "records", "items", "data", "bars", "ohlcv", "prices"):
                value = obj.get(key)
                if isinstance(value, list):
                    return len(value)
                if isinstance(value, dict):
                    nested = count_payload(value)
                    if nested:
                        return nested
            nested_payload = obj.get("payload")
            if isinstance(nested_payload, (dict, list)):
                nested = count_payload(nested_payload)
                if nested:
                    return nested
        return 0

    def symbol_match(path: Path) -> str | None:
        low = str(path).lower()
        for symbol in symbols:
            tokens = {
                symbol.lower(),
                symbol.lower().replace("-", "_"),
                symbol.lower().replace("-", ""),
            }
            if any(token in low for token in tokens):
                return symbol
        return None

    for path in sorted(data_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".csv"}:
            continue
        if "artifacts" in {p.lower() for p in path.parts}:
            continue
        sym = symbol_match(path)
        if not sym:
            continue
        try:
            if path.suffix.lower() == ".json":
                rows[sym] += count_payload(json.loads(path.read_text(encoding="utf-8")))
            elif path.suffix.lower() == ".jsonl":
                rows[sym] += sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
            elif path.suffix.lower() == ".csv":
                rows[sym] += max(len(path.read_text(encoding="utf-8").splitlines()) - 1, 0)
        except Exception:
            continue
    return rows


def _criterion(criterion_id: str, status: str, ready: bool, observed: Any, threshold: str, blocker: str = "") -> dict[str, Any]:
    return {
        "criterion_id": criterion_id,
        "status": status,
        "ready": bool(ready),
        "observed": observed,
        "threshold": threshold,
        "blocker": blocker,
    }


def _assert_research_only(rendered: str) -> None:
    low = rendered.lower()
    for term in FORBIDDEN_RENDERED_PHRASES:
        if term in low:
            raise ValueError(f"Operational language is not allowed in canonical data collection dry run: {term}")


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["|" + "|".join(headers) + "|", "|" + "|".join(["---"] * len(headers)) + "|"]
    for row in rows:
        out.append("|" + "|".join(str(x) for x in row) + "|")
    return "\n".join(out)


def render_markdown(payload: dict[str, Any]) -> str:
    job_rows = [
        [j["symbol"], j["interval"], j["observed_rows"], j["target_rows"], j["gap_rows"], j["priority"], j["output_path"]]
        for j in payload["collection_jobs"]
    ]
    criteria_rows = [
        [c["criterion_id"], c["status"], c["ready"], c["observed"], c["threshold"], c["blocker"]]
        for c in payload["criteria"]
    ]

    md = f"""# QRDS/QOS Canonical Data Collection Dry Run

This artifact creates a dry-run collection queue for canonical research datasets. It records what would be needed; it does not download data, connect accounts, or create live workflow markers.

**Gate answer:** {payload['gate_answer']}

**Policy lock:** {payload['policy_lock']} • **Mode:** {payload['app_mode']}

## Summary

- Collection mode: {payload['collection_mode']}
- Symbols: {', '.join(payload['symbols'])}
- Jobs created: {payload['jobs_created']}
- Ready jobs: {payload['ready_jobs']}
- Total observed rows: {payload['total_observed_rows']}
- Total target rows: {payload['total_target_rows']}
- Total gap rows: {payload['total_gap_rows']}
- Target rows/symbol: {payload['target_rows_per_symbol']}
- Source profile: {payload['source_profile']}
- Git status lines: {payload['git_status_line_count']}
- Criteria ready: {payload['criteria_ready_count']}/{payload['criteria_total_count']}
- Mean dry-run score: {payload['mean_dry_run_score']}

Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.

## Collection jobs

{_table(['symbol', 'interval', 'observed_rows', 'target_rows', 'gap_rows', 'priority', 'output_path'], job_rows)}

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
        ("Collection mode", payload["collection_mode"]),
        ("Jobs created", payload["jobs_created"]),
        ("Ready jobs", payload["ready_jobs"]),
        ("Total observed rows", payload["total_observed_rows"]),
        ("Total target rows", payload["total_target_rows"]),
        ("Total gap rows", payload["total_gap_rows"]),
        ("Target rows/symbol", payload["target_rows_per_symbol"]),
        ("Git status lines", payload["git_status_line_count"]),
        ("Mean score", payload["mean_dry_run_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)

    job_rows = "".join(
        f"<tr><td>{esc(j['symbol'])}</td><td>{esc(j['interval'])}</td><td>{esc(j['observed_rows'])}</td><td>{esc(j['target_rows'])}</td><td>{esc(j['gap_rows'])}</td><td>{esc(j['priority'])}</td><td>{esc(j['output_path'])}</td></tr>"
        for j in payload["collection_jobs"]
    )
    criteria_rows = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td><td>{esc(c['blocker'])}</td></tr>"
        for c in payload["criteria"]
    )

    page = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>QRDS Canonical Data Collection Dry Run</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}
.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}
.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px 8px 8px 0;min-width:150px}}
table{{border-collapse:collapse;width:100%;background:white;margin:14px 0}}
th,td{{border:1px solid #d9deea;padding:8px;text-align:left;font-size:14px;vertical-align:top}}
th{{background:#eef2ff}}
.badge{{display:inline-block;border-radius:999px;background:#e0f2fe;padding:6px 10px;font-weight:700}}
</style></head>
<body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1>
<h2>Canonical Data Collection Dry Run</h2>
<p>This page creates a dry-run collection queue for canonical research datasets. It cannot unlock operational use.</p>
<div class='card'>
<p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p>
<p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>
{card_html}
<p class='badge'>Research-only guardrail active</p>
<p>Safety lock remains active for account access, order flow, execution-style instructions, and live-fund workflow markers.</p>
</div>
<h2>Collection jobs</h2>
<table><thead><tr><th>symbol</th><th>interval</th><th>observed_rows</th><th>target_rows</th><th>gap_rows</th><th>priority</th><th>output_path</th></tr></thead><tbody>{job_rows}</tbody></table>
<h2>Criteria</h2>
<table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th><th>blocker</th></tr></thead><tbody>{criteria_rows}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p>
</body></html>"""
    _assert_research_only(page)
    return page


def build_canonical_data_collection_dry_run(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    symbols: str | Iterable[str] | None = None,
    target_rows_per_symbol: int = 5000,
    interval: str = "1h",
    source_profile: str = "PUBLIC_OR_OFFLINE_RESEARCH_DATA_ONLY",
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    symbol_list = _symbols(symbols)
    git_status = _git_status(root)

    foundation = _load_json(root, "crypto_decision_lab/artifacts/foundation_checkpoint_next_phase/foundation_checkpoint_next_phase_index.json")
    depth_plan = _load_json(root, "crypto_decision_lab/artifacts/data_acquisition_depth_plan/data_acquisition_depth_plan_index.json")
    source_contract = _load_json(root, "crypto_decision_lab/artifacts/data_source_contract/data_source_contract_index.json")

    target_rows = _as_int(_field(depth_plan, "target_rows_per_symbol", "target_rows_symbol", default=target_rows_per_symbol), target_rows_per_symbol)
    local_rows_by_symbol = _scan_existing_rows(root, symbol_list)

    total_depth_plan_rows = _as_int(_field(depth_plan, "total_rows", default=sum(local_rows_by_symbol.values())))
    if sum(local_rows_by_symbol.values()) == 0 and total_depth_plan_rows:
        approx = total_depth_plan_rows // max(len(symbol_list), 1)
        local_rows_by_symbol = {s: approx for s in symbol_list}

    collection_jobs = []
    for symbol in symbol_list:
        observed = int(local_rows_by_symbol.get(symbol, 0))
        gap = max(target_rows - observed, 0)
        priority = "HIGH" if gap > 0 else "COMPLETE"
        clean_symbol = symbol.lower().replace("-", "_")
        output_path = f"crypto_decision_lab/data/research/{clean_symbol}/{interval}/canonical_ohlcv.jsonl"
        collection_jobs.append(
            {
                "symbol": symbol,
                "interval": interval,
                "observed_rows": observed,
                "target_rows": target_rows,
                "gap_rows": gap,
                "priority": priority,
                "source_profile": source_profile,
                "output_path": output_path,
                "required_fields": ["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"],
                "dry_run_only": True,
            }
        )

    total_observed = sum(j["observed_rows"] for j in collection_jobs)
    total_target = sum(j["target_rows"] for j in collection_jobs)
    total_gap = sum(j["gap_rows"] for j in collection_jobs)
    ready_jobs = sum(1 for j in collection_jobs if j["gap_rows"] >= 0 and j["output_path"])

    foundation_ready = "FOUNDATION_CHECKPOINT_READY_FOR_PHASE_10" in str(foundation.get("gate_answer", ""))
    source_contract_ready = "SCHEMA_READY" in str(source_contract.get("gate_answer", ""))

    criteria = [
        _criterion("foundation_checkpoint_ready", "PASS" if foundation_ready else "WARN", foundation_ready, str(foundation.get("gate_answer", "MISSING")), "foundation checkpoint ready", "" if foundation_ready else "Foundation checkpoint should be generated first."),
        _criterion("source_contract_ready", "PASS" if source_contract_ready else "WARN", source_contract_ready, str(source_contract.get("gate_answer", "MISSING")), "source contract schema ready", "" if source_contract_ready else "Data source contract should be ready."),
        _criterion("jobs_created", "PASS" if len(collection_jobs) == len(symbol_list) else "FAIL", len(collection_jobs) == len(symbol_list), f"{len(collection_jobs)}/{len(symbol_list)}", "one job per symbol", ""),
        _criterion("dry_run_only", "PASS", True, "DRY_RUN_ONLY", "no data download or account workflow", ""),
        _criterion("depth_gap_explicit", "PASS" if total_gap > 0 else "WARN", total_gap > 0, total_gap, "> 0 gap rows expected before collection", "" if total_gap > 0 else "No depth gap observed."),
        _criterion("git_status_recorded", "PASS", True, len(git_status), "git status captured", ""),
        _criterion("research_only_lock", "PASS", True, "ACTIVE", "policy lock active", ""),
    ]

    ready_count = sum(1 for c in criteria if c["ready"])
    mean_score = round(ready_count / len(criteria), 4)

    if foundation_ready and source_contract_ready and total_gap > 0:
        gate_answer = "CANONICAL_DATA_COLLECTION_DRY_RUN_READY_RESEARCH_ONLY"
    elif total_gap > 0:
        gate_answer = "CANONICAL_DATA_COLLECTION_DRY_RUN_READY_WITH_FOUNDATION_REVIEW_RESEARCH_ONLY"
    else:
        gate_answer = "CANONICAL_DATA_COLLECTION_DRY_RUN_NO_DEPTH_GAP_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.canonical_data_collection_dry_run.v1",
        "report_name": "qrds-canonical-data-collection-dry-run",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate_answer,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "collection_mode": "DRY_RUN_ONLY",
        "symbols": symbol_list,
        "source_profile": source_profile,
        "interval": interval,
        "target_rows_per_symbol": target_rows,
        "jobs_created": len(collection_jobs),
        "ready_jobs": ready_jobs,
        "total_observed_rows": total_observed,
        "total_target_rows": total_target,
        "total_gap_rows": total_gap,
        "collection_jobs": collection_jobs,
        "foundation_gate_answer": foundation.get("gate_answer", "MISSING"),
        "source_contract_gate_answer": source_contract.get("gate_answer", "MISSING"),
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_dry_run_score": mean_score,
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    report_path = out / "canonical_data_collection_dry_run.json"
    md_path = out / "canonical_data_collection_dry_run.md"
    html_path = out / "index.html"
    index_path = out / "canonical_data_collection_dry_run_index.json"

    report_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    index = {
        "schema": "qrds.canonical_data_collection_dry_run_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "collection_mode": payload["collection_mode"],
        "symbols": payload["symbols"],
        "source_profile": payload["source_profile"],
        "interval": payload["interval"],
        "target_rows_per_symbol": payload["target_rows_per_symbol"],
        "jobs_created": payload["jobs_created"],
        "ready_jobs": payload["ready_jobs"],
        "total_observed_rows": payload["total_observed_rows"],
        "total_target_rows": payload["total_target_rows"],
        "total_gap_rows": payload["total_gap_rows"],
        "git_status_line_count": payload["git_status_line_count"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_dry_run_score": payload["mean_dry_run_score"],
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


build_collection_dry_run = build_canonical_data_collection_dry_run
