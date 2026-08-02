#!/usr/bin/env python3
"""Fail-closed Gateway v0.10 admission and frozen downstream replay.

The replay starts from the admitted 2026-08-02 feature snapshot. Public-data
acquisition and feature construction are not reconstructed because the user
reference did not contain a complete raw-history input snapshot.
"""
from __future__ import annotations

import argparse, base64, csv, glob, hashlib, importlib.util, json, os, shutil
import subprocess, sys, tempfile, traceback, zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GW = ROOT / "migration/canonical/gateway"
SOURCE = GW / "gateway_v010_canonical_source.zip.b64"
PARTS = str(GW / "reference/payload/gateway_reference_minimal_2026-08-02.zip.b64.part-*")
MANIFEST = GW / "reference/gateway_reference_manifest_2026-08-02.json"
CONTRACT = ROOT / "migration/gateway/gateway_output_contract_v010.json"
SORT = {
    "all_strategy_selections.csv": ["strategy", "base", "side", "execution_layer"],
    "strategy_compositions.csv": ["strategy", "asset", "role"],
    "strategy_execution_profiles.csv": ["strategy"],
    "delta_stop_trade_rules.csv": ["strategy", "asset", "side"],
    "gateway_decision_log.csv": ["base"],
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha(path: Path) -> str:
    return sha(path.read_bytes())


def save(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def safe_zip(data: bytes, path: Path, expected: dict, label: str) -> dict:
    size, digest = len(data), sha(data)
    if size != int(expected["decoded_archive_size_bytes"]):
        raise RuntimeError(f"{label} decoded size mismatch: {size}")
    if digest != expected["decoded_archive_sha256"]:
        raise RuntimeError(f"{label} decoded SHA-256 mismatch: {digest}")
    path.write_bytes(data)
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        if bad:
            raise RuntimeError(f"{label} corrupt member: {bad}")
        names = z.namelist()
        if any(Path(n).is_absolute() or ".." in Path(n).parts for n in names):
            raise RuntimeError(f"{label} unsafe member")
    return {"status": "PASS", "bytes": size, "sha256": digest, "entries": len(names)}


def decode_single(path: Path, out: Path, expected: dict) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    data = base64.b64decode("".join(path.read_text(encoding="ascii").split()), validate=True)
    result = safe_zip(data, out, expected, path.name)
    result["encoded_file"] = path.relative_to(ROOT).as_posix()
    return result


def decode_parts(pattern: str, out: Path, expected: dict) -> dict:
    parts = [Path(p) for p in sorted(glob.glob(pattern))]
    if not parts:
        raise FileNotFoundError(f"no payload parts matched {pattern}")
    encoded = "".join(p.read_text(encoding="ascii") for p in parts)
    data = base64.b64decode("".join(encoded.split()), validate=True)
    result = safe_zip(data, out, expected, "reference parts")
    result["encoded_parts"] = [p.relative_to(ROOT).as_posix() for p in parts]
    return result


def extract(path: Path, dest: Path) -> None:
    with zipfile.ZipFile(path) as z:
        for i in z.infolist():
            p = Path(i.filename)
            if p.is_absolute() or ".." in p.parts:
                raise RuntimeError(f"unsafe member {i.filename}")
            target = dest / p
            if i.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(i))


def verify(root: Path, expected: dict, label: str) -> dict:
    result = {}
    for name, spec in expected.items():
        path = root / name
        actual = {"size_bytes": path.stat().st_size, "sha256": file_sha(path)} if path.is_file() else None
        if actual != spec:
            raise RuntimeError(f"{label} mismatch for {name}: {actual} != {spec}")
        result[name] = actual
    return result


def load_gateway(script: Path):
    spec = importlib.util.spec_from_file_location("gate_btc_gateway_v010", script)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load canonical Gateway")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def scalar(value: Any, digits: int) -> str:
    if pd.isna(value):
        return "<NA>"
    if isinstance(value, (bool, np.bool_)):
        return "true" if bool(value) else "false"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        value = 0.0 if float(value) == 0.0 else float(value)
        return format(value, f".{digits}g")
    return str(value)


def semantic(frame: pd.DataFrame, keys: list[str], digits: int) -> dict:
    frame = frame.copy()
    columns = list(frame.columns)
    keys = [k for k in keys if k in frame.columns]
    for key in keys:
        frame[key] = frame[key].fillna("").astype(str)
    if keys:
        frame = frame.sort_values(keys, kind="stable")
    digest = hashlib.sha256(("\x1f".join(columns) + "\n").encode())
    for row in frame.reset_index(drop=True).itertuples(index=False, name=None):
        digest.update(("\x1f".join(scalar(v, digits) for v in row) + "\n").encode())
    return {"rows": len(frame), "columns": columns, "sha256": digest.hexdigest()}


def replay(module, ref: Path, spec: dict, out: Path) -> dict:
    features = pd.read_csv(ref / spec["input_file"])
    selections, compositions = module.build_compositions(features)
    profiles, stops = module.build_execution_reality_layer(selections, compositions, features)
    module.OUT = out / "decision_log_work"
    module.OUT.mkdir(parents=True, exist_ok=True)
    decisions = module.decision_log(features, selections)
    frames = {
        "all_strategy_selections.csv": selections,
        "strategy_compositions.csv": compositions,
        "strategy_execution_profiles.csv": profiles,
        "delta_stop_trade_rules.csv": stops,
        "gateway_decision_log.csv": decisions,
    }
    if set(frames) != set(spec["files"]):
        raise RuntimeError("replay file set mismatch")
    outputs, results, digits = out / "replay_outputs", {}, int(spec["float_significant_digits"])
    outputs.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        actual = semantic(frame, SORT[name], digits)
        expected = spec["files"][name]
        if actual != expected:
            raise RuntimeError(f"{name} semantic mismatch: {actual} != {expected}")
        csv_path = outputs / name
        frame.to_csv(csv_path, index=False, lineterminator="\n")
        results[name] = {"status": "PASS", **actual, "output_sha256": file_sha(csv_path)}
    return {"status": "PASS", "scope": spec["scope"], "input_rows": len(features), "files": results}


def fixture(source: Path, out: Path, contract_path: Path) -> dict:
    output = out / "gateway_fixture_outputs_v010.zip"
    env = os.environ.copy(); env["GATE_BTC_RESEARCH_ONLY"] = "true"; env["PYTHONDONTWRITEBYTECODE"] = "1"
    run = subprocess.run(
        [sys.executable, str(source / "scripts/00_run_all_v2a1.py"), "--fixture-mode", "--output-zip", str(output)],
        cwd=source, text=True, capture_output=True, encoding="utf-8", errors="replace", env=env, timeout=180,
    )
    save(out / "gateway_fixture_stdout.txt", run.stdout); save(out / "gateway_fixture_stderr.txt", run.stderr)
    if run.returncode:
        raise RuntimeError(f"Gateway fixture failed: {run.returncode}")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    with zipfile.ZipFile(output) as z:
        if z.testzip():
            raise RuntimeError("fixture ZIP corrupt")
        for name, fields in contract["required_files"].items():
            raw = z.read(f"outputs/{name}")
            present = json.loads(raw) if name.endswith(".json") else next(csv.reader(raw.decode("utf-8-sig").splitlines()), [])
            missing = [field for field in fields if field not in present]
            if missing:
                raise RuntimeError(f"fixture {name} missing {missing}")
        manifest = json.loads(z.read("outputs/v2a1_run_manifest.json"))
    expected = {
        "version": "QOS_V2A1_GATEWAY_SCANNER_0.10", "technical_status": "PASS",
        "data_quality_status": "PASS", "snapshot_status": "SNAPSHOT_USABLE_RESEARCH_ONLY",
        "evidence_status": "SNAPSHOT_ONLY_NO_WALK_FORWARD_BACKTEST", "operational_status": "NOT_APPROVED",
        "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION", "errors": [],
        "selected_rows": 118, "execution_profile_rows": 8, "delta_stop_rule_rows": 80,
        "mode": "offline_fixture_no_network",
    }
    wrong = {k: (manifest.get(k), v) for k, v in expected.items() if manifest.get(k) != v}
    if wrong:
        raise RuntimeError(f"fixture manifest mismatch: {wrong}")
    return {"status": "PASS", "output_zip": {"bytes": output.stat().st_size, "sha256": file_sha(output)}}


def report(payload: dict) -> str:
    lines = [
        "GATE BTC - CANONICAL GATEWAY V0.10 ADMISSION AND FROZEN REPLAY",
        f"Generated UTC: {payload['generated_utc']}", f"STATUS={payload['status']}",
        f"STAGE_REACHED={payload['stage_reached']}",
        f"SOURCE_ARCHIVE_SHA256={payload.get('source_archive', {}).get('sha256', 'N/A')}",
        f"REFERENCE_ARCHIVE_SHA256={payload.get('reference_archive', {}).get('sha256', 'N/A')}",
        f"SOURCE_CANONICALITY={payload.get('source_canonicality', {}).get('status', 'NOT_EVALUATED')}",
        f"REFERENCE_INTEGRITY={payload.get('reference_integrity', {}).get('status', 'NOT_EVALUATED')}",
        f"FROZEN_REPLAY={payload.get('frozen_replay', {}).get('status', 'NOT_EVALUATED')}",
        f"FIXTURE_CONTRACT={payload.get('fixture_contract', {}).get('status', 'SKIPPED')}",
        f"REPLAY_SCOPE={payload.get('replay_scope', 'NOT_EVALUATED')}",
        "RESEARCH_ONLY=True", "ORDERS_GENERATED=0", "REAL_CAPITAL_USED=0",
        "OPERATIONAL_STATUS=NOT_APPROVED", "RETROSPECTIVE_GATEWAY_PERFORMANCE=PROHIBITED",
        "PUBLIC_SOURCE_ACQUISITION_RECONSTRUCTED=False", "FEATURE_CONSTRUCTION_RECONSTRUCTED=False",
        "METHODOLOGY_CHANGES=0", "MERGE_AUTHORIZED=False", "CRON_ON_MAIN_ENABLED=False",
    ]
    if payload["errors"]:
        lines += ["", "ERRORS", json.dumps(payload["errors"], indent=2, ensure_ascii=False)]
    else:
        lines += ["", "REPLAY_RESULTS"] + [
            f"{name}={item['status']} rows={item['rows']} semantic_sha256={item['sha256']}"
            for name, item in payload["frozen_replay"]["files"].items()
        ] + ["", "NEXT_ACTION=REMOTE_CHECKS_PASS_THEN_UPSTREAM_EQUIVALENCE_BOUNDARY_REVIEW"]
    return "\n".join(lines) + "\n"


def package(out: Path, target: Path) -> None:
    tmp = target.with_suffix(".partial.zip")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path not in {tmp, target}:
                z.write(path, path.relative_to(out).as_posix())
    with zipfile.ZipFile(tmp) as z:
        if z.testzip():
            raise RuntimeError("evidence ZIP corrupt")
    os.replace(tmp, target)


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--source-b64", type=Path, default=SOURCE)
    p.add_argument("--reference-parts-glob", default=PARTS)
    p.add_argument("--manifest", type=Path, default=MANIFEST)
    p.add_argument("--contract", type=Path, default=CONTRACT)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--skip-fixture", action="store_true")
    a = p.parse_args(argv); a.output_dir = a.output_dir.resolve(); a.output_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "gate-btc-gateway-v010-replay-evidence-v2", "generated_utc": datetime.now(timezone.utc).isoformat(),
        "status": "RUNNING", "stage_reached": "STARTED", "research_only": True,
        "orders_generated": 0, "real_capital_used": 0, "operational_status": "NOT_APPROVED",
        "retrospective_gateway_performance": "PROHIBITED", "public_source_acquisition_reconstructed": False,
        "feature_construction_reconstructed": False, "methodology_changes": 0, "errors": [],
    }
    work = Path(tempfile.mkdtemp(prefix="gate_btc_gateway_replay_"))
    try:
        if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
            raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
        manifest = json.loads(a.manifest.read_text(encoding="utf-8"))
        if manifest.get("admission_status") != "PASS":
            raise RuntimeError("Gateway admission manifest is not PASS")
        source_zip, ref_zip = work / "source.zip", work / "reference.zip"
        payload["source_archive"] = decode_single(a.source_b64, source_zip, manifest["repository_payload"])
        payload["reference_archive"] = decode_parts(a.reference_parts_glob, ref_zip, manifest["reference_run"]["repository_payload"])
        source, ref = work / "source", work / "reference"; extract(source_zip, source); extract(ref_zip, ref)
        payload["source_canonicality"] = {"status": "PASS", "files": verify(source, manifest["canonical_files"], "source")}
        payload["stage_reached"] = "SOURCE_ADMITTED_CANONICALITY_CONFIRMED"
        payload["reference_integrity"] = {"status": "PASS", "files": verify(ref, manifest["reference_run"]["reference_files"], "reference")}
        module = load_gateway(source / "scripts/00_run_all_v2a1.py")
        if module.VERSION != "QOS_V2A1_GATEWAY_SCANNER_0.10":
            raise RuntimeError(f"unexpected Gateway version {module.VERSION}")
        payload["frozen_replay"] = replay(module, ref, manifest["reference_run"]["semantic_replay"], a.output_dir)
        payload["replay_scope"] = payload["frozen_replay"]["scope"]
        payload["stage_reached"] = "FROZEN_DOWNSTREAM_REFERENCE_REPLAY_PASS"
        payload["fixture_contract"] = {"status": "SKIPPED"} if a.skip_fixture else fixture(source, a.output_dir, a.contract)
        if not a.skip_fixture:
            payload["stage_reached"] = "CANONICAL_FIXTURE_AND_FROZEN_DOWNSTREAM_REPLAY_PASS"
        payload["status"] = "PASS"
    except Exception as exc:
        payload["status"] = "FAIL"
        payload["errors"].append({"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
    finally:
        shutil.rmtree(work, ignore_errors=True)
    text = report(payload)
    save(a.output_dir / "GATE_BTC_GATEWAY_V010_REPLAY.json", json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n")
    save(a.output_dir / "GATE_BTC_GATEWAY_V010_REPLAY.txt", text)
    package(a.output_dir, a.output_dir / "GATE_BTC_GATEWAY_V010_REPLAY_EVIDENCE.zip")
    print(text, end="")
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
