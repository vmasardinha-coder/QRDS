from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
SOURCE_LABEL = "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY"
EXPECTED_ROWS_TOTAL = 15000

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


def _repo_root(repo_root: str | Path | None = None) -> Path:
    if repo_root:
        return Path(repo_root).resolve()
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "crypto_decision_lab").exists():
            return p
    return here


def _load_json(root: Path, rel: str) -> dict[str, Any]:
    try:
        d = json.loads((root / rel).read_text(encoding="utf-8"))
        d["_present"] = True
        return d
    except Exception:
        return {"_present": False, "gate_answer": "MISSING_RESEARCH_ONLY"}


def _payload(d: dict[str, Any]) -> dict[str, Any]:
    return d.get("payload") if isinstance(d.get("payload"), dict) else {}


def _field(d: dict[str, Any], key: str, default: Any = None) -> Any:
    if key in d:
        return d[key]
    return _payload(d).get(key, default)


def _int(x: Any, default: int = 0) -> int:
    try:
        return int(float(x))
    except Exception:
        return default


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _git_status(root: Path) -> list[str]:
    try:
        p = subprocess.run(["git", "status", "--short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    except Exception:
        return []
    return rows


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except Exception:
        return []


def _discover_rows(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    paths_checked: list[str] = []
    rows: list[dict[str, Any]] = []

    preferred_dirs = [
        root / "crypto_decision_lab" / "artifacts" / "phase11_offline_source_normalizer_pack" / "normalized",
        root / "crypto_decision_lab" / "artifacts" / "phase10_offline_sample_intake_promotion_pack" / "validated_staging",
    ]
    for directory in preferred_dirs:
        if directory.exists():
            files = sorted([p for p in directory.glob("*.jsonl") if p.is_file()])
            if files:
                for p in files:
                    paths_checked.append(str(p))
                    rows.extend(_read_jsonl(p))
                if rows:
                    return rows, paths_checked

    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    if inbox.exists():
        files = sorted(inbox.glob("*_binance_public_klines_1h.csv"))
        for p in files:
            paths_checked.append(str(p))
            rows.extend(_read_csv(p))

    return rows, paths_checked


def _as_float(value: Any) -> float | None:
    try:
        if value in ("", None):
            return None
        return float(value)
    except Exception:
        return None


def _safe_mean(values: list[float]) -> float:
    return statistics.fmean(values) if values else 0.0


def _safe_stdev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) >= 2 else 0.0


def _max_drawdown(closes: list[float]) -> float:
    if not closes:
        return 0.0
    peak = closes[0]
    max_dd = 0.0
    for close in closes:
        if close > peak:
            peak = close
        if peak > 0:
            dd = close / peak - 1.0
            if dd < max_dd:
                max_dd = dd
    return max_dd


def _autocorr_lag1(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    x = values[:-1]
    y = values[1:]
    mx = _safe_mean(x)
    my = _safe_mean(y)
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    denx = math.sqrt(sum((a - mx) ** 2 for a in x))
    deny = math.sqrt(sum((b - my) ** 2 for b in y))
    if denx == 0 or deny == 0:
        return 0.0
    return num / (denx * deny)


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(max(int(round((len(ordered) - 1) * pct)), 0), len(ordered) - 1)
    return ordered[idx]


def _symbol_metrics(symbol: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda r: str(r.get("timestamp", "")))
    closes = [_as_float(r.get("close")) for r in ordered]
    closes_f = [x for x in closes if x is not None and x > 0]
    returns: list[float] = []
    for prev, cur in zip(closes_f[:-1], closes_f[1:]):
        if prev > 0:
            returns.append(cur / prev - 1.0)

    first_close = closes_f[0] if closes_f else 0.0
    last_close = closes_f[-1] if closes_f else 0.0
    cumulative_return = (last_close / first_close - 1.0) if first_close > 0 else 0.0
    mean_return = _safe_mean(returns)
    vol_hourly = _safe_stdev(returns)
    vol_annualized = vol_hourly * math.sqrt(24 * 365)
    positive_rate = (sum(1 for r in returns if r > 0) / len(returns)) if returns else 0.0
    max_dd = _max_drawdown(closes_f)
    ret_p05 = _percentile(returns, 0.05)
    ret_p50 = _percentile(returns, 0.50)
    ret_p95 = _percentile(returns, 0.95)
    lag1 = _autocorr_lag1(returns)

    # Simple descriptive regime buckets, not instructions.
    vol_regime = "HIGH_VOL_RESEARCH_BUCKET" if vol_annualized >= 1.0 else ("MEDIUM_VOL_RESEARCH_BUCKET" if vol_annualized >= 0.55 else "LOW_VOL_RESEARCH_BUCKET")
    drawdown_regime = "LARGE_DRAWDOWN_RESEARCH_BUCKET" if max_dd <= -0.30 else ("MODERATE_DRAWDOWN_RESEARCH_BUCKET" if max_dd <= -0.15 else "SMALL_DRAWDOWN_RESEARCH_BUCKET")

    return {
        "symbol": symbol,
        "rows": len(ordered),
        "return_count": len(returns),
        "first_timestamp": ordered[0].get("timestamp", "MISSING") if ordered else "MISSING",
        "last_timestamp": ordered[-1].get("timestamp", "MISSING") if ordered else "MISSING",
        "first_close": round(first_close, 8),
        "last_close": round(last_close, 8),
        "cumulative_return": round(cumulative_return, 8),
        "mean_return_hourly": round(mean_return, 10),
        "volatility_hourly": round(vol_hourly, 10),
        "volatility_annualized_24x365": round(vol_annualized, 8),
        "positive_return_rate": round(positive_rate, 8),
        "max_drawdown": round(max_dd, 8),
        "return_p05": round(ret_p05, 10),
        "return_p50": round(ret_p50, 10),
        "return_p95": round(ret_p95, 10),
        "autocorr_lag1": round(lag1, 8),
        "volatility_regime_bucket": vol_regime,
        "drawdown_regime_bucket": drawdown_regime,
        "research_only": True,
        "recommendation_generated": False,
        "trading_signal_generated": False,
    }


def _group_by_symbol(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        symbol = str(row.get("symbol", "UNKNOWN"))
        grouped.setdefault(symbol, []).append(row)
    return grouped


def _criterion(cid: str, ok: bool, observed: Any, threshold: str, status: str | None = None) -> dict[str, Any]:
    return {
        "criterion_id": cid,
        "status": status or ("PASS" if ok else "FAIL"),
        "ready": bool(ok),
        "observed": observed,
        "threshold": threshold,
    }


def _write_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Backtest ready", payload["backtest_baseline_ready"]),
        ("Rows analyzed", payload["rows_analyzed"]),
        ("Symbols", payload["symbols_count"]),
        ("Public certified", payload["public_data_research_ready"]),
        ("Operational", payload["operational_status"]),
        ("Promotion", payload["promotion_allowed"]),
        ("Canonical writes", payload["canonical_data_writes"]),
        ("Mean score", payload["mean_backtest_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    rows_html = "".join(
        f"<tr><td>{esc(m['symbol'])}</td><td>{esc(m['rows'])}</td><td>{esc(m['first_timestamp'])}</td><td>{esc(m['last_timestamp'])}</td><td>{esc(m['cumulative_return'])}</td><td>{esc(m['volatility_annualized_24x365'])}</td><td>{esc(m['max_drawdown'])}</td><td>{esc(m['positive_return_rate'])}</td><td>{esc(m['volatility_regime_bucket'])}</td><td>{esc(m['drawdown_regime_bucket'])}</td></tr>"
        for m in payload["symbol_metrics"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Research Backtest Baseline</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left}}th{{background:#eef2ff}}.blocked{{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}}.ok{{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}}</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 13 Research Backtest Baseline Pack</h2>
<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Baseline statistical research metrics generated from certified public data.</p><p class='blocked'>No trading signal, no recommendation, no allocation, no operational decision, no canonical promotion.</p></div>
<h2>Symbol metrics</h2><table><thead><tr><th>symbol</th><th>rows</th><th>first</th><th>last</th><th>cum return</th><th>ann vol</th><th>max drawdown</th><th>positive rate</th><th>vol bucket</th><th>drawdown bucket</th></tr></thead><tbody>{rows_html}</tbody></table>
<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"""
    path.write_text(page, encoding="utf-8")


def build_phase13_research_backtest_baseline_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    certification = _load_json(root, "crypto_decision_lab/artifacts/phase12_public_data_research_readiness_certification_pack/phase12_public_data_research_readiness_certification_pack_index.json")
    acceptance = _load_json(root, "crypto_decision_lab/artifacts/phase11_data_drop_acceptance_pipeline_pack/phase11_data_drop_acceptance_pipeline_pack_index.json")

    rows, paths_checked = _discover_rows(root)
    grouped = _group_by_symbol(rows)
    metrics = [_symbol_metrics(symbol, symbol_rows) for symbol, symbol_rows in sorted(grouped.items()) if symbol != "UNKNOWN"]
    total_rows = sum(m["rows"] for m in metrics)
    symbols = [m["symbol"] for m in metrics]
    git_status = _git_status(root)

    public_ready = bool(_field(certification, "public_data_research_ready", False))
    certified_rows = _int(_field(certification, "public_rows_total", 0), 0)
    acceptance_rows = _int(_field(acceptance, "acceptance_rows_normalized", _field(acceptance, "rows_normalized", 0)), 0)

    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False

    metrics_have_returns = all(m["return_count"] > 0 for m in metrics) if metrics else False
    metrics_clean_flags = all(not m["recommendation_generated"] and not m["trading_signal_generated"] for m in metrics)
    baseline_ready = (
        public_ready
        and len(metrics) >= 3
        and total_rows >= EXPECTED_ROWS_TOTAL
        and certified_rows >= EXPECTED_ROWS_TOTAL
        and acceptance_rows >= EXPECTED_ROWS_TOTAL
        and metrics_have_returns
        and canonical_data_writes == 0
        and not promotion_allowed
        and not safe_apply_allowed
        and metrics_clean_flags
    )

    criteria = [
        _criterion("public_certification_present", bool(certification.get("_present")), certification.get("gate_answer", "MISSING"), "Phase 12 certification present"),
        _criterion("public_data_research_ready", public_ready, public_ready, "true"),
        _criterion("rows_loaded_for_backtest", total_rows >= EXPECTED_ROWS_TOTAL, total_rows, f">= {EXPECTED_ROWS_TOTAL}"),
        _criterion("symbols_loaded", len(metrics) >= 3, symbols, ">=3 symbols"),
        _criterion("returns_computed", metrics_have_returns, [m["return_count"] for m in metrics], ">0 returns per symbol"),
        _criterion("drawdown_computed", all("max_drawdown" in m for m in metrics), [m.get("max_drawdown") for m in metrics], "max drawdown per symbol"),
        _criterion("volatility_computed", all("volatility_annualized_24x365" in m for m in metrics), [m.get("volatility_annualized_24x365") for m in metrics], "annualized vol per symbol"),
        _criterion("no_recommendation_in_metrics", metrics_clean_flags, metrics_clean_flags, "true"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    gate = "PHASE13_RESEARCH_BACKTEST_BASELINE_READY_RESEARCH_ONLY" if baseline_ready else "PHASE13_RESEARCH_BACKTEST_BASELINE_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase13_research_backtest_baseline_pack.v1",
        "report_name": "qrds-phase13-research-backtest-baseline-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_13_RESEARCH_BACKTEST_BASELINE",
        "backtest_baseline_ready": bool(baseline_ready),
        "data_nature": "PUBLIC_MARKET_DATA_RESEARCH_ONLY",
        "source_label": SOURCE_LABEL,
        "public_data_research_ready": public_ready,
        "certified_public_rows": certified_rows,
        "acceptance_rows_normalized": acceptance_rows,
        "rows_analyzed": total_rows,
        "symbols_count": len(metrics),
        "symbols": symbols,
        "input_paths_checked": paths_checked,
        "symbol_metrics": metrics,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "BASELINE_RESEARCH_METRICS_READY" if baseline_ready else "BASELINE_RESEARCH_METRICS_NEED_REVIEW",
        "canonical_data_writes": canonical_data_writes,
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_backtest_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase13_research_backtest_baseline_pack.json"
    mp = out / "phase13_research_backtest_baseline_pack.md"
    hp = out / "index.html"
    ip = out / "phase13_research_backtest_baseline_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 13 Research Backtest Baseline Pack\n\n"
        f"**Gate answer:** {gate}\n\n"
        f"Backtest baseline ready: {baseline_ready}\n\n"
        f"Rows analyzed: {total_rows}\n\n"
        f"Symbols: {', '.join(symbols)}\n\n"
        f"Operational status: BLOCKED_RESEARCH_ONLY\n\n"
        f"No signal, recommendation, allocation, safe-apply, promotion or canonical write was generated.\n",
        encoding="utf-8",
    )
    _write_html(hp, payload)

    index = {
        "schema": "qrds.phase13_research_backtest_baseline_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "backtest_baseline_ready": payload["backtest_baseline_ready"],
        "data_nature": payload["data_nature"],
        "source_label": payload["source_label"],
        "public_data_research_ready": payload["public_data_research_ready"],
        "certified_public_rows": payload["certified_public_rows"],
        "acceptance_rows_normalized": payload["acceptance_rows_normalized"],
        "rows_analyzed": payload["rows_analyzed"],
        "symbols_count": payload["symbols_count"],
        "symbols": payload["symbols"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_backtest_score": payload["mean_backtest_score"],
        "git_status_line_count": payload["git_status_line_count"],
        "report_path": str(rp),
        "markdown_path": str(mp),
        "html_path": str(hp),
        "index_path": str(ip),
        "serve_entrypoint": str(hp),
        "report_payload_sha256": payload["report_payload_sha256"],
        "payload": payload,
        **SAFETY_FLAGS,
    }
    ip.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index


build_backtest_baseline_pack = build_phase13_research_backtest_baseline_pack
