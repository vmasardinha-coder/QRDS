#!/usr/bin/env python3
"""Replay canonical Delta on frozen public inputs without changing methodology."""
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
CANONICAL_ROOT = REPO_ROOT / "migration" / "canonical" / "delta"
CANONICAL_SCRIPT = CANONICAL_ROOT / "scripts" / "00_run_delta_v11.py"
WRAPPER_VERSION = "DELTA_FROZEN_REPLAY_1.0"
INPUT_FILES = {
    "ohlc": "inputs/delta_ohlc_daily.csv",
    "funding": "inputs/delta_funding_events.csv",
    "quality": "inputs/data_quality_by_asset.csv",
    "failures": "inputs/download_failures.csv",
}


def _load_canonical():
    spec = importlib.util.spec_from_file_location("gate_btc_canonical_delta", CANONICAL_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import canonical Delta script: {CANONICAL_SCRIPT}")
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


def _safe_manifest(manifest: dict[str, Any]) -> None:
    if manifest.get("technical_status") != "PASS":
        raise RuntimeError(f"source package technical_status={manifest.get('technical_status')!r}")
    if manifest.get("operational_status") != "NOT_APPROVED":
        raise RuntimeError("source package operational status is not NOT_APPROVED")
    if manifest.get("real_orders", 0) != 0 or manifest.get("capital_used", 0) != 0:
        raise RuntimeError("source package violates zero-order / zero-capital lock")


def _read_source(source_package: Path, source_data_dir: Path | None) -> dict[str, Any]:
    package_bytes = source_package.read_bytes()
    with zipfile.ZipFile(io.BytesIO(package_bytes)) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"corrupt source package member: {bad}")
        snapshot_matches = [
            name for name in archive.namelist()
            if name.endswith("delta_input_snapshot_manifest.json")
        ]
        if len(snapshot_matches) > 1:
            raise RuntimeError("source package contains multiple Delta input manifests")
        if snapshot_matches:
            snapshot_manifest = json.loads(
                archive.read(snapshot_matches[0]).decode("utf-8-sig")
            )
            _safe_manifest(snapshot_manifest)
            payloads = {
                key: archive.read(_single_member(archive, member))
                for key, member in INPUT_FILES.items()
            }
            expected = snapshot_manifest.get("files_sha256", {})
            actual = {
                INPUT_FILES[key]: _sha256_bytes(payload)
                for key, payload in payloads.items()
            }
            mismatch = {
                name: {"expected": expected.get(name), "actual": digest}
                for name, digest in actual.items()
                if expected.get(name) != digest
            }
            if mismatch:
                raise RuntimeError(f"source Delta input manifest hash mismatch: {mismatch}")
            source_run_matches = [
                name for name in archive.namelist()
                if name.endswith("source_delta_run_manifest.json")
            ]
            source_run_manifest = (
                json.loads(archive.read(source_run_matches[0]).decode("utf-8-sig"))
                if len(source_run_matches) == 1 else snapshot_manifest
            )
            return {
                "package_sha256": _sha256_bytes(package_bytes),
                "payloads": payloads,
                "source_run_manifest": source_run_manifest,
                "prior_input_manifest": snapshot_manifest,
                "prior_input_manifest_verified": True,
            }

        source_run_manifest = json.loads(
            archive.read(_single_member(archive, "outputs/delta_v11_run_manifest.json")).decode("utf-8-sig")
        )
        _safe_manifest(source_run_manifest)
        quality = archive.read(_single_member(archive, "outputs/data_quality_by_asset.csv"))
        failures = archive.read(_single_member(archive, "outputs/download_failures.csv"))
    if source_data_dir is None:
        raise RuntimeError("canonical Delta output omits raw inputs; --source-data-dir is required")
    ohlc_path = source_data_dir / "delta_ohlc_daily.csv"
    funding_path = source_data_dir / "delta_funding_events.csv"
    if not ohlc_path.is_file() or not funding_path.is_file():
        raise RuntimeError(f"missing canonical Delta data files under {source_data_dir}")
    return {
        "package_sha256": _sha256_bytes(package_bytes),
        "payloads": {
            "ohlc": ohlc_path.read_bytes(),
            "funding": funding_path.read_bytes(),
            "quality": quality,
            "failures": failures,
        },
        "source_run_manifest": source_run_manifest,
        "prior_input_manifest": None,
        "prior_input_manifest_verified": False,
    }


def _quality_table(ohlc: pd.DataFrame, funding: pd.DataFrame) -> pd.DataFrame:
    ohlc_quality = ohlc.groupby("symbol", as_index=False).agg(
        ohlc_rows=("date", "size"),
        ohlc_start=("date", "min"),
        ohlc_end=("date", "max"),
    )
    funding_quality = (
        funding.groupby("symbol", as_index=False).agg(
            funding_events=("date", "size"),
            funding_start=("date", "min"),
            funding_end=("date", "max"),
        )
        if not funding.empty
        else pd.DataFrame(
            columns=["symbol", "funding_events", "funding_start", "funding_end"]
        )
    )
    return ohlc_quality.merge(funding_quality, on="symbol", how="left")


def _write_snapshot(
    snapshot_zip: Path,
    canonical: Any,
    source: dict[str, Any],
    data_cutoff: str | None,
) -> dict[str, Any]:
    paths = {
        INPUT_FILES["ohlc"]: canonical.DATA / "delta_ohlc_daily.csv",
        INPUT_FILES["funding"]: canonical.DATA / "delta_funding_events.csv",
        INPUT_FILES["quality"]: canonical.OUT / "data_quality_by_asset.csv",
        INPUT_FILES["failures"]: canonical.OUT / "download_failures.csv",
    }
    files_sha256 = {name: _sha256_path(path) for name, path in paths.items()}
    identity = {
        "canonical_version": canonical.VERSION,
        "files_sha256": files_sha256,
        "data_cutoff": data_cutoff,
    }
    snapshot_id = _sha256_bytes(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )
    ohlc = pd.read_csv(paths[INPUT_FILES["ohlc"]])
    input_manifest = {
        "schema": "delta-input-snapshot-v1",
        "wrapper_version": WRAPPER_VERSION,
        "technical_status": "PASS",
        "operational_status": "NOT_APPROVED",
        "real_orders": 0,
        "capital_used": 0,
        "canonical_version": canonical.VERSION,
        "input_snapshot_id": snapshot_id,
        "files_sha256": files_sha256,
        "data_cutoff": data_cutoff,
        "data_as_of": pd.to_datetime(ohlc["date"]).max().date().isoformat(),
        "loaded_assets": int(ohlc["symbol"].nunique()),
        "source_package_sha256": source["package_sha256"],
        "source_package_input_manifest_verified": source["prior_input_manifest_verified"],
        "research_only": True,
    }
    snapshot_zip.parent.mkdir(parents=True, exist_ok=True)
    partial = snapshot_zip.with_suffix(".partial.zip")
    if partial.exists():
        partial.unlink()
    with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, path in paths.items():
            archive.write(path, name)
        archive.writestr(
            "delta_input_snapshot_manifest.json",
            json.dumps(input_manifest, indent=2, ensure_ascii=False, default=str) + "\n",
        )
        archive.writestr(
            "source_delta_run_manifest.json",
            json.dumps(
                source["source_run_manifest"],
                indent=2,
                ensure_ascii=False,
                default=str,
            ) + "\n",
        )
    os.replace(partial, snapshot_zip)
    return input_manifest


def _write_evidence(evidence_dir: Path, stamp: str, result: dict[str, Any]) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    json_path = evidence_dir / f"DELTA_FROZEN_REPLAY_MANIFEST_{stamp}.json"
    txt_path = evidence_dir / f"DELTA_FROZEN_REPLAY_REPORT_{stamp}.txt"
    json_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )
    errors = [
        json.dumps(item, ensure_ascii=False, default=str)
        for item in result.get("errors", [])
    ] or ["NONE"]
    lines = [
        "GATE BTC — DELTA FROZEN PUBLIC-INPUT REPLAY",
        f"STATUS={result.get('technical_status', 'FAIL')}",
        f"DATA_AS_OF={result.get('data_as_of', 'UNAVAILABLE')}",
        f"DATA_CUTOFF={result.get('data_cutoff', 'NONE')}",
        f"INPUT_SNAPSHOT_ID={result.get('input_snapshot_id', 'UNAVAILABLE')}",
        "RESEARCH_ONLY=True",
        "ORDERS_GENERATED=0",
        "REAL_CAPITAL_USED=0",
        "OPERATIONAL_STATUS=NOT_APPROVED",
        "",
        "ERRORS:",
        *errors,
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def replay(
    source_package: Path,
    output_zip: Path,
    data_cutoff: str | None,
    evidence_dir: Path,
    source_data_dir: Path | None = None,
    input_snapshot_zip: Path | None = None,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%d_%H%M%S")
    result: dict[str, Any] = {
        "schema": "delta-frozen-replay-v1",
        "wrapper_version": WRAPPER_VERSION,
        "run_utc": started.isoformat(),
        "mode": "frozen_public_input_no_network",
        "technical_status": "RUNNING",
        "data_quality_status": "PENDING",
        "operational_status": "NOT_APPROVED",
        "real_orders": 0,
        "capital_used": 0,
        "data_cutoff": data_cutoff,
        "errors": [],
    }
    canonical = None
    try:
        if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").lower() != "true":
            raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
        for forbidden in ("EXCHANGE_API_SECRET", "EXCHANGE_PRIVATE_KEY", "TRADING_API_KEY"):
            if os.environ.get(forbidden):
                raise RuntimeError(f"forbidden operational credential present: {forbidden}")

        source = _read_source(source_package, source_data_dir)
        ohlc = pd.read_csv(
            io.BytesIO(source["payloads"]["ohlc"]),
            float_precision="round_trip",
        )
        funding = pd.read_csv(
            io.BytesIO(source["payloads"]["funding"]),
            float_precision="round_trip",
        )
        failures = pd.read_csv(io.BytesIO(source["payloads"]["failures"]))
        required_ohlc = {
            "date", "symbol", "open", "high", "low", "close", "volume", "source"
        }
        if not required_ohlc.issubset(ohlc.columns):
            raise RuntimeError(
                f"frozen Delta OHLC missing columns: {sorted(required_ohlc - set(ohlc.columns))}"
            )
        ohlc["date"] = pd.to_datetime(ohlc["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
        funding["date"] = pd.to_datetime(funding["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
        ohlc["symbol"] = ohlc["symbol"].astype(str).str.upper()
        funding["symbol"] = funding["symbol"].astype(str).str.upper()
        ohlc = ohlc.dropna(subset=["date", "symbol", "close"])
        funding = funding.dropna(subset=["date", "symbol", "funding_rate"])
        if data_cutoff:
            cutoff = pd.Timestamp(data_cutoff).normalize()
            ohlc = ohlc[ohlc["date"] <= cutoff].copy()
            funding = funding[funding["date"] <= cutoff].copy()
        if ohlc.empty:
            raise RuntimeError("Delta cutoff removed all OHLC observations")
        loaded = sorted(ohlc["symbol"].unique())
        canonical = _load_canonical()
        if "BTC" not in loaded:
            raise RuntimeError("BTC OHLC is mandatory")
        if len(loaded) < int(canonical.CFG["minimum_loaded_assets"]):
            raise RuntimeError(f"insufficient OHLC assets after cutoff: {len(loaded)}")
        quality = _quality_table(ohlc, funding)

        original_collect = canonical.collect_public_data
        original_zip_tree = canonical.zip_tree
        captured: dict[str, Any] = {}

        def frozen_collect():
            return ohlc.copy(), funding.copy(), quality.copy(), failures.copy()

        def evidence_zip(source_dir: Path, destination: Path) -> None:
            snapshot_target = input_snapshot_zip or output_zip.with_name(
                f"{output_zip.stem}_input_snapshot.zip"
            )
            input_manifest = _write_snapshot(
                snapshot_target,
                canonical,
                source,
                data_cutoff,
            )
            manifest_path = canonical.OUT / "delta_v11_run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest.update({
                "schema": "delta-frozen-replay-v1",
                "wrapper_version": WRAPPER_VERSION,
                "mode": "frozen_public_input_no_network",
                "data_cutoff": data_cutoff,
                "input_snapshot_id": input_manifest["input_snapshot_id"],
                "input_files_sha256": input_manifest["files_sha256"],
                "source_package_sha256": source["package_sha256"],
                "source_package_input_manifest_verified": source["prior_input_manifest_verified"],
            })
            canonical.write_json(manifest_path, manifest)
            canonical.write_json(
                canonical.OUT / "delta_input_manifest.json",
                input_manifest,
            )
            captured["input_manifest"] = input_manifest
            captured["snapshot_zip"] = snapshot_target
            original_zip_tree(source_dir, destination)

        canonical.collect_public_data = frozen_collect
        canonical.zip_tree = evidence_zip
        output_zip.parent.mkdir(parents=True, exist_ok=True)
        return_code = canonical.main(["--output-zip", str(output_zip)])
        canonical.collect_public_data = original_collect
        canonical.zip_tree = original_zip_tree
        if return_code != 0:
            raise RuntimeError(f"canonical Delta replay returned {return_code}")
        with zipfile.ZipFile(output_zip) as archive:
            bad = archive.testzip()
            if bad:
                raise RuntimeError(f"corrupt Delta replay output member: {bad}")
            manifest = json.loads(
                archive.read(
                    _single_member(archive, "outputs/delta_v11_run_manifest.json")
                ).decode("utf-8-sig")
            )
        _safe_manifest(manifest)
        result.update(manifest)
        result["technical_status"] = "PASS"
        result["output_zip"] = str(output_zip)
        result["output_zip_sha256"] = _sha256_path(output_zip)
        if captured.get("snapshot_zip"):
            result["input_snapshot_zip"] = str(captured["snapshot_zip"])
            result["input_snapshot_zip_sha256"] = _sha256_path(captured["snapshot_zip"])
    except Exception as exc:
        if canonical is not None:
            try:
                canonical.collect_public_data = original_collect
                canonical.zip_tree = original_zip_tree
            except Exception:
                pass
        result["technical_status"] = "FAIL"
        result["data_quality_status"] = "NOT_EVALUATED"
        result["errors"].append({
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
        })
    finally:
        _write_evidence(evidence_dir, stamp, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_package", type=Path)
    parser.add_argument("--source-data-dir", type=Path)
    parser.add_argument("--data-cutoff")
    parser.add_argument("--output-zip", type=Path, required=True)
    parser.add_argument("--input-snapshot-zip", type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    args = parser.parse_args()
    evidence_dir = args.evidence_dir or args.output_zip.parent
    result = replay(
        args.source_package,
        args.output_zip,
        args.data_cutoff,
        evidence_dir,
        args.source_data_dir,
        args.input_snapshot_zip,
    )
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 0 if result["technical_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
