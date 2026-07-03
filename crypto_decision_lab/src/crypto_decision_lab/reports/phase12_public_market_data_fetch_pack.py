from __future__ import annotations

import csv
import hashlib
import html
import json
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
DEFAULT_BASE_URLS = ["https://data-api.binance.vision", "https://api.binance.com"]
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
DEFAULT_INTERVAL = "1h"
DEFAULT_ROWS_PER_SYMBOL = 5000
SOURCE_LABEL = "BINANCE_SPOT_PUBLIC_KLINES_RESEARCH_ONLY"

SAFETY_FLAGS = {
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


def _root(repo_root: str | Path | None = None) -> Path:
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


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except Exception:
        return []


def _ms_to_iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def _http_get_json(url: str, timeout: int = 20) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "QRDS-Research-Only/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read().decode("utf-8")
    return json.loads(raw)


def fetch_klines(symbol: str, interval: str, rows: int, base_urls: list[str] | None = None, sleep_seconds: float = 0.12) -> tuple[list[list[Any]], str]:
    base_urls = base_urls or DEFAULT_BASE_URLS
    collected: list[list[Any]] = []
    end_time: int | None = None
    last_error = ""

    while len(collected) < rows:
        limit = min(1000, rows - len(collected))
        params = {"symbol": symbol, "interval": interval, "limit": str(limit)}
        if end_time is not None:
            params["endTime"] = str(end_time)
        query = urllib.parse.urlencode(params)
        success = False

        for base in base_urls:
            url = f"{base.rstrip('/')}/api/v3/klines?{query}"
            try:
                data = _http_get_json(url)
                if not isinstance(data, list):
                    raise ValueError(f"unexpected response type: {type(data)}")
                if not data:
                    raise ValueError("empty kline response")
                batch = [x for x in data if isinstance(x, list) and len(x) >= 6]
                if not batch:
                    raise ValueError("no valid kline rows")
                # Prepend older batch. When endTime is used, endpoint returns the most recent rows up to that time.
                collected = batch + collected
                oldest_open_time = int(batch[0][0])
                end_time = oldest_open_time - 1
                success = True
                break
            except Exception as exc:
                last_error = f"{base}: {exc}"

        if not success:
            raise RuntimeError(f"failed to fetch {symbol} {interval}: {last_error}")

        if len(collected) >= rows:
            collected = collected[-rows:]
            break
        time.sleep(sleep_seconds)

    # De-duplicate by open time and keep chronological order.
    by_time: dict[int, list[Any]] = {}
    for row in collected:
        by_time[int(row[0])] = row
    ordered = [by_time[k] for k in sorted(by_time.keys())]
    if len(ordered) > rows:
        ordered = ordered[-rows:]
    return ordered, (base_urls[0] if base_urls else "UNKNOWN")


def klines_to_ohlcv_rows(symbol: str, interval: str, rows: list[list[Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    dash_symbol = symbol.replace("USDT", "-USDT") if symbol.endswith("USDT") else symbol
    for row in rows:
        normalized.append(
            {
                "timestamp": _ms_to_iso(int(row[0])),
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
                "symbol": dash_symbol,
                "interval": interval,
                "source": SOURCE_LABEL,
            }
        )
    return normalized


def write_public_market_csvs(root: Path, symbols: list[str], interval: str, rows_per_symbol: int, base_urls: list[str] | None = None, clean_synthetic: bool = True) -> list[dict[str, Any]]:
    inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
    archive = root / "crypto_decision_lab" / "manual_intake" / "archive" / "synthetic_fixtures"
    inbox.mkdir(parents=True, exist_ok=True)
    archive.mkdir(parents=True, exist_ok=True)

    if clean_synthetic:
        for old in inbox.glob("*_synthetic_fixture_ohlcv.csv"):
            old.rename(archive / old.name)

    outputs: list[dict[str, Any]] = []
    for symbol in symbols:
        raw_rows, used_base = fetch_klines(symbol, interval, rows_per_symbol, base_urls=base_urls)
        rows = klines_to_ohlcv_rows(symbol, interval, raw_rows)
        safe = symbol.lower().replace("usdt", "_usdt")
        path = inbox / f"{safe}_binance_public_klines_{interval}.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume", "symbol", "interval", "source"])
            w.writeheader()
            w.writerows(rows)
        timestamps = [r["timestamp"] for r in rows]
        outputs.append(
            {
                "symbol": symbol,
                "normalized_symbol": rows[0]["symbol"] if rows else symbol,
                "interval": interval,
                "path": str(path),
                "rows": len(rows),
                "source": SOURCE_LABEL,
                "base_url_used": used_base,
                "first_timestamp": timestamps[0] if timestamps else "MISSING",
                "last_timestamp": timestamps[-1] if timestamps else "MISSING",
                "sha256": _sha_file(path)[:16],
            }
        )
    return outputs


def _criterion(cid: str, ok: bool, observed: Any, threshold: str, status: str | None = None) -> dict[str, Any]:
    return {"criterion_id": cid, "status": status or ("PASS" if ok else "FAIL"), "ready": bool(ok), "observed": observed, "threshold": threshold}


def _validate_public_files(files: list[dict[str, Any]], rows_per_symbol: int) -> dict[str, Any]:
    rows_total = 0
    source_labels = set()
    symbols = set()
    monotonic_ok = True
    shape_ok = True

    for f in files:
        path = Path(f["path"])
        rows = _read_csv_rows(path)
        rows_total += len(rows)
        prev_ts = ""
        for row in rows:
            source_labels.add(str(row.get("source", "")))
            symbols.add(str(row.get("symbol", "")))
            ts = str(row.get("timestamp", ""))
            if prev_ts and ts <= prev_ts:
                monotonic_ok = False
            prev_ts = ts
            try:
                o = float(row["open"]); h = float(row["high"]); l = float(row["low"]); c = float(row["close"]); v = float(row["volume"])
                if h < l or o < l or o > h or c < l or c > h or v < 0:
                    shape_ok = False
            except Exception:
                shape_ok = False

    return {
        "rows_total": rows_total,
        "source_labels": sorted(source_labels),
        "symbols": sorted(symbols),
        "monotonic_ok": monotonic_ok,
        "shape_ok": shape_ok,
        "all_files_have_target_rows": all(int(f["rows"]) == rows_per_symbol for f in files),
    }


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Data nature", payload["data_nature"]),
        ("Files", payload["public_file_count"]),
        ("Rows", payload["public_rows_total"]),
        ("Rows/symbol", payload["rows_per_symbol"]),
        ("Source", payload["source_label"]),
        ("Canonical writes", payload["canonical_data_writes"]),
        ("Promotion allowed", payload["promotion_allowed"]),
        ("Mean score", payload["mean_public_fetch_score"]),
    ]
    card = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    files = "".join(
        f"<tr><td>{esc(x['symbol'])}</td><td>{esc(x['rows'])}</td><td>{esc(x['first_timestamp'])}</td><td>{esc(x['last_timestamp'])}</td><td>{esc(x['base_url_used'])}</td><td>{esc(x['sha256'])}</td><td>{esc(x['path'])}</td></tr>"
        for x in payload["public_files"]
    )
    crit = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = f"""<!doctype html><html><head><meta charset='utf-8'><title>QRDS Public Market Data Fetch</title>
<style>body{{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}}.card{{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}}.kpi{{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}}table{{border-collapse:collapse;width:100%;background:white}}th,td{{border:1px solid #d9deea;padding:8px;text-align:left}}th{{background:#eef2ff}}.blocked{{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}}</style></head><body>
<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 12 Public Market Data Fetch Pack</h2>
<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card}<p class='blocked'>Public market data only. No account, no API key, no trading endpoints, no canonical promotion.</p></div>
<h2>Public files</h2><table><thead><tr><th>symbol</th><th>rows</th><th>first timestamp</th><th>last timestamp</th><th>base URL</th><th>sha256</th><th>path</th></tr></thead><tbody>{files}</tbody></table>
<h2>Criteria</h2><table><thead><tr><th>criterion_id</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit}</tbody></table>
<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"""
    path.write_text(page, encoding="utf-8")


def build_phase12_public_market_data_fetch_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    symbols: list[str] | None = None,
    interval: str = DEFAULT_INTERVAL,
    rows_per_symbol: int = DEFAULT_ROWS_PER_SYMBOL,
    fetch: bool = True,
    base_urls: list[str] | None = None,
    **_: Any,
) -> dict[str, Any]:
    root = _root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    symbols = symbols or DEFAULT_SYMBOLS
    if fetch:
        public_files = write_public_market_csvs(root, symbols, interval, rows_per_symbol, base_urls=base_urls)
    else:
        inbox = root / "crypto_decision_lab" / "manual_intake" / "inbox"
        public_files = []
        for p in sorted(inbox.glob(f"*_binance_public_klines_{interval}.csv")):
            rows = _read_csv_rows(p)
            symbol = p.name.split("_binance_public_klines_")[0].upper().replace("_", "")
            public_files.append(
                {
                    "symbol": symbol,
                    "normalized_symbol": symbol.replace("USDT", "-USDT"),
                    "interval": interval,
                    "path": str(p),
                    "rows": len(rows),
                    "source": SOURCE_LABEL,
                    "base_url_used": "EXISTING_FILE",
                    "first_timestamp": rows[0]["timestamp"] if rows else "MISSING",
                    "last_timestamp": rows[-1]["timestamp"] if rows else "MISSING",
                    "sha256": _sha_file(p)[:16],
                }
            )

    validation = _validate_public_files(public_files, rows_per_symbol)
    canonical_data_writes = 0
    promotion_allowed = False
    git_status = _git_status(root)

    criteria = [
        _criterion("public_file_count", len(public_files) == len(symbols), f"{len(public_files)}/{len(symbols)}", "one public file per symbol"),
        _criterion("rows_per_symbol", validation["all_files_have_target_rows"], [f["rows"] for f in public_files], f"{rows_per_symbol} rows each"),
        _criterion("public_source_label", validation["source_labels"] == [SOURCE_LABEL], validation["source_labels"], SOURCE_LABEL),
        _criterion("timestamp_monotonic", validation["monotonic_ok"], validation["monotonic_ok"], "strictly increasing per file"),
        _criterion("ohlcv_shape_valid", validation["shape_ok"], validation["shape_ok"], "OHLCV shape valid"),
        _criterion("no_api_key", True, False, "api_key_present false"),
        _criterion("no_account_connection", True, False, "authenticated connection false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0 canonical writes"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready = sum(1 for c in criteria if c["ready"])
    gate = "PHASE12_PUBLIC_MARKET_DATA_FETCH_READY_RESEARCH_ONLY" if ready == len(criteria) else "PHASE12_PUBLIC_MARKET_DATA_FETCH_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase12_public_market_data_fetch_pack.v1",
        "report_name": "qrds-phase12-public-market-data-fetch-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_12_PUBLIC_MARKET_DATA_FETCH",
        "data_nature": "PUBLIC_MARKET_DATA_RESEARCH_ONLY",
        "source_label": SOURCE_LABEL,
        "source_endpoint_family": "BINANCE_SPOT_PUBLIC_KLINES",
        "symbols": symbols,
        "interval": interval,
        "rows_per_symbol": rows_per_symbol,
        "public_file_count": len(public_files),
        "public_rows_total": validation["rows_total"],
        "public_files": public_files,
        "validation": validation,
        "canonical_data_writes": canonical_data_writes,
        "promotion_allowed": promotion_allowed,
        "safe_apply_allowed": False,
        "api_key_present": False,
        "authenticated_connection_used": False,
        "trading_endpoint_used": False,
        "git_status_line_count": len(git_status),
        "git_status_lines": git_status[:80],
        "criteria": criteria,
        "criteria_ready_count": ready,
        "criteria_total_count": len(criteria),
        "mean_public_fetch_score": round(ready / len(criteria), 4),
        "safety_flags": SAFETY_FLAGS,
        **SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = _sha_payload(payload)

    rp = out / "phase12_public_market_data_fetch_pack.json"
    mp = out / "phase12_public_market_data_fetch_pack.md"
    hp = out / "index.html"
    ip = out / "phase12_public_market_data_fetch_pack_index.json"
    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(f"# QRDS/QOS Phase 12 Public Market Data Fetch Pack\n\n**Gate answer:** {gate}\n\nSource: {SOURCE_LABEL}\n\nRows: {validation['rows_total']}\n\nNo API key. No account. No trading endpoint. Canonical writes: 0. Promotion blocked.\n", encoding="utf-8")
    _render_html(hp, payload)

    index = {k: payload[k] for k in ["schema","report_name","generated_at","gate_answer","policy_lock","app_mode","station","data_nature","source_label","source_endpoint_family","symbols","interval","rows_per_symbol","public_file_count","public_rows_total","canonical_data_writes","promotion_allowed","safe_apply_allowed","api_key_present","authenticated_connection_used","trading_endpoint_used","criteria_ready_count","criteria_total_count","mean_public_fetch_score","git_status_line_count", *SAFETY_FLAGS.keys()] if k in payload}
    index.update({"schema": "qrds.phase12_public_market_data_fetch_pack_index.v1", "report_path": str(rp), "markdown_path": str(mp), "html_path": str(hp), "index_path": str(ip), "serve_entrypoint": str(hp), "report_payload_sha256": payload["report_payload_sha256"], "payload": payload})
    ip.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    return index


build_public_fetch_pack = build_phase12_public_market_data_fetch_pack
