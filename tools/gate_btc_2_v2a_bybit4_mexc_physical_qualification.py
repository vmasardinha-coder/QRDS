#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

try:
    from tools import gate_btc_2_v2a_exact_spot_qualification_runner as q
except ModuleNotFoundError:
    import gate_btc_2_v2a_exact_spot_qualification_runner as q

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "tools/gate_btc_2_v2a_bybit4_mexc_source_prereg_v1.json"
REGISTRY = ROOT / "tools/gate_btc_2_v2a_complete_qualified_source_registry_v1.json"
START = date.fromisoformat("2026-08-04")
END = date.fromisoformat("2026-09-05")
EXPECTED_DAYS = [(START + timedelta(days=i)).isoformat() for i in range((END - START).days + 1)]


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry_entry(registry: dict, symbol: str) -> dict:
    hits = [e for e in registry.get("entries", []) if e.get("symbol") == symbol]
    if len(hits) != 1:
        raise ValueError(f"registry must contain exactly one {symbol} entry")
    e = hits[0]
    if e.get("source_identity") != "BYBIT_SPOT":
        raise ValueError(f"{symbol} current registry source is not BYBIT_SPOT")
    if e.get("source_symbol") != f"{symbol}USDT":
        raise ValueError(f"{symbol} BYBIT source symbol mismatch")
    if not e.get("provenance_sha256"):
        raise ValueError(f"{symbol} missing frozen provenance binding")
    return e


def main() -> int:
    prereg = _load(PREREG)
    registry = _load(REGISTRY)
    out_root = ROOT / "artifacts/gate_btc_2/v2a_bybit4_mexc_physical"
    out_root.mkdir(parents=True, exist_ok=True)

    prereg_sha = hashlib.sha256(PREREG.read_bytes()).hexdigest()
    results = []

    for target in prereg["targets"]:
        symbol = target["symbol"]
        candidate = target["candidate_source"]
        pair = candidate["pair"]
        if candidate["provider"] != "MEXC" or candidate["market"] != "SPOT":
            raise ValueError(f"{symbol} prereg candidate is not MEXC spot")
        if pair != f"{symbol}USDT":
            raise ValueError(f"{symbol} prereg pair mismatch")

        prior = _registry_entry(registry, symbol)
        target_out = out_root / symbol
        target_out.mkdir(parents=True, exist_ok=True)

        status = "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR"
        error = None
        qa = None
        try:
            raw = q.collect("MEXC", pair, symbol, "USDT", END, target_out, 1)
            rows = [r for r in raw["rows"] if START.isoformat() <= r["day"] <= END.isoformat()]
            days = [r["day"] for r in rows]
            unique_days = sorted(set(days))
            missing = [d for d in EXPECTED_DAYS if d not in set(days)]
            duplicates = len(days) - len(unique_days)
            exact_33 = unique_days == EXPECTED_DAYS and len(rows) == 33
            qa_pass = bool(raw["qa_pass"] and exact_33 and not missing and duplicates == 0)
            status = "QUALIFIED_EXACT_SOURCE" if qa_pass else "FAIL_CLOSED_FULL_CORPUS_QA"
            qa = {
                "qa_pass": qa_pass,
                "physical_rows_in_frozen_window": len(rows),
                "unique_daily_buckets": len(unique_days),
                "missing_days": missing,
                "duplicate_rows_in_frozen_window": duplicates,
                "earliest_day": unique_days[0] if unique_days else None,
                "latest_day": unique_days[-1] if unique_days else None,
                "identity_sha256": raw["identity_sha256"],
                "pages": raw["pages"],
                "source_surface": raw["source_surface"],
            }
        except Exception as exc:
            error = str(exc)
            qa = {"qa_pass": False, "error": error}

        result = {
            "schema_version": "GATE_BTC_2_V2A_BYBIT4_MEXC_PHYSICAL_QUALIFICATION_V1",
            "symbol": symbol,
            "frozen_prior_source_identity": prior["source_identity"],
            "frozen_prior_source_symbol": prior["source_symbol"],
            "frozen_prior_provenance_sha256": prior["provenance_sha256"],
            "candidate_source_identity": "MEXC_SPOT",
            "candidate_source_symbol": pair,
            "prereg_sha256": prereg_sha,
            "window_start_utc": START.isoformat(),
            "window_end_utc": END.isoformat(),
            "required_unique_daily_buckets": 33,
            "status": status,
            "qa": qa,
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "engine_feed": False,
            "orders": 0,
            "real_capital_brl": 0,
            "no_retune": True,
            "no_backfill": True,
            "no_counter_reset": True,
            "no_silent_source_substitution": True,
            "fail_closed": True,
            "scientific_credit": 0,
            "prospective_credit": 0,
            "economic_credit": 0,
            "source_admission": False,
            "d0_started": False,
        }
        (target_out / "QUALIFICATION.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        results.append(result)

    passed = [r for r in results if r["status"] == "QUALIFIED_EXACT_SOURCE" and r["qa"].get("qa_pass")]
    summary = {
        "schema_version": "GATE_BTC_2_V2A_BYBIT4_MEXC_PHYSICAL_SUMMARY_V1",
        "targets": len(results),
        "passed": len(passed),
        "failed": len(results) - len(passed),
        "all_pass": len(passed) == len(results) == 4,
        "symbols_passed": [r["symbol"] for r in passed],
        "symbols_failed": [r["symbol"] for r in results if r not in passed],
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
        "scientific_credit": 0,
        "prospective_credit": 0,
        "economic_credit": 0,
        "source_admission": False,
        "d0_started": False,
    }
    (out_root / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["all_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
