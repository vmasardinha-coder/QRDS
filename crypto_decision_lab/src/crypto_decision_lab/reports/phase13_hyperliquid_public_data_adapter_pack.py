from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import statistics
import subprocess
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
API_URL = "https://api.hyperliquid.xyz/info"
SOURCE_LABEL = "HYPERLIQUID_PUBLIC_CANDLES_RESEARCH_ONLY"
DEFAULT_COINS = ["BTC", "ETH", "SOL"]
DEFAULT_INTERVAL = "1h"
DEFAULT_ROWS_PER_COIN = 5000
INTERVAL_MS = {
    "1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000, "30m": 1800000,
    "1h": 3600000, "2h": 7200000, "4h": 14400000, "8h": 28800000,
    "12h": 43200000, "1d": 86400000, "3d": 259200000, "1w": 604800000,
}

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


def _sha_file(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return "MISSING"


def _sha_payload(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _git_status(root: Path) -> list[str]:
    try:
        p = subprocess.run(["git", "status", "--short"], cwd=root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return [x for x in p.stdout.splitlines() if x.strip()]
    except Exception:
        return []


def _ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _post_info(body: dict[str, Any], timeout: int = 25) -> Any:
    raw = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        API_URL,
        data=raw,
        headers={"Content-Type": "application/json", "User-Agent": "QRDS-Research-Only/1.0"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_hyperliquid_candles(coin: str, interval: str, rows: int) -> list[dict[str, Any]]:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")
    end_ms = int(time.time() * 1000)
    start_ms = end_ms - (rows + 20) * INTERVAL_MS[interval]
    body = {"type": "candleSnapshot", "req": {"coin": coin, "interval": interval, "startTime": start_ms, "endTime": end_ms}}
    data = _post_info(body)
    if not isinstance(data, list):
        raise RuntimeError(f"unexpected Hyperliquid candle response for {coin}: {type(data)}")

    out: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        t = item.get("t") or item.get("T")
        if t is None:
            continue
        out.append(
            {
                "timestamp": _ms_to_iso(int(t)),
                "open": item.get("o"),
                "high": item.get("h"),
                "low": item.get("l"),
                "close": item.get("c"),
                "volume": item.get("v"),
                "symbol": f"{coin}-USDC-PERP",
                "coin": coin,
                "interval": interval,
                "source": SOURCE_LABEL,
                "venue": "HYPERLIQUID",
            }
        )
    out = sorted(out, key=lambda r: r["timestamp"])
    return out[-rows:]


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except Exception:
        return []


def write_hyperliquid_csvs(root: Path, coins: list[str], interval: str, rows_per_coin: int, fetch: bool = True) -> list[dict[str, Any]]:
    inbox = root / "crypto_decision_lab" / "manual_intake" / "hyperliquid_inbox"
    inbox.mkdir(parents=True, exist_ok=True)

    outputs: list[dict[str, Any]] = []
    if fetch:
        for old in inbox.glob("*_hyperliquid_public_candles_*.csv"):
            old.unlink()
        for coin in coins:
            rows = fetch_hyperliquid_candles(coin, interval, rows_per_coin)
            path = inbox / f"{coin.lower()}_hyperliquid_public_candles_{interval}.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume", "symbol", "coin", "interval", "source", "venue"])
                w.writeheader()
                w.writerows(rows)
            outputs.append(
                {
                    "coin": coin,
                    "symbol": f"{coin}-USDC-PERP",
                    "interval": interval,
                    "path": str(path),
                    "rows": len(rows),
                    "source": SOURCE_LABEL,
                    "first_timestamp": rows[0]["timestamp"] if rows else "MISSING",
                    "last_timestamp": rows[-1]["timestamp"] if rows else "MISSING",
                    "sha256": _sha_file(path)[:16],
                }
            )
    else:
        for path in sorted(inbox.glob(f"*_hyperliquid_public_candles_{interval}.csv")):
            rows = _read_csv(path)
            coin = path.name.split("_hyperliquid_public_candles_")[0].upper()
            outputs.append(
                {
                    "coin": coin,
                    "symbol": f"{coin}-USDC-PERP",
                    "interval": interval,
                    "path": str(path),
                    "rows": len(rows),
                    "source": SOURCE_LABEL,
                    "first_timestamp": rows[0].get("timestamp", "MISSING") if rows else "MISSING",
                    "last_timestamp": rows[-1].get("timestamp", "MISSING") if rows else "MISSING",
                    "sha256": _sha_file(path)[:16],
                }
            )
    return outputs


def _as_float(x: Any) -> float | None:
    try:
        if x in ("", None):
            return None
        return float(x)
    except Exception:
        return None


def _validate_files(files: list[dict[str, Any]], rows_per_coin: int) -> dict[str, Any]:
    total_rows = 0
    source_labels = set()
    symbols = set()
    monotonic_ok = True
    shape_ok = True
    file_summaries: list[dict[str, Any]] = []

    for f in files:
        path = Path(f["path"])
        rows = _read_csv(path)
        total_rows += len(rows)
        prev_ts = ""
        file_sources = set()
        file_symbols = set()
        closes: list[float] = []
        for row in rows:
            ts = str(row.get("timestamp", ""))
            src = str(row.get("source", ""))
            sym = str(row.get("symbol", ""))
            source_labels.add(src)
            file_sources.add(src)
            symbols.add(sym)
            file_symbols.add(sym)
            if prev_ts and ts <= prev_ts:
                monotonic_ok = False
            prev_ts = ts
            o = _as_float(row.get("open"))
            h = _as_float(row.get("high"))
            l = _as_float(row.get("low"))
            c = _as_float(row.get("close"))
            v = _as_float(row.get("volume"))
            if None in (o, h, l, c, v) or h < l or o < l or o > h or c < l or c > h or v < 0:
                shape_ok = False
            if c is not None:
                closes.append(c)
        returns = []
        for a, b in zip(closes[:-1], closes[1:]):
            if a > 0:
                returns.append(b / a - 1)
        vol = statistics.stdev(returns) * math.sqrt(24 * 365) if len(returns) > 1 else 0.0
        file_summaries.append(
            {
                "coin": f.get("coin"),
                "symbol": f.get("symbol"),
                "rows": len(rows),
                "sources": sorted(file_sources),
                "symbols": sorted(file_symbols),
                "first_timestamp": rows[0].get("timestamp", "MISSING") if rows else "MISSING",
                "last_timestamp": rows[-1].get("timestamp", "MISSING") if rows else "MISSING",
                "ann_vol_research": round(vol, 8),
                "ready": len(rows) >= rows_per_coin and file_sources == {SOURCE_LABEL},
                "path": str(path),
                "sha256": f.get("sha256"),
            }
        )

    return {
        "total_rows": total_rows,
        "source_labels": sorted(source_labels),
        "symbols": sorted(symbols),
        "monotonic_ok": monotonic_ok,
        "shape_ok": shape_ok,
        "all_files_have_target_rows": all(int(f.get("rows", 0)) >= rows_per_coin for f in files),
        "file_summaries": file_summaries,
    }


def _criterion(cid: str, ok: bool, obs: Any, threshold: str, status: str | None = None) -> dict[str, Any]:
    return {"criterion_id": cid, "status": status or ("PASS" if ok else "FAIL"), "ready": bool(ok), "observed": obs, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Adapter ready", payload["hyperliquid_adapter_ready"]),
        ("Files", payload["hyperliquid_file_count"]),
        ("Rows", payload["hyperliquid_rows_total"]),
        ("Rows/coin", payload["rows_per_coin"]),
        ("Source", payload["source_label"]),
        ("Operational", payload["operational_status"]),
        ("Canonical writes", payload["canonical_data_writes"]),
        ("Mean score", payload["mean_adapter_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    files_html = "".join(
        f"<tr><td>{esc(f['coin'])}</td><td>{esc(f['symbol'])}</td><td>{esc(f['rows'])}</td><td>{esc(f['first_timestamp'])}</td><td>{esc(f['last_timestamp'])}</td><td>{esc(f['ann_vol_research'])}</td><td>{esc(f['sha256'])}</td></tr>"
        for f in payload["file_summaries"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Hyperliquid Public Adapter</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 13 Hyperliquid Public Data Adapter Pack</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Hyperliquid public candle adapter generated research-only files in a separate inbox.</p><p class='blocked'>No API wallet, no exchange endpoint, no orders, no signals, no recommendation, no canonical promotion.</p></div>"
        f"<h2>Files</h2><table><thead><tr><th>coin</th><th>symbol</th><th>rows</th><th>first</th><th>last</th><th>ann vol research</th><th>sha256</th></tr></thead><tbody>{files_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def build_phase13_hyperliquid_public_data_adapter_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    coins: list[str] | None = None,
    interval: str = DEFAULT_INTERVAL,
    rows_per_coin: int = DEFAULT_ROWS_PER_COIN,
    fetch: bool = True,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    coins = coins or DEFAULT_COINS
    files = write_hyperliquid_csvs(root, coins, interval, rows_per_coin, fetch=fetch)
    validation = _validate_files(files, rows_per_coin)
    git_status = _git_status(root)

    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    expected_total = len(coins) * rows_per_coin

    criteria = [
        _criterion("separate_hyperliquid_inbox", True, "manual_intake/hyperliquid_inbox", "separate from Binance-certified inbox"),
        _criterion("file_count", len(files) == len(coins), f"{len(files)}/{len(coins)}", "one file per coin"),
        _criterion("rows_depth", validation["total_rows"] >= expected_total, validation["total_rows"], f">= {expected_total} rows"),
        _criterion("source_label_clean", validation["source_labels"] == [SOURCE_LABEL], validation["source_labels"], SOURCE_LABEL),
        _criterion("timestamp_monotonic", validation["monotonic_ok"], validation["monotonic_ok"], "true"),
        _criterion("ohlcv_shape_valid", validation["shape_ok"], validation["shape_ok"], "true"),
        _criterion("no_api_key", True, False, "api_key_present false"),
        _criterion("no_account_connection", True, False, "authenticated_connection_used false"),
        _criterion("no_exchange_endpoint", True, False, "exchange endpoint not used"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    adapter_ready = ready_count == len(criteria)
    gate = "PHASE13_HYPERLIQUID_PUBLIC_DATA_ADAPTER_READY_RESEARCH_ONLY" if adapter_ready else "PHASE13_HYPERLIQUID_PUBLIC_DATA_ADAPTER_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase13_hyperliquid_public_data_adapter_pack.v1",
        "report_name": "qrds-phase13-hyperliquid-public-data-adapter-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_13_HYPERLIQUID_PUBLIC_DATA_ADAPTER",
        "hyperliquid_adapter_ready": adapter_ready,
        "data_nature": "HYPERLIQUID_PUBLIC_MARKET_DATA_RESEARCH_ONLY",
        "source_label": SOURCE_LABEL,
        "source_endpoint_family": "HYPERLIQUID_INFO_CANDLE_SNAPSHOT",
        "api_url": API_URL,
        "coins": coins,
        "interval": interval,
        "rows_per_coin": rows_per_coin,
        "hyperliquid_file_count": len(files),
        "hyperliquid_rows_total": validation["total_rows"],
        "hyperliquid_files": files,
        "file_summaries": validation["file_summaries"],
        "validation": validation,
        "separate_inbox_path": str(root / "crypto_decision_lab" / "manual_intake" / "hyperliquid_inbox"),
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "HYPERLIQUID_PUBLIC_DATA_READY_FOR_SOURCE_COMPARISON" if adapter_ready else "HYPERLIQUID_PUBLIC_DATA_NEEDS_REVIEW",
        "canonical_data_writes": canonical_data_writes,
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "exchange_endpoint_used": False,
        "trading_endpoint_used": False,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready_count,
        "criteria_total_count": len(criteria),
        "mean_adapter_score": round(ready_count / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase13_hyperliquid_public_data_adapter_pack.json"
    mp = out / "phase13_hyperliquid_public_data_adapter_pack.md"
    hp = out / "index.html"
    ip = out / "phase13_hyperliquid_public_data_adapter_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 13 Hyperliquid Public Data Adapter Pack\n\n**Gate answer:** {gate}\n\nRows: {validation['total_rows']}\n\nSource: {SOURCE_LABEL}\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nNo API wallet, no exchange endpoint, no orders, no recommendation, no canonical writes.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase13_hyperliquid_public_data_adapter_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "hyperliquid_adapter_ready": payload["hyperliquid_adapter_ready"],
        "data_nature": payload["data_nature"],
        "source_label": payload["source_label"],
        "source_endpoint_family": payload["source_endpoint_family"],
        "coins": payload["coins"],
        "interval": payload["interval"],
        "rows_per_coin": payload["rows_per_coin"],
        "hyperliquid_file_count": payload["hyperliquid_file_count"],
        "hyperliquid_rows_total": payload["hyperliquid_rows_total"],
        "separate_inbox_path": payload["separate_inbox_path"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "exchange_endpoint_used": payload["exchange_endpoint_used"],
        "trading_endpoint_used": payload["trading_endpoint_used"],
        "safe_apply_allowed": payload["safe_apply_allowed"],
        "promotion_allowed": payload["promotion_allowed"],
        "canonical_data_writes": payload["canonical_data_writes"],
        "criteria_ready_count": payload["criteria_ready_count"],
        "criteria_total_count": payload["criteria_total_count"],
        "mean_adapter_score": payload["mean_adapter_score"],
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


build_hyperliquid_adapter_pack = build_phase13_hyperliquid_public_data_adapter_pack
