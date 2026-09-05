#!/usr/bin/env python3
"""Fail-closed source gate for preregistered B3 autonomous science v3.

This module never evaluates economics.  It only determines whether a physical,
hash-bound official B3 trade/tick manifest exists with the frozen historical
coverage and identity evidence required by protocol v3.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

REQUIRED_PROVIDER = "B3"
REQUIRED_YEARS = {2020, 2021, 2022, 2023, 2024}
OFFICIAL_DISCOVERY_PAGES = [
    "https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/market-data/historico/",
    "https://www.b3.com.br/pt_br/market-data-e-indices/servicos-de-dados/up2data/",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _base(contract: dict) -> dict:
    return {
        "schema": "gate_btc.b3.v3.source_gate.v1",
        "generation": contract["generation"],
        "protocol": contract["protocol"],
        "data_dimension": contract.get("data_dimension"),
        "official_primary_required": True,
        "official_discovery_pages": OFFICIAL_DISCOVERY_PAGES,
        "economics_read": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "fail_closed": True,
    }


def qualify(contract: dict, manifest_path: Path | None) -> dict:
    out = _base(contract)
    if not str(contract.get("protocol", "")).endswith("protocol_v3.md"):
        out.update(status="NOT_APPLICABLE_PRE_V3", ready_for_economics=True, reason="pre-v3 contract")
        return out

    if manifest_path is None or not manifest_path.is_file():
        out.update(
            status="WAITING_OFFICIAL_TICK_SOURCE",
            ready_for_economics=False,
            reason="No physical official-B3 historical trade/tick manifest is materialized for 2020-2024; aggregated public newsletters are not silently substituted.",
            manifest_path=None if manifest_path is None else str(manifest_path),
            next_action="CONTINUE_OFFICIAL_FREE_SOURCE_DISCOVERY_OR_MATERIALIZE_AUDITABLE_AUTHORIZED_ARCHIVE",
        )
        return out

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    if str(manifest.get("provider", "")).upper() != REQUIRED_PROVIDER:
        failures.append("PROVIDER_NOT_B3")
    if manifest.get("source_role") != "OFFICIAL_PRIMARY":
        failures.append("SOURCE_ROLE_NOT_OFFICIAL_PRIMARY")
    if not manifest.get("instrument_identity_policy"):
        failures.append("MISSING_INSTRUMENT_IDENTITY_POLICY")
    if not manifest.get("parser_version"):
        failures.append("MISSING_PARSER_VERSION")
    if not manifest.get("timezone_semantics"):
        failures.append("MISSING_TIMEZONE_SEMANTICS")

    files = manifest.get("files") or []
    years: set[int] = set()
    verified_files = []
    root = manifest_path.parent
    for row in files:
        try:
            year = int(row["year"])
            rel = str(row["path"])
            expected = str(row["sha256"]).lower()
        except Exception:
            failures.append("MALFORMED_FILE_ROW")
            continue
        p = (root / rel).resolve()
        if not p.is_file():
            failures.append(f"FILE_MISSING:{rel}")
            continue
        actual = sha256_file(p)
        if actual != expected:
            failures.append(f"HASH_MISMATCH:{rel}")
            continue
        years.add(year)
        verified_files.append({"year": year, "path": rel, "sha256": actual, "size_bytes": p.stat().st_size})

    missing_years = sorted(REQUIRED_YEARS - years)
    if missing_years:
        failures.append("MISSING_REQUIRED_YEARS:" + ",".join(map(str, missing_years)))

    qa = manifest.get("qa") or {}
    for key in (
        "event_time_monotonic_or_nondecreasing",
        "price_domain_valid",
        "quantity_domain_valid",
        "dedupe_policy_frozen",
        "causal_availability_attested",
        "contract_roll_identity_auditable",
    ):
        if qa.get(key) is not True:
            failures.append(f"QA_NOT_GREEN:{key}")

    if failures:
        out.update(
            status="SOURCE_QA_FAIL",
            ready_for_economics=False,
            reason="Physical candidate source exists but does not satisfy frozen v3 source contract.",
            failures=failures,
            verified_files=verified_files,
            manifest_path=str(manifest_path),
            next_action="REPAIR_SOURCE_OR_IDENTITY_PLUMBING_WITHOUT_CHANGING_V3_SCIENCE",
        )
        return out

    out.update(
        status="GREEN_OFFICIAL_TICK_SOURCE_QUALIFIED",
        ready_for_economics=True,
        reason="Physical official-B3 source manifest, hashes, coverage and structural QA satisfy the frozen v3 source boundary.",
        manifest_path=str(manifest_path),
        manifest_sha256=sha256_file(manifest_path),
        verified_files=verified_files,
        next_action="RUN_FROZEN_V3_EVALUATOR_ONLY",
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--manifest")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    manifest_arg = args.manifest or os.getenv("B3_V3_TICK_MANIFEST")
    manifest = Path(manifest_arg) if manifest_arg else None
    result = qualify(contract, manifest)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"generation": result["generation"], "status": result["status"], "ready_for_economics": result["ready_for_economics"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
