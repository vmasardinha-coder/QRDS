#!/usr/bin/env python3
"""Aggregate the daily research-only V2A, Delta and Gateway collection.

This script does not calculate portfolio methodology. It only validates and
packages evidence produced by the admitted canonical engines. It fails closed
on stale/mismatched closes, incomplete HTTP replay, unsafe status, orders,
capital, operational promotion or missing evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_payload_sha(payload: dict[str, Any], field: str) -> str:
    clean = dict(payload)
    clean.pop(field, None)
    raw = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    temporary.write_text(text, encoding="utf-8", newline="")
    os.replace(temporary, path)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str) + "\n")


def load_unique(directory: Path, pattern: str) -> tuple[Path, dict[str, Any]]:
    matches = sorted(directory.glob(pattern))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one {pattern} in {directory}; found {len(matches)}")
    return matches[0], json.loads(matches[0].read_text(encoding="utf-8-sig"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def file_record(path: Path, root: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(root).as_posix(),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def package(directory: Path, target: Path) -> None:
    temporary = target.with_suffix(".partial.zip")
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.rglob("*")):
            if path.is_file() and path not in {temporary, target}:
                archive.write(path, path.relative_to(directory).as_posix())
    with zipfile.ZipFile(temporary) as archive:
        bad = archive.testzip()
        if bad:
            raise RuntimeError(f"daily evidence ZIP corrupt member: {bad}")
    os.replace(temporary, target)


def render(payload: dict[str, Any]) -> str:
    lines = [
        "GATE BTC - DAILY RESEARCH COLLECTION",
        f"Generated UTC: {payload['generated_utc']}",
        f"STATUS={payload['status']}",
        f"STAGE_REACHED={payload['stage_reached']}",
        f"DATA_CUTOFF={payload['data_cutoff']}",
        f"V2A_STATUS={payload.get('components', {}).get('v2a', {}).get('status', 'NOT_EVALUATED')}",
        f"DELTA_STATUS={payload.get('components', {}).get('delta', {}).get('status', 'NOT_EVALUATED')}",
        f"GATEWAY_UPSTREAM_STATUS={payload.get('components', {}).get('gateway_upstream', {}).get('status', 'NOT_EVALUATED')}",
        f"GATEWAY_DOWNSTREAM_STATUS={payload.get('components', {}).get('gateway_downstream', {}).get('status', 'NOT_EVALUATED')}",
        f"GATEWAY_DATA_QUALITY={payload.get('components', {}).get('gateway_upstream', {}).get('data_quality_status', 'NOT_EVALUATED')}",
        f"GATEWAY_SNAPSHOT_STATUS={payload.get('components', {}).get('gateway_upstream', {}).get('snapshot_status', 'NOT_EVALUATED')}",
        f"HTTP_CAPTURE_COUNT={payload.get('components', {}).get('gateway_upstream', {}).get('http_capture_count', 0)}",
        f"HTTP_REPLAY_CONSUMED={payload.get('components', {}).get('gateway_upstream', {}).get('http_replay_consumed', 0)}",
        f"TOTAL_SYSTEM_EQUIVALENCE_BASELINE={payload.get('total_system_equivalence_baseline', 'NOT_EVALUATED')}",
        "RESEARCH_ONLY=True",
        "ORDERS_GENERATED=0",
        "REAL_CAPITAL_USED=0",
        "OPERATIONAL_STATUS=NOT_APPROVED",
        "RETROSPECTIVE_GATEWAY_PERFORMANCE=PROHIBITED",
        "METHODOLOGY_CHANGES=0",
    ]
    if payload.get("errors"):
        lines.extend(["", "ERRORS", json.dumps(payload["errors"], indent=2, ensure_ascii=False)])
    else:
        lines.extend([
            "",
            "REPORT_DELIVERY_INPUTS=READY",
            "EXPECTED_DAILY_SHADOW_REPORTS=3",
            "SHADOW_1=MASTER_ANALYTIC",
            "SHADOW_2=COMPARATIVOS_COMPLETOS",
            "SHADOW_3=PROFIT_PRESERVATION",
            "NEXT_ACTION=GENERATE_AND_DELIVER_THREE_RESEARCH_ONLY_SHADOW_REPORTS",
        ])
    return "\n".join(lines) + "\n"


def run(args: argparse.Namespace) -> int:
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "schema": "gate-btc-daily-research-collection-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "data_cutoff": args.data_cutoff,
        "status": "RUNNING",
        "stage_reached": "STARTED",
        "research_only": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "operational_status": "NOT_APPROVED",
        "retrospective_gateway_performance": "PROHIBITED",
        "methodology_changes": 0,
        "components": {},
        "report_delivery": {
            "expected_shadow_pdf_count": 3,
            "reports": [
                "MASTER_ANALYTIC",
                "COMPARATIVOS_COMPLETOS",
                "PROFIT_PRESERVATION",
            ],
        },
        "errors": [],
    }
    try:
        require(os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() in {"1", "true", "yes", "on"}, "GATE_BTC_RESEARCH_ONLY must remain true")
        for forbidden in ("EXCHANGE_API_SECRET", "EXCHANGE_PRIVATE_KEY", "TRADING_API_KEY"):
            require(not os.environ.get(forbidden), f"forbidden operational credential present: {forbidden}")

        qos_path, qos = load_unique(args.qos_dir.resolve(), "QOS_ORCHESTRATION_MANIFEST_*.json")
        gateway_path = args.gateway_dir.resolve() / "GATE_BTC_GATEWAY_UPSTREAM_EQUIVALENCE.json"
        downstream_path = args.gateway_reference_dir.resolve() / "GATE_BTC_GATEWAY_V010_REPLAY.json"
        lock_sidecar_path = args.qos_dir.resolve() / "lock_valuation_sidecar.json"
        require(gateway_path.is_file(), f"missing Gateway upstream evidence: {gateway_path}")
        require(downstream_path.is_file(), f"missing Gateway downstream evidence: {downstream_path}")
        require(lock_sidecar_path.is_file(), f"missing LOCK valuation sidecar: {lock_sidecar_path}")
        gateway = json.loads(gateway_path.read_text(encoding="utf-8-sig"))
        downstream = json.loads(downstream_path.read_text(encoding="utf-8-sig"))
        lock_sidecar = json.loads(lock_sidecar_path.read_text(encoding="utf-8-sig"))
        require(
            lock_sidecar.get("status") in {"PASS_EXACT_ACTIVE_HOLDING_CLOSES", "WAITING_NOT_YET_ELIGIBLE"},
            f"LOCK valuation sidecar status={lock_sidecar.get('status')}",
        )
        require(lock_sidecar.get("snapshot_id") == args.data_cutoff, "LOCK valuation sidecar cutoff mismatch")
        require(lock_sidecar.get("valuation_only") is True, "LOCK valuation sidecar is not valuation-only")
        require(lock_sidecar.get("engine_feed") is False, "LOCK valuation sidecar cannot feed V2A")
        require(lock_sidecar.get("selection_membership_changed") is False, "LOCK sidecar changed selection membership")
        require(lock_sidecar.get("sidecar_sha256") == canonical_payload_sha(lock_sidecar, "sidecar_sha256"), "LOCK valuation sidecar hash invalid")

        require(qos.get("status") in {"PASS", "PASS_WITH_GATEWAY_PENDING"}, f"QOS orchestration status={qos.get('status')}")
        require(not qos.get("errors"), f"QOS orchestration errors={qos.get('errors')}")
        require(qos.get("matched_component_close") is True, "V2A/Delta matched close is not true")
        require(qos.get("requested_data_cutoff") == args.data_cutoff, "QOS requested cutoff mismatch")
        engines = {item.get("name"): item for item in qos.get("engines", [])}
        require(engines.get("V2A", {}).get("status") == "PASS", "V2A daily engine is not PASS")
        require(engines.get("Delta", {}).get("status") == "PASS", "Delta daily engine is not PASS")
        require(engines["V2A"].get("manifest", {}).get("data_as_of") == args.data_cutoff, "V2A data_as_of mismatch")
        require(engines["Delta"].get("manifest", {}).get("data_as_of") == args.data_cutoff, "Delta data_as_of mismatch")
        locks = qos.get("locks", {})
        require(locks.get("research_only") is True, "QOS research-only lock missing")
        require(locks.get("orders_generated") == 0, "QOS generated orders")
        require(locks.get("real_capital_used") == 0, "QOS used real capital")
        require(locks.get("operational_status") == "NOT_APPROVED", "QOS operational status changed")

        require(gateway.get("status") == "PASS", f"Gateway upstream status={gateway.get('status')}")
        require(str(gateway.get("public_source_acquisition_equivalence", "")).startswith("PASS"), "Gateway public-source acquisition equivalence missing")
        require(str(gateway.get("feature_construction_equivalence", "")).startswith("PASS"), "Gateway feature-construction equivalence missing")
        capture = gateway.get("capture", {})
        replay = gateway.get("linux_replay", {})
        require(capture.get("status") == "PASS", "Gateway public capture is not PASS")
        require(replay.get("status") == "PASS", "Gateway Linux offline replay is not PASS")
        capture_http = capture.get("http", {})
        replay_http = replay.get("http", {})
        require(capture_http.get("capture_count", 0) > 0, "Gateway captured no public HTTP responses")
        require(replay_http.get("replay_total") == replay_http.get("replay_consumed"), "Gateway HTTP replay did not consume all responses")
        require(replay_http.get("replay_remaining") == 0, "Gateway HTTP replay has remaining responses")
        gateway_manifest = capture.get("gateway", {}).get("manifest", {})
        require(gateway_manifest.get("technical_status") == "PASS", "Gateway technical status is not PASS")
        require(gateway_manifest.get("operational_status") == "NOT_APPROVED", "Gateway operational status changed")
        require(gateway_manifest.get("retrospective_performance_status") == "PROHIBITED_CURRENT_COMPOSITION", "Gateway retrospective prohibition missing")
        require(gateway_manifest.get("errors") == [], "Gateway manifest contains errors")

        require(downstream.get("status") == "PASS", f"Gateway downstream status={downstream.get('status')}")
        require(downstream.get("source_canonicality", {}).get("status") == "PASS", "Gateway source canonicality is not PASS")
        require(downstream.get("reference_integrity", {}).get("status") == "PASS", "Gateway reference integrity is not PASS")
        require(downstream.get("frozen_replay", {}).get("status") == "PASS", "Gateway frozen downstream replay is not PASS")
        require(downstream.get("fixture_contract", {}).get("status") == "PASS", "Gateway fixture contract is not PASS")

        for evidence in (gateway, downstream):
            require(evidence.get("research_only") is True, "Gateway research-only lock missing")
            require(evidence.get("orders_generated") == 0, "Gateway generated orders")
            require(evidence.get("real_capital_used") == 0, "Gateway used real capital")
            require(evidence.get("operational_status") == "NOT_APPROVED", "Gateway operational status changed")
            require(evidence.get("methodology_changes") == 0, "Gateway methodology changed")

        payload["components"] = {
            "v2a": {
                "status": "PASS",
                "data_as_of": engines["V2A"]["manifest"].get("data_as_of"),
                "version": engines["V2A"]["manifest"].get("version"),
                "output_zip": engines["V2A"].get("output_zip"),
            },
            "delta": {
                "status": "PASS",
                "data_as_of": engines["Delta"]["manifest"].get("data_as_of"),
                "version": engines["Delta"]["manifest"].get("version"),
                "output_zip": engines["Delta"].get("output_zip"),
            },
            "gateway_upstream": {
                "status": "PASS",
                "data_as_of": gateway_manifest.get("data_as_of"),
                "version": gateway_manifest.get("version"),
                "data_quality_status": gateway_manifest.get("data_quality_status"),
                "snapshot_status": gateway_manifest.get("snapshot_status"),
                "http_capture_count": capture_http.get("capture_count"),
                "http_replay_consumed": replay_http.get("replay_consumed"),
                "public_source_acquisition_equivalence": gateway.get("public_source_acquisition_equivalence"),
                "feature_construction_equivalence": gateway.get("feature_construction_equivalence"),
            },
            "gateway_downstream": {
                "status": "PASS",
                "scope": downstream.get("replay_scope"),
                "files": downstream.get("frozen_replay", {}).get("files", {}),
            },
            "lock_valuation_sidecar": {
                "status": lock_sidecar["status"],
                "data_as_of": lock_sidecar["snapshot_id"],
                "required_assets": lock_sidecar.get("required_assets", []),
                "observation_count": lock_sidecar.get("observation_count", 0),
                "sidecar_sha256": lock_sidecar["sidecar_sha256"],
                "valuation_only": True,
                "engine_feed": False,
            },
        }
        warning_state = (
            gateway_manifest.get("data_quality_status") != "PASS"
            or gateway_manifest.get("snapshot_status") != "SNAPSHOT_USABLE_RESEARCH_ONLY"
        )
        payload["status"] = "PASS_WITH_DATA_WARNINGS" if warning_state else "PASS"
        payload["stage_reached"] = "DAILY_V2A_DELTA_GATEWAY_COLLECTION_VALIDATED"
        payload["total_system_equivalence_baseline"] = "PASS"
        payload["report_delivery"]["inputs_ready"] = True
        payload["source_evidence"] = {
            "qos_manifest": file_record(qos_path, args.qos_dir.resolve()),
            "gateway_upstream": file_record(gateway_path, args.gateway_dir.resolve()),
            "gateway_downstream": file_record(downstream_path, args.gateway_reference_dir.resolve()),
            "lock_valuation_sidecar": file_record(lock_sidecar_path, args.qos_dir.resolve()),
        }
    except Exception as exc:
        payload["status"] = "FAIL"
        payload["stage_reached"] = payload.get("stage_reached", "STARTED")
        payload["total_system_equivalence_baseline"] = "NOT_REVOKED_BUT_DAILY_RUN_FAILED_CLOSED"
        payload["report_delivery"]["inputs_ready"] = False
        payload["errors"].append({"type": type(exc).__name__, "message": str(exc), "traceback": traceback.format_exc()})

    manifest_path = output / "GATE_BTC_DAILY_RESEARCH_MANIFEST.json"
    report_path = output / "GATE_BTC_DAILY_RESEARCH_REPORT.txt"
    atomic_json(manifest_path, payload)
    atomic_text(report_path, render(payload))
    package(output, output / "GATE_BTC_DAILY_RESEARCH_EVIDENCE.zip")
    print(render(payload), end="")
    return 0 if payload["status"] in {"PASS", "PASS_WITH_DATA_WARNINGS"} else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qos-dir", type=Path, required=True)
    parser.add_argument("--gateway-dir", type=Path, required=True)
    parser.add_argument("--gateway-reference-dir", type=Path, required=True)
    parser.add_argument("--data-cutoff", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
