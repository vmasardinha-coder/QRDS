from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import statistics
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
API_BASE = "https://api.bybit.com"
SOURCE_LABEL = "BYBIT_LINEAR_PUBLIC_KLINES_RESEARCH_ONLY"
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
DEFAULT_CATEGORY = "linear"
DEFAULT_INTERVAL = "60"
DEFAULT_ROWS_PER_SYMBOL = 5000
INTERVAL_MS = {"60": 3600000}

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


def _http_get_json(url: str, timeout: int = 25) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "QRDS-Research-Only/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {
            "__network_error__": True,
            "error_type": "HTTPError",
            "status_code": exc.code,
            "reason": str(exc.reason),
            "url": url,
            "research_status": "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY",
        }
    except Exception as exc:
        return {
            "__network_error__": True,
            "error_type": exc.__class__.__name__,
            "status_code": None,
            "reason": str(exc),
            "url": url,
            "research_status": "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY",
        }


def fetch_bybit_klines(symbol: str, category: str, interval: str, rows: int) -> list[dict[str, Any]]:
    if interval not in INTERVAL_MS:
        raise ValueError(f"Unsupported interval: {interval}")

    collected: dict[int, list[Any]] = {}
    end_ms = int(time.time() * 1000)

    while len(collected) < rows:
        params = {
            "category": category,
            "symbol": symbol,
            "interval": interval,
            "limit": "1000",
            "end": str(end_ms),
        }
        url = API_BASE + "/v5/market/kline?" + urllib.parse.urlencode(params)
        data = _http_get_json(url)
        if isinstance(data, dict) and data.get("__network_error__"):
            return []
        if not isinstance(data, dict) or data.get("retCode") != 0:
            return []
        result = data.get("result") if isinstance(data.get("result"), dict) else {}
        batch = result.get("list") if isinstance(result.get("list"), list) else []
        if not batch:
            break
        for row in batch:
            if isinstance(row, list) and len(row) >= 7:
                collected[int(row[0])] = row
        oldest = min(int(row[0]) for row in batch if isinstance(row, list) and row)
        end_ms = oldest - 1
        if len(batch) < 2:
            break
        time.sleep(0.12)

    ordered = [collected[k] for k in sorted(collected.keys())][-rows:]
    normalized: list[dict[str, Any]] = []
    base = symbol.replace("USDT", "")
    for row in ordered:
        normalized.append(
            {
                "timestamp": _ms_to_iso(int(row[0])),
                "open": row[1],
                "high": row[2],
                "low": row[3],
                "close": row[4],
                "volume": row[5],
                "turnover": row[6],
                "symbol": f"{base}-USDT-PERP",
                "raw_symbol": symbol,
                "category": category,
                "interval": "1h",
                "source": SOURCE_LABEL,
                "venue": "BYBIT",
            }
        )
    return normalized


def _read_csv(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as f:
            return [dict(r) for r in csv.DictReader(f)]
    except Exception:
        return []


def write_bybit_csvs(root: Path, symbols: list[str], category: str, interval: str, rows_per_symbol: int, fetch: bool = True) -> list[dict[str, Any]]:
    inbox = root / "crypto_decision_lab" / "manual_intake" / "bybit_inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []

    if fetch:
        for old in inbox.glob("*_bybit_public_linear_klines_1h.csv"):
            old.unlink()
        for symbol in symbols:
            rows = fetch_bybit_klines(symbol, category, interval, rows_per_symbol)
            base = symbol.lower().replace("usdt", "_usdt")
            path = inbox / f"{base}_bybit_public_linear_klines_1h.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume", "turnover", "symbol", "raw_symbol", "category", "interval", "source", "venue"])
                w.writeheader()
                w.writerows(rows)
            outputs.append(
                {
                    "raw_symbol": symbol,
                    "symbol": rows[0]["symbol"] if rows else symbol,
                    "category": category,
                    "interval": "1h",
                    "path": str(path),
                    "rows": len(rows),
                    "source": SOURCE_LABEL,
                    "first_timestamp": rows[0]["timestamp"] if rows else "MISSING",
                    "last_timestamp": rows[-1]["timestamp"] if rows else "MISSING",
                    "sha256": _sha_file(path)[:16],
                }
            )
    else:
        for path in sorted(inbox.glob("*_bybit_public_linear_klines_1h.csv")):
            rows = _read_csv(path)
            raw_symbol = rows[0].get("raw_symbol", path.name.split("_bybit_public")[0].upper().replace("_", "")) if rows else path.name
            outputs.append(
                {
                    "raw_symbol": raw_symbol,
                    "symbol": rows[0].get("symbol", raw_symbol) if rows else raw_symbol,
                    "category": rows[0].get("category", category) if rows else category,
                    "interval": rows[0].get("interval", "1h") if rows else "1h",
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


def _validate_files(files: list[dict[str, Any]], rows_per_symbol: int) -> dict[str, Any]:
    total_rows = 0
    source_labels = set()
    symbols = set()
    monotonic_ok = True
    shape_ok = True
    summaries: list[dict[str, Any]] = []

    for file_info in files:
        path = Path(file_info["path"])
        rows = _read_csv(path)
        total_rows += len(rows)
        prev_ts = ""
        closes: list[float] = []
        file_sources = set()
        file_symbols = set()

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
                returns.append(b / a - 1.0)
        ann_vol = statistics.stdev(returns) * math.sqrt(24 * 365) if len(returns) > 1 else 0.0

        summaries.append(
            {
                "raw_symbol": file_info.get("raw_symbol"),
                "symbol": file_info.get("symbol"),
                "rows": len(rows),
                "sources": sorted(file_sources),
                "symbols": sorted(file_symbols),
                "first_timestamp": rows[0].get("timestamp", "MISSING") if rows else "MISSING",
                "last_timestamp": rows[-1].get("timestamp", "MISSING") if rows else "MISSING",
                "ann_vol_research": round(ann_vol, 8),
                "ready": len(rows) >= rows_per_symbol and file_sources == {SOURCE_LABEL},
                "path": str(path),
                "sha256": file_info.get("sha256"),
            }
        )

    return {
        "total_rows": total_rows,
        "source_labels": sorted(source_labels),
        "symbols": sorted(symbols),
        "monotonic_ok": monotonic_ok,
        "shape_ok": shape_ok,
        "all_files_have_target_rows": all(int(f.get("rows", 0)) >= rows_per_symbol for f in files),
        "file_summaries": summaries,
    }


def _criterion(cid: str, ok: bool, obs: Any, threshold: str) -> dict[str, Any]:
    return {"criterion_id": cid, "status": "PASS" if ok else "FAIL", "ready": bool(ok), "observed": obs, "threshold": threshold}


def _render_html(path: Path, payload: dict[str, Any]) -> None:
    esc = lambda x: html.escape(str(x))
    cards = [
        ("Station", payload["station"]),
        ("Adapter ready", payload["bybit_adapter_ready"]),
        ("Files", payload["bybit_file_count"]),
        ("Rows", payload["bybit_rows_total"]),
        ("Rows/symbol", payload["rows_per_symbol"]),
        ("Category", payload["category"]),
        ("Operational", payload["operational_status"]),
        ("Mean score", payload["mean_adapter_score"]),
    ]
    card_html = "".join(f"<div class='kpi'><b>{esc(k)}</b><br>{esc(v)}</div>" for k, v in cards)
    files_html = "".join(
        f"<tr><td>{esc(f['raw_symbol'])}</td><td>{esc(f['symbol'])}</td><td>{esc(f['rows'])}</td><td>{esc(f['first_timestamp'])}</td><td>{esc(f['last_timestamp'])}</td><td>{esc(f['ann_vol_research'])}</td><td>{esc(f['sha256'])}</td></tr>"
        for f in payload["file_summaries"]
    )
    crit_html = "".join(
        f"<tr><td>{esc(c['criterion_id'])}</td><td>{esc(c['status'])}</td><td>{esc(c['ready'])}</td><td>{esc(c['observed'])}</td><td>{esc(c['threshold'])}</td></tr>"
        for c in payload["criteria"]
    )
    page = (
        "<!doctype html><html><head><meta charset='utf-8'><title>QRDS Bybit Public Adapter</title>"
        "<style>body{font-family:Arial,sans-serif;margin:32px;background:#f6f7fb;color:#172033}.card{background:white;border:1px solid #d9deea;border-radius:14px;padding:20px;margin:16px 0}.kpi{display:inline-block;background:#eef2ff;border-radius:10px;padding:12px 16px;margin:8px;min-width:150px}table{border-collapse:collapse;width:100%;background:white}th,td{border:1px solid #d9deea;padding:8px;text-align:left}th{background:#eef2ff}.blocked{background:#fee2e2;border-radius:999px;padding:6px 10px;font-weight:700}.ok{background:#dcfce7;border-radius:999px;padding:6px 10px;font-weight:700}</style></head><body>"
        f"<h1>QRDS/QOS • Gate BTC • Research-only</h1><h2>Phase 14 Bybit Public Data Adapter Pack</h2>"
        f"<div class='card'><p><b>Gate answer:</b> {esc(payload['gate_answer'])}</p><p><b>Policy lock:</b> {esc(payload['policy_lock'])} • <b>Mode:</b> {esc(payload['app_mode'])}</p>{card_html}<p class='ok'>Bybit public kline adapter generated research-only files in a separate inbox.</p><p class='blocked'>No API key, no account, no order endpoint, no signal, no recommendation, no canonical promotion.</p></div>"
        f"<h2>Files</h2><table><thead><tr><th>raw symbol</th><th>symbol</th><th>rows</th><th>first</th><th>last</th><th>ann vol research</th><th>sha256</th></tr></thead><tbody>{files_html}</tbody></table>"
        f"<h2>Criteria</h2><table><thead><tr><th>criterion</th><th>status</th><th>ready</th><th>observed</th><th>threshold</th></tr></thead><tbody>{crit_html}</tbody></table>"
        f"<p>Generated at {esc(payload['generated_at'])} • SHA256 {esc(payload['report_payload_sha256'])}</p></body></html>"
    )
    path.write_text(page, encoding="utf-8")


def build_phase14_bybit_public_data_adapter_pack(
    output_dir: str | Path,
    repo_root: str | Path | None = None,
    symbols: list[str] | None = None,
    category: str = DEFAULT_CATEGORY,
    interval: str = DEFAULT_INTERVAL,
    rows_per_symbol: int = DEFAULT_ROWS_PER_SYMBOL,
    fetch: bool = True,
    **_: Any,
) -> dict[str, Any]:
    root = _repo_root(repo_root)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    symbols = symbols or DEFAULT_SYMBOLS
    files = write_bybit_csvs(root, symbols, category, interval, rows_per_symbol, fetch=fetch)
    validation = _validate_files(files, rows_per_symbol)
    git_status = _git_status(root)

    canonical_data_writes = 0
    promotion_allowed = False
    safe_apply_allowed = False
    expected_total = len(symbols) * rows_per_symbol

    criteria = [
        _criterion("separate_bybit_inbox", True, "manual_intake/bybit_inbox", "separate source inbox"),
        _criterion("file_count", len(files) == len(symbols), f"{len(files)}/{len(symbols)}", "one file per symbol"),
        _criterion("rows_depth", validation["total_rows"] >= expected_total, validation["total_rows"], f">= {expected_total} rows"),
        _criterion("source_label_clean", validation["source_labels"] == [SOURCE_LABEL], validation["source_labels"], SOURCE_LABEL),
        _criterion("timestamp_monotonic", validation["monotonic_ok"], validation["monotonic_ok"], "true"),
        _criterion("ohlcv_shape_valid", validation["shape_ok"], validation["shape_ok"], "true"),
        _criterion("no_api_key", True, False, "api_key_present false"),
        _criterion("no_account_connection", True, False, "authenticated_connection_used false"),
        _criterion("no_order_endpoint", True, False, "order endpoint not used"),
        _criterion("safe_apply_blocked", not safe_apply_allowed, safe_apply_allowed, "false"),
        _criterion("promotion_blocked", not promotion_allowed, promotion_allowed, "false"),
        _criterion("canonical_writes_zero", canonical_data_writes == 0, canonical_data_writes, "0"),
        _criterion("research_only_lock", True, "ACTIVE", "policy lock active"),
    ]
    ready_count = sum(1 for c in criteria if c["ready"])
    adapter_ready = ready_count == len(criteria)
    gate = "PHASE14_BYBIT_PUBLIC_DATA_ADAPTER_READY_RESEARCH_ONLY" if adapter_ready else "PHASE14_BYBIT_PUBLIC_DATA_ADAPTER_NEEDS_REVIEW_RESEARCH_ONLY"

    payload: dict[str, Any] = {
        "schema": "qrds.phase14_bybit_public_data_adapter_pack.v1",
        "report_name": "qrds-phase14-bybit-public-data-adapter-pack",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate_answer": gate,
        "policy_lock": "ACTIVE",
        "app_mode": APP_MODE,
        "station": "PHASE_14_BYBIT_PUBLIC_DATA_ADAPTER",
        "bybit_adapter_ready": adapter_ready,
        "data_nature": "BYBIT_PUBLIC_MARKET_DATA_RESEARCH_ONLY",
        "source_label": SOURCE_LABEL,
        "source_endpoint_family": "BYBIT_V5_MARKET_KLINE",
        "api_base": API_BASE,
        "endpoint_access_status": "PUBLIC_ENDPOINT_ACCESS_OK_RESEARCH_ONLY" if validation["total_rows"] > 0 else "PUBLIC_ENDPOINT_BLOCKED_OR_UNAVAILABLE_RESEARCH_ONLY",
        "endpoint_blocked_or_unavailable": validation["total_rows"] == 0,
        "symbols": symbols,
        "category": category,
        "interval": "1h",
        "bybit_interval_raw": interval,
        "rows_per_symbol": rows_per_symbol,
        "bybit_file_count": len(files),
        "bybit_rows_total": validation["total_rows"],
        "bybit_files": files,
        "file_summaries": validation["file_summaries"],
        "validation": validation,
        "separate_inbox_path": str(root / "crypto_decision_lab" / "manual_intake" / "bybit_inbox"),
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "modeling_status": "BYBIT_PUBLIC_DATA_READY_FOR_MULTI_SOURCE_COMPARISON" if adapter_ready else "BYBIT_PUBLIC_DATA_NEEDS_REVIEW",
        "canonical_data_writes": canonical_data_writes,
        "safe_apply_allowed": safe_apply_allowed,
        "promotion_allowed": promotion_allowed,
        "order_endpoint_used": False,
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

    rp = out / "phase14_bybit_public_data_adapter_pack.json"
    mp = out / "phase14_bybit_public_data_adapter_pack.md"
    hp = out / "index.html"
    ip = out / "phase14_bybit_public_data_adapter_pack_index.json"

    rp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    mp.write_text(
        f"# QRDS/QOS Phase 14 Bybit Public Data Adapter Pack\n\n**Gate answer:** {gate}\n\nRows: {validation['total_rows']}\n\nSource: {SOURCE_LABEL}\n\nOperational status: BLOCKED_RESEARCH_ONLY\n\nNo API key, no account, no order endpoint, no recommendation, no canonical writes.\n",
        encoding="utf-8",
    )
    _render_html(hp, payload)

    index = {
        "schema": "qrds.phase14_bybit_public_data_adapter_pack_index.v1",
        "report_name": payload["report_name"],
        "generated_at": payload["generated_at"],
        "gate_answer": payload["gate_answer"],
        "policy_lock": payload["policy_lock"],
        "app_mode": payload["app_mode"],
        "station": payload["station"],
        "bybit_adapter_ready": payload["bybit_adapter_ready"],
        "data_nature": payload["data_nature"],
        "source_label": payload["source_label"],
        "source_endpoint_family": payload["source_endpoint_family"],
        "endpoint_access_status": payload["endpoint_access_status"],
        "endpoint_blocked_or_unavailable": payload["endpoint_blocked_or_unavailable"],
        "symbols": payload["symbols"],
        "category": payload["category"],
        "interval": payload["interval"],
        "rows_per_symbol": payload["rows_per_symbol"],
        "bybit_file_count": payload["bybit_file_count"],
        "bybit_rows_total": payload["bybit_rows_total"],
        "separate_inbox_path": payload["separate_inbox_path"],
        "operational_status": payload["operational_status"],
        "modeling_status": payload["modeling_status"],
        "order_endpoint_used": payload["order_endpoint_used"],
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


build_bybit_adapter_pack = build_phase14_bybit_public_data_adapter_pack
