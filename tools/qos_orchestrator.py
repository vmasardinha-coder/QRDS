#!/usr/bin/env python3
"""Research-only QOS orchestration for the GitHub migration.

Runs the canonical V2A and Delta engines, validates their evidence, and records
Gateway as a separately validated reference until its canonical scanner source
is recovered. This module never places orders or uses private credentials.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import traceback
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCKS = {
    "research_only": True,
    "orders_allowed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
    "promotion_allowed": False,
    "operational_status": "NOT_APPROVED",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _run_engine(
    name: str,
    command: list[str],
    output_zip: Path,
    manifest_suffix: str | None = None,
) -> dict:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
    record = {
        "name": name,
        "state": "EXECUTED_REMOTE",
        "return_code": result.returncode,
        "output_zip": output_zip.name,
        "stdout_tail": result.stdout[-4000:],
        "stderr_tail": result.stderr[-4000:],
    }
    if result.returncode != 0:
        record["status"] = "ERROR"
        return record
    if not output_zip.is_file():
        record.update(status="ERROR", error="missing output ZIP")
        return record
    try:
        with zipfile.ZipFile(output_zip) as archive:
            bad = archive.testzip()
            members = archive.namelist()
            suffix = manifest_suffix or (
                "v2a_run_manifest.json" if name == "V2A" else "delta_v11_run_manifest.json"
            )
            manifest_members = [member for member in members if member.endswith(suffix)]
            engine_manifest = (
                json.loads(archive.read(manifest_members[0]).decode("utf-8-sig"))
                if len(manifest_members) == 1 else None
            )
        if bad:
            record.update(status="ERROR", error=f"corrupt ZIP member: {bad}")
        elif engine_manifest is None:
            record.update(status="ERROR", error=f"missing or ambiguous {suffix}")
        else:
            record.update(status="PASS", sha256=_sha256(output_zip), members=len(members))
            record["manifest"] = {
                key: engine_manifest.get(key)
                for key in (
                    "version", "wrapper_version", "mode", "technical_status",
                    "data_quality_status", "data_as_of", "input_snapshot_id",
                )
            }
    except zipfile.BadZipFile as exc:
        record.update(status="ERROR", error=str(exc))
    return record


def run(
    output_dir: Path,
    fixture_mode: bool = True,
    gateway_reference: Path | None = None,
    data_cutoff: str | None = None,
) -> tuple[dict, Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%d_%H%M%S")
    txt_path = output_dir / f"QOS_ORCHESTRATION_REPORT_{stamp}.txt"
    json_path = output_dir / f"QOS_ORCHESTRATION_MANIFEST_{stamp}.json"
    zip_path = output_dir / f"QOS_ORCHESTRATION_EVIDENCE_{stamp}.zip"
    v2a_zip = output_dir / "qos_v2a_outputs.zip"
    delta_zip = output_dir / "delta_walk_forward_outputs.zip"
    public_collection_zip = output_dir / "qos_v2a_public_collection.zip"
    delta_collection_zip = output_dir / "delta_public_collection_outputs.zip"
    delta_input_snapshot_zip = output_dir / "delta_public_input_snapshot.zip"
    errors: list[str] = []
    engines: list[dict] = []
    input_collections: list[dict] = []
    gateway = {"name": "Gateway v0.10", "state": "PENDING_SOURCE", "status": "PENDING"}

    try:
        if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").lower() != "true":
            raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
        for forbidden in ("EXCHANGE_API_SECRET", "EXCHANGE_PRIVATE_KEY", "TRADING_API_KEY"):
            if os.environ.get(forbidden):
                raise RuntimeError(f"forbidden operational credential present: {forbidden}")

        if fixture_mode:
            engines.append(_run_engine(
                "V2A",
                [sys.executable, "migration/canonical/v2a/scripts/00_run_all_v2a.py",
                 "--fixture-mode", "--output-zip", str(v2a_zip)],
                v2a_zip,
            ))
        elif data_cutoff:
            collection = _run_engine(
                "V2A public collection",
                [sys.executable, "migration/canonical/v2a/scripts/00_run_all_v2a.py",
                 "--output-zip", str(public_collection_zip)],
                public_collection_zip,
                "v2a_run_manifest.json",
            )
            input_collections.append(collection)
            if collection["status"] == "PASS":
                engines.append(_run_engine(
                    "V2A",
                    [sys.executable, "tools/v2a_frozen_replay.py", str(public_collection_zip),
                     "--data-cutoff", data_cutoff,
                     "--output-zip", str(v2a_zip),
                     "--evidence-dir", str(output_dir / "v2a_frozen_replay_evidence")],
                    v2a_zip,
                    "v2a_run_manifest.json",
                ))
            else:
                engines.append({
                    "name": "V2A",
                    "state": "BLOCKED_BY_PUBLIC_COLLECTION",
                    "status": "ERROR",
                    "return_code": collection.get("return_code"),
                    "error": "public V2A collection failed before frozen replay",
                })
        else:
            engines.append(_run_engine(
                "V2A",
                [sys.executable, "migration/canonical/v2a/scripts/00_run_all_v2a.py",
                 "--output-zip", str(v2a_zip)],
                v2a_zip,
            ))

        if fixture_mode:
            engines.append(_run_engine(
                "Delta",
                [sys.executable, "migration/canonical/delta/scripts/00_run_delta_v11.py",
                 "--fixture-mode", "--output-zip", str(delta_zip)],
                delta_zip,
            ))
        elif data_cutoff:
            delta_collection = _run_engine(
                "Delta public collection",
                [sys.executable, "migration/canonical/delta/scripts/00_run_delta_v11.py",
                 "--output-zip", str(delta_collection_zip)],
                delta_collection_zip,
                "delta_v11_run_manifest.json",
            )
            input_collections.append(delta_collection)
            if delta_collection["status"] == "PASS":
                engines.append(_run_engine(
                    "Delta",
                    [sys.executable, "tools/delta_frozen_replay.py", str(delta_collection_zip),
                     "--source-data-dir", "migration/canonical/delta/data",
                     "--data-cutoff", data_cutoff,
                     "--output-zip", str(delta_zip),
                     "--input-snapshot-zip", str(delta_input_snapshot_zip),
                     "--evidence-dir", str(output_dir / "delta_frozen_replay_evidence")],
                    delta_zip,
                    "delta_v11_run_manifest.json",
                ))
            else:
                engines.append({
                    "name": "Delta",
                    "state": "BLOCKED_BY_PUBLIC_COLLECTION",
                    "status": "ERROR",
                    "return_code": delta_collection.get("return_code"),
                    "error": "public Delta collection failed before frozen replay",
                })
        else:
            engines.append(_run_engine(
                "Delta",
                [sys.executable, "migration/canonical/delta/scripts/00_run_delta_v11.py",
                 "--output-zip", str(delta_zip)],
                delta_zip,
            ))

        if gateway_reference is not None:
            validator = ROOT / "tools" / "validate_gateway_output_contract.py"
            result = subprocess.run(
                [sys.executable, str(validator), str(gateway_reference)],
                cwd=ROOT, text=True, capture_output=True, check=False,
            )
            gateway = {
                "name": "Gateway v0.10",
                "state": "VALIDATED_REFERENCE",
                "status": "PASS" if result.returncode == 0 else "ERROR",
                "validator_output": result.stdout[-4000:] or result.stderr[-4000:],
            }
        errors.extend(
            f"{item['name']}: {item.get('error', item.get('stderr_tail', 'failed'))}"
            for item in [*input_collections, *engines]
            if item["status"] != "PASS"
        )
        if gateway["status"] == "ERROR":
            errors.append("Gateway reference failed the canonical output contract")
    except Exception:
        errors.append(traceback.format_exc())

    status = "ERROR" if errors else (
        "PASS_WITH_GATEWAY_PENDING" if gateway["status"] == "PENDING" else "PASS"
    )
    component_data_as_of = {
        item["name"].lower(): item.get("manifest", {}).get("data_as_of")
        for item in engines
    }
    matched_component_close = len({value for value in component_data_as_of.values() if value}) == 1
    if not fixture_mode and data_cutoff:
        close_mismatches = {
            name: value for name, value in component_data_as_of.items()
            if value != data_cutoff
        }
        if close_mismatches:
            errors.append(f"matched-close requirement failed: {close_mismatches}")
            status = "ERROR"
    manifest = {
        "schema": "qos-orchestration-migration-v1",
        "status": status,
        "stage_reached": "CANONICAL_V2A_DELTA_ORCHESTRATED_GATEWAY_CONTRACT_BOUNDARY",
        "started_at_utc": started.isoformat(),
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "offline_fixture_no_network" if fixture_mode else "public_data_no_private_api_no_orders",
        "requested_data_cutoff": data_cutoff,
        "data_as_of": component_data_as_of.get("delta"),
        "component_data_as_of": component_data_as_of,
        "matched_component_close": matched_component_close,
        "input_collections": input_collections,
        "engines": engines,
        "gateway": gateway,
        "locks": LOCKS,
        "errors": errors,
        "equivalence_claim": False,
        "next_action": "RECOVER_GATEWAY_SOURCE_AND_RUN_LOCAL_SAME_INPUT_V2A_PARITY",
    }
    json_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "GATE BTC — QOS ORCHESTRATION MIGRATION REPORT",
        f"STATUS={status}",
        f"STAGE_REACHED={manifest['stage_reached']}",
        f"REQUESTED_DATA_CUTOFF={data_cutoff or 'NONE'}",
        f"DATA_AS_OF={manifest['data_as_of']}",
        f"MATCHED_COMPONENT_CLOSE={matched_component_close}",
        "RESEARCH_ONLY=True",
        "ORDERS_GENERATED=0",
        "REAL_CAPITAL_USED=0",
        "OPERATIONAL_STATUS=NOT_APPROVED",
        "EQUIVALENCE_CLAIM=False",
        f"GATEWAY_STATE={gateway['state']}",
        f"NEXT_ACTION={manifest['next_action']}",
        "",
        "INPUT_COLLECTIONS:",
        *([f"{item['name']}={item['status']}" for item in input_collections] or ["NONE"]),
        "",
        "ENGINES:",
        *[f"{item['name']}={item['status']} STATE={item['state']}" for item in engines],
        "",
        "ERRORS:",
        *(errors or ["NONE"]),
    ]
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in (
            txt_path, json_path, public_collection_zip, v2a_zip,
            delta_collection_zip, delta_input_snapshot_zip, delta_zip,
        ):
            if path.is_file():
                archive.write(path, path.name)
    return manifest, txt_path, json_path, zip_path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=Path("artifacts/qos_orchestration"))
    parser.add_argument("--public-data", action="store_true")
    parser.add_argument("--data-cutoff")
    parser.add_argument("--gateway-reference", type=Path)
    args = parser.parse_args()
    manifest, *_ = run(
        args.output_dir,
        fixture_mode=not args.public_data,
        gateway_reference=args.gateway_reference,
        data_cutoff=args.data_cutoff,
    )
    print(json.dumps(manifest, ensure_ascii=False))
    return 1 if manifest["status"] == "ERROR" else 0


if __name__ == "__main__":
    raise SystemExit(main())
