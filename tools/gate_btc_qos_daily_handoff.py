#!/usr/bin/env python3
"""Admit an exact-cutoff, research-only V2A bundle for QOS/PRL/ALT."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zipfile import ZipFile

from tools.gate_btc_daily_research import atomic_json, canonical_payload_sha, load_unique, sha256_file
from tools.gate_btc_prl_alt_same_source_recovery import packed, sha

SCHEMA = "gate_btc.qos_daily_handoff.v1"
RECEIPT = Path("qos_handoff/GATE_BTC_QOS_DAILY_HANDOFF.json")
DAILY_MANIFEST = Path("daily_handoff/GATE_BTC_DAILY_RESEARCH_MANIFEST.json")
BUNDLE = Path("qos_daily/qos_v2a_outputs.zip")
SAFETY = dict(research_only=True, operational_status="NOT_APPROVED",
              orders_generated=0, real_capital_used=0, methodology_changes=0)


def require(ok, message):
    if not ok:
        raise ValueError(message)


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def inspect_bundle(path, cutoff):
    require(path.is_file(), "QOS_V2A_BUNDLE_MISSING")
    with ZipFile(path) as z:
        m = json.loads(z.read("outputs/v2a_run_manifest.json"))
        for member in ("outputs/qos_v2a_current_portfolios.csv",
                       "data/processed/qos_v2a_master_daily.csv"):
            require(z.namelist().count(member) == 1, "QOS_V2A_MEMBER_MISSING_OR_DUPLICATE:" + member)
    require(m.get("data_as_of") == cutoff, "QOS_V2A_CUTOFF_MISMATCH")
    require(m.get("technical_status") == "PASS"
            and m.get("operational_status") == "NOT_APPROVED"
            and m.get("real_orders") == m.get("capital_used") == 0
            and m.get("evidence_status") == "RESEARCH_ONLY_NOT_PROMOTED"
            and m.get("lookahead_guard") == "signals execute on next daily bar",
            "QOS_V2A_SAFETY_MISMATCH")
    return sha256_file(path)


def build(root, cutoff, run_id):
    _, qos = load_unique(root / BUNDLE.parent, "QOS_ORCHESTRATION_MANIFEST_*.json")
    require(qos.get("status") in {"PASS", "PASS_WITH_GATEWAY_PENDING"} and not qos.get("errors")
            and qos.get("requested_data_cutoff") == cutoff and qos.get("matched_component_close") is True,
            "QOS_ORCHESTRATION_CUTOFF_NOT_ADMITTED")
    locks = qos.get("locks", {})
    require(locks.get("research_only") is True
            and locks.get("orders_generated") == locks.get("real_capital_used") == 0
            and locks.get("operational_status") == "NOT_APPROVED", "QOS_ORCHESTRATION_UNSAFE")
    for name in ("V2A", "Delta"):
        matches = [e for e in qos.get("engines", []) if e.get("name") == name]
        require(len(matches) == 1 and matches[0].get("status") == "PASS"
                and matches[0].get("manifest", {}).get("data_as_of") == cutoff,
                "QOS_COMPONENT_CUTOFF_NOT_ADMITTED:" + name)
    result = {**SAFETY, "schema": SCHEMA, "scope": "QOS_PRL_ALT_V2A_ONLY",
              "status": "PASS", "data_cutoff": cutoff, "source_run_id": run_id,
              "v2a_sha256": inspect_bundle(root / BUNDLE, cutoff)}
    atomic_json(root / RECEIPT, result)
    return result


def sealed_source(root, cutoff):
    status = read(root / "STATUS.json")
    require(status.get("status") == "ACTIVE_PROSPECTIVE_THREE_TRACK"
            and status.get("latest_snapshot_date") == cutoff, "QOS_SEALED_SOURCE_NOT_CURRENT")
    active = sorted(p.parent for p in (root / "cycles").glob("*/SIGNAL_STATE.json")
                    if p.parent.name <= cutoff and not (p.parent / "BLOCKED.json").exists())
    require(bool(active), "QOS_ACTIVE_SIGNAL_MISSING")
    cycle = active[-1]
    row = read(cycle / "path" / "snapshots" / f"{cutoff}.json")
    manifest = read(root / "source_evidence" / cycle.name / cutoff / "PRICES.json")
    state = read(cycle / "SIGNAL_STATE.json")
    run_id = row.get("source_run_id", "")
    require(isinstance(run_id, str) and re.fullmatch(r"[1-9][0-9]*", run_id), "QOS_SOURCE_RUN_ID_INVALID")
    require(row.get("row_sha256") == canonical_payload_sha(row, "row_sha256")
            and row.get("snapshot_date") == manifest.get("cutoff") == cutoff
            and row.get("signal_date") == state.get("signal_date") == cycle.name
            and row.get("signal_state_sha256") == manifest.get("signal_state_sha256")
            == state.get("state_sha256") and bool(state.get("state_sha256")), "QOS_SOURCE_ROW_INVALID")
    require(manifest.pop("manifest_sha256", None) == sha(packed(manifest)), "QOS_SOURCE_MANIFEST_INVALID")
    digest = manifest.get("source_run_zip_sha256", "")
    require(isinstance(digest, str) and re.fullmatch(r"[a-f0-9]{64}", digest), "QOS_SOURCE_BUNDLE_DIGEST_INVALID")
    return run_id, digest


def verify(root, cutoff, run_id, qos_root=None):
    path = root / RECEIPT
    if path.is_file():
        receipt = read(path)
        require(receipt.get("schema") == SCHEMA and receipt.get("scope") == "QOS_PRL_ALT_V2A_ONLY"
                and receipt.get("status") == "PASS" and receipt.get("source_run_id") == run_id
                and receipt.get("data_cutoff") == cutoff, "QOS_DAILY_RECEIPT_SCOPE_MISMATCH")
    else:
        # Support full manifests produced before the scoped receipt was introduced.
        require((root / DAILY_MANIFEST).is_file(), "QOS_DAILY_HANDOFF_NOT_PUBLISHED")
        receipt = read(root / DAILY_MANIFEST)
        v2a = receipt.get("components", {}).get("v2a", {})
        require(receipt.get("status") in {"PASS", "PASS_WITH_DATA_WARNINGS"}
                and receipt.get("data_cutoff") == cutoff and v2a.get("status") == "PASS"
                and v2a.get("data_as_of") == cutoff, "QOS_DAILY_LEGACY_HANDOFF_NOT_ADMITTED")
    require(receipt.get("research_only") is True
            and all(receipt.get(k) == v for k, v in SAFETY.items()), "QOS_DAILY_HANDOFF_UNSAFE")
    digest = inspect_bundle(root / BUNDLE, cutoff)
    if path.is_file():
        require(receipt.get("v2a_sha256") == digest, "QOS_DAILY_BUNDLE_HASH_MISMATCH")
    if qos_root is not None:
        require(sealed_source(qos_root, cutoff) == (run_id, digest), "QOS_SEALED_BUNDLE_MISMATCH")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("build", "verify", "resolve"))
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--qos-root", type=Path)
    parser.add_argument("--cutoff", default=(datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat())
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.mode == "build":
        build(args.artifact_root, args.cutoff, args.run_id)
    elif args.mode == "verify":
        verify(args.artifact_root, args.cutoff, args.run_id, args.qos_root)
    else:
        print(sealed_source(args.qos_root, args.cutoff)[0])


if __name__ == "__main__":
    main()
