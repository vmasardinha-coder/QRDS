#!/usr/bin/env python3
"""Replay canonical V2A functions on a frozen public-input package.

This is migration infrastructure only. It does not change strategy formulas,
parameters, universes, costs, risk rules, or operational status.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
CANONICAL_ROOT = REPO_ROOT / "migration" / "canonical" / "v2a"
CANONICAL_SCRIPT = CANONICAL_ROOT / "scripts" / "00_run_all_v2a.py"
WRAPPER_VERSION = "V2A_FROZEN_REPLAY_1.0"


def _load_canonical():
    spec = importlib.util.spec_from_file_location("gate_btc_canonical_v2a", CANONICAL_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import canonical V2A script: {CANONICAL_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _single_member(archive: zipfile.ZipFile, suffix: str) -> str:
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        raise RuntimeError(f"source package must contain exactly one {suffix}; found {len(matches)}")
    return matches[0]


def _load_source(package: Path) -> dict[str, Any]:
    package_bytes = package.read_bytes()
    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"corrupt source package member: {bad}")
        names = {
            "master": _single_member(archive, "data/processed/qos_v2a_master_daily.csv"),
            "universe": _single_member(archive, "data/raw/coingecko_current_universe_v04.csv"),
            "failures": _single_member(archive, "outputs/download_failures_v2a.csv"),
            "run_manifest": _single_member(archive, "outputs/v2a_run_manifest.json"),
        }
        payloads = {key: archive.read(name) for key, name in names.items()}
        prior_input_names = [name for name in archive.namelist() if name.endswith("outputs/v2a_input_manifest.json")]
        prior_input_manifest = None
        if len(prior_input_names) == 1:
            prior_input_manifest = json.loads(archive.read(prior_input_names[0]).decode("utf-8-sig"))
        elif len(prior_input_names) > 1:
            raise RuntimeError("source package contains multiple V2A input manifests")

    run_manifest = json.loads(payloads["run_manifest"].decode("utf-8-sig"))
    if run_manifest.get("technical_status") != "PASS":
        raise RuntimeError(f"source package technical_status={run_manifest.get('technical_status')!r}")
    if run_manifest.get("operational_status") != "NOT_APPROVED":
        raise RuntimeError("source package operational status is not NOT_APPROVED")
    if run_manifest.get("real_orders", 0) != 0 or run_manifest.get("capital_used", 0) != 0:
        raise RuntimeError("source package violates zero-order / zero-capital lock")

    member_hashes = {
        "data/processed/qos_v2a_master_daily.csv": _sha256_bytes(payloads["master"]),
        "data/raw/coingecko_current_universe_v04.csv": _sha256_bytes(payloads["universe"]),
        "outputs/download_failures_v2a.csv": _sha256_bytes(payloads["failures"]),
    }
    verified_prior_manifest = False
    if prior_input_manifest is not None:
        expected = prior_input_manifest.get("files_sha256", {})
        mismatch = {
            name: {"expected": expected.get(name), "actual": digest}
            for name, digest in member_hashes.items()
            if expected.get(name) != digest
        }
        if mismatch:
            raise RuntimeError(f"source V2A input manifest hash mismatch: {mismatch}")
        verified_prior_manifest = True

    return {
        "package_sha256": _sha256_bytes(package_bytes),
        "payloads": payloads,
        "run_manifest": run_manifest,
        "prior_input_manifest": prior_input_manifest,
        "prior_input_manifest_verified": verified_prior_manifest,
        "member_hashes": member_hashes,
    }


def _write_evidence(evidence_dir: Path, stamp: str, result: dict[str, Any]) -> tuple[Path, Path]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    json_path = evidence_dir / f"V2A_FROZEN_REPLAY_MANIFEST_{stamp}.json"
    txt_path = evidence_dir / f"V2A_FROZEN_REPLAY_REPORT_{stamp}.txt"
    json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
    error_lines = [json.dumps(item, ensure_ascii=False, default=str) for item in result.get("errors", [])] or ["NONE"]
    lines = [
        "GATE BTC — V2A FROZEN PUBLIC-INPUT REPLAY",
        f"STATUS={result.get('technical_status', 'FAIL')}",
        f"DATA_AS_OF={result.get('data_as_of', 'UNAVAILABLE')}",
        f"DATA_CUTOFF={result.get('data_cutoff', 'NONE')}",
        f"INPUT_SNAPSHOT_ID={result.get('input_snapshot_id', 'UNAVAILABLE')}",
        f"SOURCE_PACKAGE_SHA256={result.get('source_package_sha256', 'UNAVAILABLE')}",
        "RESEARCH_ONLY=True",
        "ORDERS_GENERATED=0",
        "REAL_CAPITAL_USED=0",
        "OPERATIONAL_STATUS=NOT_APPROVED",
        "",
        "ERRORS:",
        *error_lines,
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return txt_path, json_path


def replay(source_package: Path, output_zip: Path, data_cutoff: str | None,
           evidence_dir: Path) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%d_%H%M%S")
    result: dict[str, Any] = {
        "schema": "qos-v2a-frozen-replay-v1",
        "wrapper_version": WRAPPER_VERSION,
        "run_utc": started.isoformat(),
        "mode": "frozen_public_input_no_network",
        "technical_status": "RUNNING",
        "data_quality_status": "PENDING",
        "evidence_status": "RESEARCH_ONLY_NOT_PROMOTED",
        "operational_status": "NOT_APPROVED",
        "real_orders": 0,
        "capital_used": 0,
        "data_cutoff": data_cutoff,
        "errors": [],
        "warnings": ["current-universe survivorship bias remains; point-in-time universe is not yet available"],
    }
    canonical = None
    try:
        if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").lower() != "true":
            raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
        for forbidden in ("EXCHANGE_API_SECRET", "EXCHANGE_PRIVATE_KEY", "TRADING_API_KEY"):
            if os.environ.get(forbidden):
                raise RuntimeError(f"forbidden operational credential present: {forbidden}")

        source = _load_source(source_package)
        canonical = _load_canonical()
        canonical.reset_run_dirs()
        canonical.DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
        canonical.DATA_RAW.mkdir(parents=True, exist_ok=True)
        canonical.OUT.mkdir(parents=True, exist_ok=True)
        master_path = canonical.DATA_PROCESSED / "qos_v2a_master_daily.csv"
        universe_path = canonical.DATA_RAW / "coingecko_current_universe_v04.csv"
        failures_path = canonical.OUT / "download_failures_v2a.csv"
        master_path.write_bytes(source["payloads"]["master"])
        universe_path.write_bytes(source["payloads"]["universe"])
        failures_path.write_bytes(source["payloads"]["failures"])

        master = pd.read_csv(io.BytesIO(source["payloads"]["master"]))
        universe = pd.read_csv(io.BytesIO(source["payloads"]["universe"]))
        failures = pd.read_csv(io.BytesIO(source["payloads"]["failures"]))
        required_master = {"date", "symbol", "close_usd", "volume_usd", "source"}
        if not required_master.issubset(master.columns):
            raise RuntimeError(f"frozen master missing columns: {sorted(required_master - set(master.columns))}")
        master["date"] = pd.to_datetime(master["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
        master["symbol"] = master["symbol"].astype(str).str.upper()
        master = master.dropna(subset=["date", "symbol", "close_usd"])
        if master.duplicated(["date", "symbol"]).any():
            raise RuntimeError("frozen master has duplicate date/symbol rows")

        rows_before_cutoff = len(master)
        if data_cutoff:
            cutoff = pd.Timestamp(data_cutoff).normalize()
            master = master[master["date"] <= cutoff].copy()
            if master.empty:
                raise RuntimeError(f"data cutoff {data_cutoff} removed all V2A observations")
        master = master.drop_duplicates(["date", "symbol"]).sort_values(["symbol", "date"])
        if not {"BTC", "ETH"}.issubset(set(master["symbol"])):
            raise RuntimeError("frozen V2A data gate failed: BTC/ETH histories are mandatory")

        if len(master) != rows_before_cutoff:
            canonical.save_df(master, master_path)
            master = pd.read_csv(master_path)
            master["date"] = pd.to_datetime(master["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
            master["symbol"] = master["symbol"].astype(str).str.upper()
        else:
            print(f"preserved frozen input bytes {master_path} rows={len(master):,}", flush=True)

        attempted = int(source["run_manifest"].get("attempted_symbols") or min(int(canonical.CFG["max_assets_to_fetch"]), len(universe)))
        files_sha256 = {
            "data/processed/qos_v2a_master_daily.csv": _sha256_path(master_path),
            "data/raw/coingecko_current_universe_v04.csv": _sha256_path(universe_path),
            "outputs/download_failures_v2a.csv": _sha256_path(failures_path),
        }
        identity = {
            "canonical_version": canonical.VERSION,
            "files_sha256": files_sha256,
            "data_cutoff": data_cutoff,
            "attempted_symbols": attempted,
        }
        input_snapshot_id = _sha256_bytes(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        input_manifest = {
            "schema": "qos-v2a-input-snapshot-v1",
            "canonical_version": canonical.VERSION,
            "input_snapshot_id": input_snapshot_id,
            "files_sha256": files_sha256,
            "data_cutoff": data_cutoff,
            "data_as_of": master["date"].max().date().isoformat(),
            "attempted_symbols": attempted,
            "loaded_symbols": int(master["symbol"].nunique()),
            "failed_symbols": int(len(failures)),
            "source_package_sha256": source["package_sha256"],
            "source_package_input_manifest_verified": source["prior_input_manifest_verified"],
            "research_only": True,
            "orders_generated": 0,
            "real_capital_used": 0,
            "operational_status": "NOT_APPROVED",
        }
        canonical.save_json(input_manifest, canonical.OUT / "v2a_input_manifest.json")

        features, close, current_features, data_as_of = canonical.compute_monthly_features(master)
        if features.empty or current_features.empty:
            raise RuntimeError("V2A feature gate failed during frozen replay")
        equity, allocations, trades, summary = canonical.run_backtest(features, close)
        current = canonical.current_signal(current_features, data_as_of)
        references = canonical.reference_compositions(close.columns, data_as_of)
        bear_replay = canonical.v2a_bear_replay(equity)
        monte_carlo = canonical.v2a_monte_carlo(equity, False)
        canonical.make_charts(equity, summary)

        loaded_symbols = int(master["symbol"].nunique())
        coverage = loaded_symbols / max(1, attempted)
        data_status = "PASS" if loaded_symbols >= 30 and coverage >= 0.45 else "PARTIAL_DATA_WARNING"
        result.update({
            "version": canonical.VERSION,
            "technical_status": "PASS",
            "data_quality_status": data_status,
            "data_as_of": str(data_as_of.date()),
            "attempted_symbols": attempted,
            "loaded_symbols": loaded_symbols,
            "failed_symbols": int(len(failures)),
            "coverage_ratio": coverage,
            "input_snapshot_id": input_snapshot_id,
            "input_files_sha256": files_sha256,
            "source_package_sha256": source["package_sha256"],
            "source_package_input_manifest_verified": source["prior_input_manifest_verified"],
            "historical_signal_rows": len(features),
            "current_feature_rows": len(current_features),
            "equity_rows": len(equity),
            "current_portfolio_rows": len(current),
            "reference_composition_rows": len(references),
            "bear_replay_rows": len(bear_replay),
            "monte_carlo_rows": len(monte_carlo),
            "long_horizon_scoreboard_rows": len(summary),
            "lookahead_guard": "signals execute on next daily bar",
            "partial_month_guard": "current month excluded from historical backtest",
            "portfolio_roles": {"managed_qos": 4, "public_benchmarks": 2, "static_user_proxy": 1},
            "monte_carlo_role": "SCENARIO_ENGINE_NOT_ALPHA",
        })
        if not source["prior_input_manifest_verified"]:
            result["warnings"].append("source package had no prior V2A input manifest; GitHub artifact digest remains the outer trust anchor")

        canonical.save_df(pd.DataFrame([{
            "data_as_of": data_as_of,
            "attempted_symbols": attempted,
            "loaded_symbols": loaded_symbols,
            "failed_symbols": len(failures),
            "coverage_ratio": coverage,
            "data_quality_status": data_status,
            "survivorship_bias_present": True,
        }]), canonical.OUT / "data_quality_summary.csv")
        (canonical.OUT / "EVIDENCE_STATUS.md").write_text(
            "# V2A evidence status\n\n"
            "- Technical execution: PASS\n"
            f"- Data quality: {data_status}\n"
            f"- Input snapshot: {input_snapshot_id}\n"
            f"- Data cutoff: {data_cutoff or 'NONE'}\n"
            "- Historical execution: next daily bar after signal close\n"
            "- Current-universe survivorship bias: PRESENT\n"
            "- Operational promotion: NOT APPROVED\n",
            encoding="utf-8",
        )
        canonical.save_json(result, canonical.OUT / "v2a_run_manifest.json")
        output_zip.parent.mkdir(parents=True, exist_ok=True)
        canonical.validated_zip(canonical.ROOT, output_zip)
        result["output_zip"] = str(output_zip)
        result["output_zip_sha256"] = _sha256_path(output_zip)
    except Exception as exc:
        result["technical_status"] = "FAIL"
        result["data_quality_status"] = "NOT_EVALUATED"
        result["errors"].append({
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        })
        if canonical is not None:
            canonical.OUT.mkdir(parents=True, exist_ok=True)
            canonical.save_json(result, canonical.OUT / "v2a_run_manifest.json")
    finally:
        _write_evidence(evidence_dir, stamp, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_package", type=Path)
    parser.add_argument("--output-zip", type=Path, required=True)
    parser.add_argument("--data-cutoff")
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    evidence_dir = args.evidence_dir or args.output_zip.parent
    result = replay(args.source_package, args.output_zip, args.data_cutoff, evidence_dir)
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result["technical_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
