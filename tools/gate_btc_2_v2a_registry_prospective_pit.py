#!/usr/bin/env python3
"""Registry-driven, fail-closed prospective PIT collector for GATE BTC 2.0 V2A.

Consumes only the already-admitted complete qualified-source registry.  It never
switches venue/source after seeing a result and never backfills.  The output is
runtime-ready evidence for the frozen cutover gate; it carries zero scientific
or economic credit.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

EPOCH_ID = "GATE_BTC_2_V2A_PROSPECTIVE_EPOCH_2026_09_03"
RUNTIME_REGISTRY_SCHEMA = "gate_btc.v2a_prospective_qualified_source_registry.v1"
SNAPSHOT_SCHEMA = "gate_btc.v2a_point_in_time_data_snapshot.v1"
STATUS_SCHEMA = "gate_btc.v2a_point_in_time_data_ledger_status.v1"
UA = "QRDS-GateBTC2-Prospective-PIT/1"


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _get(url: str, retries: int = 3) -> bytes:
    last: Exception | None = None
    for n in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(req, timeout=45) as r:
                raw = r.read()
                if not raw:
                    raise RuntimeError("empty response")
                return raw
        except Exception as exc:  # fail-closed after bounded retries
            last = exc
            time.sleep(1.5 * (n + 1))
    raise RuntimeError(f"request failed: {last}")


def _url(base: str, params: dict[str, Any]) -> str:
    return base + "?" + urllib.parse.urlencode(params, doseq=True)


def _probe(entry: dict[str, Any], now: datetime) -> tuple[str, bytes]:
    identity = str(entry["source_identity"])
    symbol = str(entry["source_symbol"])
    upper = identity.upper()

    if upper.startswith("BINANCE_SPOT"):
        u = _url("https://data-api.binance.vision/api/v3/klines", {"symbol": symbol, "interval": "1d", "limit": 2})
        return u, _get(u)
    if upper.startswith("OKX_SPOT") or upper.startswith("OKX_PUBLIC_SPOT"):
        u = _url("https://www.okx.com/api/v5/market/candles", {"instId": symbol, "bar": "1Dutc", "limit": 2})
        return u, _get(u)
    if upper.startswith("GATE_SPOT"):
        u = _url("https://api.gateio.ws/api/v4/spot/candlesticks", {"currency_pair": symbol, "interval": "1d", "limit": 2})
        return u, _get(u)
    if upper.startswith("MEXC_SPOT"):
        u = _url("https://api.mexc.com/api/v3/klines", {"symbol": symbol, "interval": "1d", "limit": 2})
        return u, _get(u)
    if upper.startswith("BITGET_SPOT"):
        u = _url("https://api.bitget.com/api/v2/spot/market/candles", {"symbol": symbol, "granularity": "1day", "limit": 2})
        return u, _get(u)
    if upper.startswith("BYBIT_SPOT"):
        # Qualification for these identities was execution-archive based; use a
        # current public execution print, not a derived/index price.
        u = _url("https://api.bybit.com/v5/market/recent-trade", {"category": "spot", "symbol": symbol, "limit": 1})
        return u, _get(u)
    if upper.startswith("COINBASE_EXCHANGE_SPOT"):
        product = symbol
        u = _url(f"https://api.exchange.coinbase.com/products/{urllib.parse.quote(product, safe='-')}/candles", {"granularity": 86400})
        return u, _get(u)
    if upper.startswith("KRAKEN"):
        pair = symbol.replace("/", "")
        u = _url("https://api.kraken.com/0/public/OHLC", {"pair": pair, "interval": 1440})
        return u, _get(u)
    if upper.startswith("GECKOTERMINAL_PUBLIC_ONCHAIN"):
        # source_symbol is frozen as network:pool_address.
        network, pool = symbol.split(":", 1)
        u = _url(
            f"https://api.geckoterminal.com/api/v2/networks/{urllib.parse.quote(network, safe='')}/pools/{urllib.parse.quote(pool, safe='')}/ohlcv/day",
            {"aggregate": 1, "limit": 2, "currency": "usd"},
        )
        return u, _get(u)
    if upper.startswith("DERIBIT_SPOT"):
        end_ms = int(now.timestamp() * 1000)
        start_ms = int((now - timedelta(days=3)).timestamp() * 1000)
        u = _url(
            "https://www.deribit.com/api/v2/public/get_tradingview_chart_data",
            {"instrument_name": symbol, "start_timestamp": start_ms, "end_timestamp": end_ms, "resolution": "1D"},
        )
        return u, _get(u)
    if upper.startswith("FIGURE_MARKETS"):
        base = "https://api.figuremarkets.com/public"
        iu = f"{base}/v1/markets/{urllib.parse.quote(symbol, safe='')}"
        identity_raw = _get(iu)
        start = (now.date() - timedelta(days=2)).isoformat() + "T00:00:00Z"
        end = now.date().isoformat() + "T23:59:59Z"
        cu = _url(
            f"{base}/v1/markets/{urllib.parse.quote(symbol, safe='')}/candles",
            {"start_date": start, "end_date": end, "interval_in_minutes": "1440", "candle_type": "TRADE"},
        )
        candle_raw = _get(cu)
        return cu, identity_raw + b"\n" + candle_raw
    raise RuntimeError(f"unsupported frozen source_identity={identity}")


def _response_has_observation(entry: dict[str, Any], raw: bytes) -> bool:
    try:
        payload = json.loads(raw.split(b"\n", 1)[-1].decode())
    except Exception:
        return False
    identity = str(entry["source_identity"]).upper()
    if identity.startswith("BINANCE_SPOT") or identity.startswith("MEXC_SPOT") or identity.startswith("BITGET_SPOT"):
        return isinstance(payload, list) and len(payload) > 0
    if identity.startswith("OKX_SPOT") or identity.startswith("OKX_PUBLIC_SPOT"):
        return isinstance(payload, dict) and str(payload.get("code")) == "0" and bool(payload.get("data"))
    if identity.startswith("GATE_SPOT"):
        return isinstance(payload, list) and len(payload) > 0
    if identity.startswith("BYBIT_SPOT"):
        return isinstance(payload, dict) and str(payload.get("retCode")) == "0" and bool((payload.get("result") or {}).get("list"))
    if identity.startswith("COINBASE_EXCHANGE_SPOT"):
        return isinstance(payload, list) and len(payload) > 0
    if identity.startswith("KRAKEN"):
        return isinstance(payload, dict) and not payload.get("error") and bool(payload.get("result"))
    if identity.startswith("GECKOTERMINAL_PUBLIC_ONCHAIN"):
        attrs = (((payload or {}).get("data") or {}).get("attributes") or {}) if isinstance(payload, dict) else {}
        return bool(attrs.get("ohlcv_list"))
    if identity.startswith("DERIBIT_SPOT"):
        return isinstance(payload, dict) and bool((payload.get("result") or {}).get("ticks"))
    if identity.startswith("FIGURE_MARKETS"):
        return isinstance(payload, dict) and bool(payload.get("matchHistoryData"))
    return False


def _provenance(entry: dict[str, Any]) -> str:
    value = entry.get("provenance_sha256")
    if isinstance(value, str) and len(value) == 64:
        return value
    raw = entry.get("raw_response_sha256")
    if isinstance(raw, str) and len(raw) == 64:
        return raw
    if isinstance(raw, list) and raw and isinstance(raw[0], str) and len(raw[0]) == 64:
        return raw[0]
    artifact = entry.get("evidence_artifact_sha256")
    if isinstance(artifact, str) and len(artifact) == 64:
        return artifact
    raise ValueError(f"no frozen provenance hash for {entry.get('symbol')}")


def _runtime_registry(source: dict[str, Any]) -> dict[str, Any]:
    entries = []
    for src in source.get("entries", []):
        if src.get("qualification") != "QUALIFIED_EXACT_SOURCE" or src.get("qa_pass") is not True:
            raise ValueError(f"unqualified registry entry: {src.get('symbol')}")
        e = dict(src)
        e["provenance_sha256"] = _provenance(e)
        e["observed_vs_derived"] = "OBSERVED"
        entries.append(e)
    if len(entries) != 137 or len({e.get("symbol") for e in entries}) != 137:
        raise ValueError("complete registry is not exactly 137 unique symbols")
    return {
        "schema": RUNTIME_REGISTRY_SCHEMA,
        "epoch_id": EPOCH_ID,
        "entries": entries,
        "entry_count": 137,
        "qualification": "COMPLETE_QUALIFIED_EXACT_SOURCE_REGISTRY",
        "observed_vs_derived": "OBSERVED",
        "historical_credit": 0,
        "prospective_credit_before_d0": 0,
        "backfill_performed": False,
        "counter_reset_performed": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "promotion_allowed": False,
    }


def _csv_bytes(rows: list[dict[str, Any]], fields: list[str]) -> bytes:
    sio = io.StringIO(newline="")
    w = csv.DictWriter(sio, fieldnames=fields)
    w.writeheader()
    for row in rows:
        w.writerow({k: row.get(k, "") for k in fields})
    return sio.getvalue().encode()


def _gzip_bytes(raw: bytes) -> bytes:
    bio = io.BytesIO()
    with gzip.GzipFile(fileobj=bio, mode="wb", mtime=0) as gz:
        gz.write(raw)
    return bio.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    ap.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID", "manual"))
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    source = json.loads(args.registry.read_text(encoding="utf-8"))
    runtime_registry = _runtime_registry(source)
    out = args.output_dir
    snapdir = out / "snapshots"
    archivedir = out / "archives"
    snapdir.mkdir(parents=True, exist_ok=True)
    archivedir.mkdir(parents=True, exist_ok=True)

    observations: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for e in runtime_registry["entries"]:
        symbol = str(e["symbol"])
        try:
            url, raw = _probe(e, now)
            ok = _response_has_observation(e, raw)
            row = {
                "symbol": symbol,
                "source_identity": e["source_identity"],
                "source_symbol": e["source_symbol"],
                "url": url,
                "raw_sha256": _sha(raw),
                "observed": ok,
            }
            observations.append(row)
            if not ok:
                failures.append({"symbol": symbol, "reason": "NO_CURRENT_OBSERVATION", "source_identity": e["source_identity"]})
        except Exception as exc:
            failures.append({"symbol": symbol, "reason": str(exc), "source_identity": e["source_identity"]})

    attempted = len(runtime_registry["entries"])
    loaded = attempted - len(failures)
    coverage = loaded / attempted if attempted else 0.0
    run_tag = f"{now.date().isoformat()}-registry-pit-{args.run_id}"

    universe_raw = _csv_bytes(
        [{"symbol": e["symbol"], "source_identity": e["source_identity"], "source_symbol": e["source_symbol"]} for e in runtime_registry["entries"]],
        ["symbol", "source_identity", "source_symbol"],
    )
    quality_raw = _csv_bytes(observations, ["symbol", "source_identity", "source_symbol", "url", "raw_sha256", "observed"])
    failures_raw = _csv_bytes(failures, ["symbol", "source_identity", "reason"])
    manifest_raw = _json_bytes({"run_tag": run_tag, "observations": observations, "failures": failures})

    def archive(name: str, raw: bytes) -> dict[str, Any]:
        gz = _gzip_bytes(raw)
        path = archivedir / f"{run_tag}.{name}.gz"
        path.write_bytes(gz)
        return {
            "archive_format": "gzip_mtime_0_exact_source_bytes",
            "archive_path": f"archives/{path.name}",
            "archive_sha256": _sha(gz),
            "raw_sha256": _sha(raw),
            "raw_size_bytes": len(raw),
        }

    universe_archive = archive("qualified_source_universe.csv", universe_raw)
    quality_archive = archive("source_observation_quality.csv", quality_raw)
    failures_archive = archive("source_failures.csv", failures_raw)

    snapshot: dict[str, Any] = {
        "schema": SNAPSHOT_SCHEMA,
        "snapshot_id": run_tag,
        "source_run_id": str(args.run_id),
        "source_run_utc": now.isoformat(),
        "source_data_as_of": now.date().isoformat(),
        "attempted_symbols": attempted,
        "loaded_symbols": loaded,
        "failed_symbols": len(failures),
        "coverage_ratio": coverage,
        "download_failure_row_count": len(failures),
        "no_candle_failure_count": len(failures),
        "short_history_failure_count": 0,
        "prospective_point_in_time_universe_observed": True,
        "prospective_point_in_time_universe_bias_present": False,
        "historical_model_survivorship_bias_present": True,
        "survivorship_bias_present": True,
        "retrospective_reconstruction": False,
        "purpose": "FUTURE_POINT_IN_TIME_UNIVERSE_AND_DATA_QUALITY_EVIDENCE_ONLY",
        "selected_sources": {e["symbol"]: {"source_identity": e["source_identity"], "source_symbol": e["source_symbol"]} for e in runtime_registry["entries"]},
        "source_hashes": {
            "manifest_sha256": _sha(manifest_raw),
            "universe_sha256": universe_archive["raw_sha256"],
            "quality_sha256": quality_archive["raw_sha256"],
            "failures_sha256": failures_archive["raw_sha256"],
        },
        "universe_archive": universe_archive,
        "quality_archive": quality_archive,
        "failures_archive": failures_archive,
        "universe_row_count": attempted,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "feeds_frozen_engine": False,
        "historical_credit": 0,
        "prospective_credit_before_d0": 0,
        "backfill_performed": False,
        "counter_reset_performed": False,
    }
    record_basis = dict(snapshot)
    snapshot["record_sha256"] = _sha(_json_bytes(record_basis))

    status = {
        "schema": STATUS_SCHEMA,
        "status": "ACTIVE_RESEARCH_ONLY",
        "latest_snapshot_id": run_tag,
        "latest_source_run_id": str(args.run_id),
        "latest_source_data_as_of": now.date().isoformat(),
        "latest_attempted_symbols": attempted,
        "latest_loaded_symbols": loaded,
        "latest_failed_symbols": len(failures),
        "latest_coverage_ratio": coverage,
        "latest_no_candle_failure_count": len(failures),
        "latest_short_history_failure_count": 0,
        "snapshot_count": 1,
        "prospective_point_in_time_universe_observed": True,
        "prospective_point_in_time_universe_bias_present": False,
        "historical_model_survivorship_bias_present": True,
        "survivorship_bias_present": True,
        "future_point_in_time_only": True,
        "retrospective_backfill_allowed": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "feeds_frozen_engine": False,
    }
    status["status_sha256"] = _sha(_json_bytes(status))

    (out / "QUALIFIED_SOURCE_REGISTRY.json").write_text(json.dumps(runtime_registry, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (snapdir / f"{run_tag}.json").write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "STATUS.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "MANIFEST.json").write_bytes(manifest_raw)

    summary = {
        "schema": "gate_btc.v2a_registry_prospective_pit_activation.v1",
        "snapshot_id": run_tag,
        "attempted": attempted,
        "loaded": loaded,
        "failed": len(failures),
        "coverage_ratio": coverage,
        "failures": failures,
        "cutover_input_pass": attempted == 137 and loaded == 137 and not failures,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "fail_closed": True,
    }
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["cutover_input_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
