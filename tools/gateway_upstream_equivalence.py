#!/usr/bin/env python3
"""End-to-end Gateway v0.10 public-data capture and same-input replay.

The canonical source is executed without methodology changes. Public HTTP
responses are captured once and replayed offline, fail closed, on Linux and
Windows. This closes the source-acquisition/feature-construction evidence gap
without relying on mutable public endpoints during the replay comparison.
"""
from __future__ import annotations

import argparse
import base64
import csv
import glob
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GW = ROOT / "migration/canonical/gateway"
SOURCE_PARTS = str(GW / "payload/gateway_v010_canonical_source.zip.b64.part-*")
SOURCE_SIZE = 19542
SOURCE_SHA256 = "d90c140b18792bffb147f62fdaf2b5245437637ef2f59f21bbdf68435df01d54"
SOURCE_ENTRYPOINT_SHA256 = "835e4ecb118c3ba2796c4e74c39a9025351b14415a2ddd1efb5465b82a724a20"
SITE_DIR = ROOT / "tools/gateway_capture_site"
CONTRACT = ROOT / "migration/gateway/gateway_output_contract_v010.json"
VOLATILE_JSON_KEYS = {
    "run_utc", "generated_utc", "generated_at", "created_at", "created_at_utc",
    "started_at", "started_at_utc", "finished_at", "finished_at_utc",
    "elapsed_seconds", "duration_seconds", "output_zip", "report_json",
    "evidence_zip", "working_directory", "stdout", "stderr",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(text, encoding="utf-8", newline="")
    os.replace(tmp, path)


def save_json(path: Path, payload: Any) -> None:
    save_text(path, json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n")


def decode_source(out_zip: Path) -> dict[str, Any]:
    parts = [Path(item) for item in sorted(glob.glob(SOURCE_PARTS))]
    if not parts:
        raise FileNotFoundError(f"no canonical source parts matched {SOURCE_PARTS}")
    encoded = "".join(part.read_text(encoding="ascii") for part in parts)
    data = base64.b64decode("".join(encoded.split()), validate=True)
    actual = {"size_bytes": len(data), "sha256": sha256_bytes(data)}
    expected = {"size_bytes": SOURCE_SIZE, "sha256": SOURCE_SHA256}
    if actual != expected:
        raise RuntimeError(f"canonical source archive mismatch: {actual} != {expected}")
    out_zip.write_bytes(data)
    with zipfile.ZipFile(out_zip) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"canonical source corrupt member: {bad}")
        names = archive.namelist()
        if any(Path(name).is_absolute() or ".." in Path(name).parts for name in names):
            raise RuntimeError("canonical source archive contains unsafe path")
    return {"status": "PASS", **actual, "parts": [p.relative_to(ROOT).as_posix() for p in parts]}


def safe_extract(source_zip: Path, destination: Path) -> None:
    with zipfile.ZipFile(source_zip) as archive:
        for info in archive.infolist():
            member = Path(info.filename)
            if member.is_absolute() or ".." in member.parts:
                raise RuntimeError(f"unsafe archive member: {info.filename}")
            target = destination / member
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))


def canonical_scalar(value: str, digits: int = 11) -> str:
    text = value.strip()
    if text == "":
        return ""
    lowered = text.lower()
    if lowered in {"nan", "na", "null", "none"}:
        return "<NA>"
    try:
        number = float(text)
    except ValueError:
        return text
    if number == 0.0:
        number = 0.0
    return format(number, f".{digits}g")


def semantic_csv(data: bytes) -> dict[str, Any]:
    text = data.decode("utf-8-sig", errors="strict")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return {"rows": 0, "columns": [], "sha256": sha256_bytes(b"")}
    columns = rows[0]
    body = []
    for raw in rows[1:]:
        padded = raw + [""] * max(0, len(columns) - len(raw))
        body.append(tuple(canonical_scalar(item) for item in padded[: len(columns)]))
    body.sort()
    digest = hashlib.sha256(("\x1f".join(columns) + "\n").encode("utf-8"))
    for row in body:
        digest.update(("\x1f".join(row) + "\n").encode("utf-8"))
    return {"rows": len(body), "columns": columns, "sha256": digest.hexdigest()}


def clean_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: clean_json(item)
            for key, item in sorted(value.items())
            if key.lower() not in VOLATILE_JSON_KEYS
        }
    if isinstance(value, list):
        return [clean_json(item) for item in value]
    if isinstance(value, float):
        return format(0.0 if value == 0.0 else value, ".11g")
    return value


def semantic_json(data: bytes) -> dict[str, Any]:
    parsed = json.loads(data.decode("utf-8-sig", errors="strict"))
    cleaned = clean_json(parsed)
    encoded = json.dumps(cleaned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {"sha256": sha256_bytes(encoded), "top_level_type": type(cleaned).__name__}


def zip_semantic(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {"zip_sha256": file_sha256(path), "csv": {}, "json": {}, "members": []}
    with zipfile.ZipFile(path) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"output ZIP corrupt member: {bad}")
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace("\\", "/")
            result["members"].append(name)
            data = archive.read(info)
            if name.lower().endswith(".csv"):
                result["csv"][name] = semantic_csv(data)
            elif name.lower().endswith(".json"):
                result["json"][name] = semantic_json(data)
    result["members"].sort()
    return result


def compare_semantic(reference: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    findings = []
    for kind in ("csv", "json"):
        ref_names = set(reference.get(kind, {}))
        cand_names = set(candidate.get(kind, {}))
        if ref_names != cand_names:
            findings.append({"kind": kind, "member_set": {"reference_only": sorted(ref_names - cand_names), "candidate_only": sorted(cand_names - ref_names)}})
        for name in sorted(ref_names & cand_names):
            if reference[kind][name] != candidate[kind][name]:
                findings.append({"kind": kind, "name": name, "reference": reference[kind][name], "candidate": candidate[kind][name]})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def find_member_by_basename(path: Path, basename: str) -> tuple[str, bytes]:
    matches = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith("/") and Path(name).name.lower() == basename.lower():
                matches.append((name, archive.read(name)))
    if len(matches) != 1:
        raise RuntimeError(f"expected one {basename} in {path.name}, found {len(matches)}")
    return matches[0]


def validate_gateway_output(path: Path) -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        for basename, required_fields in contract["required_files"].items():
            matches = [name for name in names if Path(name).name == basename]
            if len(matches) != 1:
                raise RuntimeError(f"contract member {basename} count={len(matches)}")
            data = archive.read(matches[0])
            if basename.endswith(".json"):
                present = json.loads(data.decode("utf-8-sig"))
            else:
                present = next(csv.reader(data.decode("utf-8-sig").splitlines()), [])
            missing = [field for field in required_fields if field not in present]
            if missing:
                raise RuntimeError(f"contract member {basename} missing {missing}")
    _, raw_manifest = find_member_by_basename(path, "v2a1_run_manifest.json")
    manifest = json.loads(raw_manifest.decode("utf-8-sig"))
    expected = {
        "version": "QOS_V2A1_GATEWAY_SCANNER_0.10",
        "technical_status": "PASS",
        "data_quality_status": "PASS",
        "snapshot_status": "SNAPSHOT_USABLE_RESEARCH_ONLY",
        "evidence_status": "SNAPSHOT_ONLY_NO_WALK_FORWARD_BACKTEST",
        "operational_status": "NOT_APPROVED",
        "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION",
        "errors": [],
        "selected_rows": 118,
        "execution_profile_rows": 8,
        "delta_stop_rule_rows": 80,
    }
    mismatches = {key: {"actual": manifest.get(key), "expected": value} for key, value in expected.items() if manifest.get(key) != value}
    if mismatches:
        raise RuntimeError(f"Gateway public output manifest mismatch: {mismatches}")
    return {"status": "PASS", "manifest": manifest, "output_zip": {"size_bytes": path.stat().st_size, "sha256": file_sha256(path)}}


def run_gateway(source_zip: Path, mode: str, cassette: Path, http_status: Path, output_zip: Path, logs: Path, timeout_seconds: int) -> dict[str, Any]:
    work = Path(tempfile.mkdtemp(prefix=f"gate_btc_gateway_{mode}_"))
    try:
        source = work / "source"
        safe_extract(source_zip, source)
        entrypoint = source / "scripts/00_run_all_v2a1.py"
        if file_sha256(entrypoint) != SOURCE_ENTRYPOINT_SHA256:
            raise RuntimeError("canonical Gateway entrypoint hash mismatch")
        env = os.environ.copy()
        env.update(
            {
                "GATE_BTC_RESEARCH_ONLY": "true",
                "GATE_BTC_HTTP_MODE": mode,
                "GATE_BTC_HTTP_CASSETTE": str(cassette.resolve()),
                "GATE_BTC_HTTP_STATUS": str(http_status.resolve()),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONPATH": str(SITE_DIR.resolve()) + os.pathsep + env.get("PYTHONPATH", ""),
            }
        )
        command = [sys.executable, str(entrypoint), "--output-zip", str(output_zip.resolve())]
        completed = subprocess.run(
            command,
            cwd=source,
            env=env,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        save_text(logs / f"gateway_{mode}_stdout.txt", completed.stdout)
        save_text(logs / f"gateway_{mode}_stderr.txt", completed.stderr)
        if completed.returncode != 0:
            raise RuntimeError(f"canonical Gateway {mode} returned {completed.returncode}")
        if not output_zip.is_file():
            raise RuntimeError(f"canonical Gateway {mode} did not create output ZIP")
        if not http_status.is_file():
            raise RuntimeError(f"canonical Gateway {mode} did not create HTTP status")
        status = json.loads(http_status.read_text(encoding="utf-8"))
        if status.get("status") != "PASS":
            raise RuntimeError(f"canonical Gateway {mode} HTTP status not PASS: {status}")
        validation = validate_gateway_output(output_zip)
        return {
            "status": "PASS",
            "returncode": completed.returncode,
            "http": status,
            "gateway": validation,
            "semantic": zip_semantic(output_zip),
        }
    finally:
        shutil.rmtree(work, ignore_errors=True)


def package_directory(directory: Path, target: Path) -> None:
    tmp = target.with_suffix(".partial.zip")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path not in {tmp, target}:
                archive.write(path, path.relative_to(directory).as_posix())
    with zipfile.ZipFile(tmp) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"evidence ZIP corrupt member: {bad}")
    os.replace(tmp, target)


def render(payload: dict[str, Any]) -> str:
    lines = [
        "GATE BTC - GATEWAY V0.10 UPSTREAM EQUIVALENCE",
        f"Generated UTC: {payload['generated_utc']}",
        f"STATUS={payload['status']}",
        f"MODE={payload['mode']}",
        f"STAGE_REACHED={payload['stage_reached']}",
        f"SOURCE_CANONICALITY={payload.get('source', {}).get('status', 'NOT_EVALUATED')}",
        f"PUBLIC_HTTP_CAPTURE={payload.get('capture', {}).get('status', 'NOT_EVALUATED')}",
        f"LINUX_OFFLINE_REPLAY={payload.get('linux_replay', {}).get('status', 'NOT_EVALUATED')}",
        f"WINDOWS_OFFLINE_REPLAY={payload.get('windows_replay', {}).get('status', 'NOT_EVALUATED')}",
        f"SEMANTIC_PARITY={payload.get('semantic_parity', {}).get('status', 'NOT_EVALUATED')}",
        f"PUBLIC_SOURCE_ACQUISITION_EQUIVALENCE={payload.get('public_source_acquisition_equivalence', 'NOT_EVALUATED')}",
        f"FEATURE_CONSTRUCTION_EQUIVALENCE={payload.get('feature_construction_equivalence', 'NOT_EVALUATED')}",
        "RESEARCH_ONLY=True",
        "ORDERS_GENERATED=0",
        "REAL_CAPITAL_USED=0",
        "OPERATIONAL_STATUS=NOT_APPROVED",
        "RETROSPECTIVE_GATEWAY_PERFORMANCE=PROHIBITED",
        "METHODOLOGY_CHANGES=0",
        "MERGE_AUTHORIZED=False",
        "CRON_ON_MAIN_ENABLED=False",
    ]
    capture = payload.get("capture", {})
    if capture:
        lines.append(f"HTTP_CAPTURE_COUNT={capture.get('http', {}).get('capture_count', 0)}")
    replay = payload.get("linux_replay") or payload.get("windows_replay") or {}
    if replay:
        lines.append(f"HTTP_REPLAY_TOTAL={replay.get('http', {}).get('replay_total', 0)}")
        lines.append(f"HTTP_REPLAY_CONSUMED={replay.get('http', {}).get('replay_consumed', 0)}")
        lines.append(f"HTTP_REPLAY_REMAINING={replay.get('http', {}).get('replay_remaining', 0)}")
    if payload.get("errors"):
        lines.extend(["", "ERRORS", json.dumps(payload["errors"], indent=2, ensure_ascii=False)])
    else:
        lines.extend(["", f"NEXT_ACTION={payload.get('next_action', 'NONE')}"])
    return "\n".join(lines) + "\n"


def capture_replay(args: argparse.Namespace) -> int:
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema": "gate-btc-gateway-upstream-equivalence-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "CAPTURE_REPLAY_LINUX",
        "status": "RUNNING",
        "stage_reached": "STARTED",
        "research_only": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "operational_status": "NOT_APPROVED",
        "methodology_changes": 0,
        "errors": [],
    }
    try:
        if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
            raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
        source_zip = out / "canonical_gateway_v010_source.zip"
        payload["source"] = decode_source(source_zip)
        cassette = out / "gateway_public_http_cassette.jsonl"
        capture_status = out / "gateway_public_http_capture_status.json"
        capture_output = out / "linux_public_capture_outputs.zip"
        payload["capture"] = run_gateway(source_zip, "capture", cassette, capture_status, capture_output, out, args.timeout_seconds)
        payload["stage_reached"] = "PUBLIC_HTTP_CAPTURE_AND_CANONICAL_RUN_PASS"
        if payload["capture"]["http"].get("capture_count", 0) <= 0:
            raise RuntimeError("public HTTP capture contained no transactions")
        save_json(out / "linux_public_capture_semantic.json", payload["capture"]["semantic"])
        replay_status = out / "gateway_public_http_linux_replay_status.json"
        replay_output = out / "linux_offline_replay_outputs.zip"
        payload["linux_replay"] = run_gateway(source_zip, "replay", cassette, replay_status, replay_output, out, args.timeout_seconds)
        payload["semantic_parity"] = compare_semantic(payload["capture"]["semantic"], payload["linux_replay"]["semantic"])
        if payload["semantic_parity"]["status"] != "PASS":
            raise RuntimeError(f"Linux capture/replay semantic mismatch: {payload['semantic_parity']['findings']}")
        payload["public_source_acquisition_equivalence"] = "PASS_PUBLIC_CAPTURE_WITH_COMPLETE_RESPONSE_CASSETTE"
        payload["feature_construction_equivalence"] = "PASS_LINUX_OFFLINE_SAME_INPUT_REPLAY"
        payload["stage_reached"] = "LINUX_PUBLIC_CAPTURE_AND_OFFLINE_REPLAY_PASS"
        payload["status"] = "PASS"
        payload["next_action"] = "WINDOWS_OFFLINE_REPLAY_USING_IDENTICAL_HTTP_CASSETTE"
    except Exception as exc:
        payload["status"] = "FAIL"
        payload["errors"].append({"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        payload["next_action"] = "FAIL_CLOSED_REVIEW_EVIDENCE"
    save_json(out / "GATE_BTC_GATEWAY_UPSTREAM_EQUIVALENCE.json", payload)
    save_text(out / "GATE_BTC_GATEWAY_UPSTREAM_EQUIVALENCE.txt", render(payload))
    package_directory(out, out / "GATE_BTC_GATEWAY_UPSTREAM_EQUIVALENCE_EVIDENCE.zip")
    print(render(payload), end="")
    return 0 if payload["status"] == "PASS" else 1


def replay_only(args: argparse.Namespace) -> int:
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema": "gate-btc-gateway-upstream-equivalence-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "REPLAY_ONLY_WINDOWS",
        "status": "RUNNING",
        "stage_reached": "STARTED",
        "research_only": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "operational_status": "NOT_APPROVED",
        "methodology_changes": 0,
        "errors": [],
    }
    try:
        if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
            raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
        source_zip = out / "canonical_gateway_v010_source.zip"
        payload["source"] = decode_source(source_zip)
        cassette = args.cassette.resolve()
        reference_semantic = json.loads(args.reference_semantic.read_text(encoding="utf-8"))
        replay_status = out / "gateway_public_http_windows_replay_status.json"
        replay_output = out / "windows_offline_replay_outputs.zip"
        payload["windows_replay"] = run_gateway(source_zip, "replay", cassette, replay_status, replay_output, out, args.timeout_seconds)
        payload["semantic_parity"] = compare_semantic(reference_semantic, payload["windows_replay"]["semantic"])
        if payload["semantic_parity"]["status"] != "PASS":
            raise RuntimeError(f"Windows replay semantic mismatch: {payload['semantic_parity']['findings']}")
        payload["public_source_acquisition_equivalence"] = "PASS_FROM_LINUX_CAPTURE_ARTIFACT"
        payload["feature_construction_equivalence"] = "PASS_WINDOWS_OFFLINE_SAME_INPUT_REPLAY"
        payload["stage_reached"] = "WINDOWS_OFFLINE_IDENTICAL_HTTP_REPLAY_PASS"
        payload["status"] = "PASS"
        payload["next_action"] = "COMBINE_WITH_LINUX_CAPTURE_AND_GATEWAY_DOWNSTREAM_EVIDENCE"
    except Exception as exc:
        payload["status"] = "FAIL"
        payload["errors"].append({"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})
        payload["next_action"] = "FAIL_CLOSED_REVIEW_EVIDENCE"
    save_json(out / "GATE_BTC_GATEWAY_WINDOWS_UPSTREAM_REPLAY.json", payload)
    save_text(out / "GATE_BTC_GATEWAY_WINDOWS_UPSTREAM_REPLAY.txt", render(payload))
    package_directory(out, out / "GATE_BTC_GATEWAY_WINDOWS_UPSTREAM_REPLAY_EVIDENCE.zip")
    print(render(payload), end="")
    return 0 if payload["status"] == "PASS" else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture-replay")
    capture.add_argument("--output-dir", type=Path, required=True)
    capture.add_argument("--timeout-seconds", type=int, default=1800)
    capture.set_defaults(func=capture_replay)
    replay = sub.add_parser("replay-only")
    replay.add_argument("--cassette", type=Path, required=True)
    replay.add_argument("--reference-semantic", type=Path, required=True)
    replay.add_argument("--output-dir", type=Path, required=True)
    replay.add_argument("--timeout-seconds", type=int, default=1800)
    replay.set_defaults(func=replay_only)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
