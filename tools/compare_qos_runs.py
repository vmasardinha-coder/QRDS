#!/usr/bin/env python3
"""Compare a trusted local QOS close with a GitHub migration run.

The comparison is deliberately fail-closed.  Offline fixtures can prove the
artifact/safety contract, but can never be promoted to value equivalence with
a public-data close.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path


SAFETY_EXPECTED = {
    "operational_status": "NOT_APPROVED",
    "real_orders": 0,
    "capital_used": 0,
}


def _mode_class(mode: object) -> str | None:
    value = str(mode or "").lower()
    if "fixture" in value:
        return "fixture"
    if "public" in value and "no" in value and "order" in value:
        return "public_research_only"
    return None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json_member(archive: zipfile.ZipFile, suffix: str) -> dict | None:
    matches = [name for name in archive.namelist() if name.endswith(suffix)]
    if len(matches) != 1:
        return None
    return json.loads(archive.read(matches[0]).decode("utf-8-sig"))


def _load_run(package: Path) -> dict:
    with zipfile.ZipFile(package) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"corrupt ZIP member: {bad}")
        local = _read_json_member(archive, "RUN_STATUS.json")
        remote = _read_json_member(archive, "QOS_ORCHESTRATION_MANIFEST.json")
        if remote is None:
            candidates = [name for name in archive.namelist()
                          if "QOS_ORCHESTRATION_MANIFEST_" in name and name.endswith(".json")]
            if len(candidates) == 1:
                remote = json.loads(archive.read(candidates[0]).decode("utf-8-sig"))
    payload = local or remote
    if payload is None:
        raise ValueError("package has neither RUN_STATUS nor QOS orchestration manifest")
    payload = dict(payload)
    payload["_package_sha256"] = _sha256(package)
    payload["_kind"] = "local_full_qos" if local else "remote_orchestration"
    return payload


def _safety_errors(payload: dict) -> list[str]:
    locks = payload.get("locks", {})
    values = {
        "operational_status": payload.get("operational_status", locks.get("operational_status")),
        "real_orders": payload.get("real_orders", locks.get("orders_generated")),
        "capital_used": payload.get("capital_used", locks.get("real_capital_used")),
    }
    return [f"{key}={values[key]!r}, expected {expected!r}"
            for key, expected in SAFETY_EXPECTED.items() if values[key] != expected]


def compare(local_package: Path, remote_package: Path) -> dict:
    local = _load_run(local_package)
    remote = _load_run(remote_package)
    errors = [f"local safety: {item}" for item in _safety_errors(local)]
    errors += [f"remote safety: {item}" for item in _safety_errors(remote)]
    local_mode = local.get("mode")
    remote_mode = remote.get("mode")
    remote_engines = {item.get("name"): item.get("status") for item in remote.get("engines", [])}
    structural_errors = list(errors)
    if remote.get("status") not in {"PASS", "PASS_WITH_GATEWAY_PENDING"}:
        structural_errors.append(f"remote status={remote.get('status')!r}")
    if remote_engines and remote_engines != {"V2A": "PASS", "Delta": "PASS"}:
        structural_errors.append(f"remote engines={remote_engines!r}")

    matched_mode = _mode_class(local_mode) == _mode_class(remote_mode) == "public_research_only"
    local_as_of = local.get("component_status", {}).get("delta", {}).get("data_as_of")
    remote_as_of = remote.get("component_data_as_of", {}).get("delta") or remote.get("data_as_of")
    matched_close = bool(local_as_of and remote_as_of and local_as_of == remote_as_of)
    gateway_executed = remote.get("gateway", {}).get("state") == "EXECUTED_REMOTE"
    value_ready = matched_mode and matched_close and gateway_executed

    if structural_errors:
        status = "ERROR"
    elif value_ready:
        # Exact metric comparison is intentionally a separate gate.  Reaching
        # this state without a metric manifest must not silently claim parity.
        status = "VALUE_PARITY_INPUT_READY"
    else:
        status = "STRUCTURAL_PASS_VALUE_PARITY_PENDING"
    return {
        "schema": "qos-local-remote-parity-v1",
        "status": status,
        "equivalence_claim": False,
        "structural_contract_pass": not structural_errors,
        "value_parity_ready": value_ready,
        "local": {"kind": local["_kind"], "sha256": local["_package_sha256"],
                  "mode": local_mode, "data_as_of": local_as_of},
        "remote": {"kind": remote["_kind"], "sha256": remote["_package_sha256"],
                   "mode": remote_mode, "data_as_of": remote_as_of,
                   "gateway_state": remote.get("gateway", {}).get("state")},
        "checks": {
            "safety": "PASS" if not errors else "ERROR",
            "remote_engines": remote_engines,
            "matched_mode": matched_mode,
            "matched_close": matched_close,
            "gateway_executed_remote": gateway_executed,
        },
        "errors": structural_errors,
        "next_action": "RUN_PUBLIC_DATA_ON_MATCHED_CLOSE_WITH_GATEWAY_SOURCE",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("local_package", type=Path)
    parser.add_argument("remote_package", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compare(args.local_package, args.remote_package)
    except Exception as exc:
        result = {"schema": "qos-local-remote-parity-v1", "status": "ERROR",
                  "equivalence_claim": False, "errors": [str(exc)]}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["status"] == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
