from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .phase199_205_research_batch_common import LOCKS, load_json, require_phase, utc_now, write_json, write_text


def build_phase200(
    registry_path: Path,
    temporal_path: Path,
    anomaly_path: Path,
    reconciliation_path: Path,
    output_dir: Path,
    documentation_path: Path | None = None,
) -> dict[str, Any]:
    registry = load_json(registry_path)
    temporal = load_json(temporal_path)
    anomaly = load_json(anomaly_path)
    reconciliation = load_json(reconciliation_path)
    for payload, phase in ((registry, 196), (temporal, 197), (anomaly, 198), (reconciliation, 199)):
        require_phase(payload, phase)

    dimensions = {
        "registry_ready": registry.get("registry_ready") is True,
        "temporal_policy_ready": temporal.get("temporal_policy_ready") is True,
        "anomaly_audit_ready": anomaly.get("anomaly_audit_ready") is True,
        "sources_reconciled": reconciliation.get("sources_reconciled") is True,
        "provenance_scored": reconciliation.get("provenance_scored") is True,
    }
    findings = {
        "timezone_review_count": temporal.get("summary", {}).get("timezone_review_count", 0),
        "invalid_timestamp_source_count": temporal.get("summary", {}).get("invalid_timestamp_source_count", 0),
        "non_monotonic_source_count": temporal.get("summary", {}).get("non_monotonic_source_count", 0),
        "flagged_source_count": anomaly.get("summary", {}).get("flagged_source_count", 0),
        "ohlc_invariant_violation_count": anomaly.get("summary", {}).get("ohlc_invariant_violation_count", 0),
        "missing_value_count": anomaly.get("summary", {}).get("missing_value_count", 0),
        "review_required_count": reconciliation.get("summary", {}).get("review_required_count", 0),
        "low_evidence_count": reconciliation.get("summary", {}).get("low_evidence_count", 0),
    }
    finding_total = sum(int(value) for value in findings.values())
    checkpoint_status = "READY_WITH_FINDINGS_RESEARCH_ONLY" if finding_total else "READY_RESEARCH_ONLY"

    payload = {
        "schema": "qrds.phase200.data_trust_checkpoint.v1",
        "phase": 200,
        "phase_status": "PASS_RESEARCH_ONLY",
        "checkpoint_status": checkpoint_status,
        "generated_at": utc_now(),
        "dimensions": dimensions,
        "findings": findings,
        "finding_total": finding_total,
        "evidence_chain_complete_196_199": all(dimensions.values()),
        "data_trust_checkpoint_ready": all(dimensions.values()),
        "data_trust_validated": False,
        "freshness_validated": False,
        "anomaly_free_validated": False,
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "next_stage": "PHASE_201_DETERMINISTIC_SHADOW_REPLAY_HARNESS_RESEARCH_ONLY",
        "locks": LOCKS,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase200_data_trust_batch_checkpoint.json", payload)
    if documentation_path:
        write_text(documentation_path, "\n".join([
            "# Phase 200 - Data Trust Batch Checkpoint",
            "",
            f"**Status:** `{checkpoint_status}`",
            "",
            f"- Evidence chain 196-199 complete: `{payload['evidence_chain_complete_196_199']}`",
            f"- Finding total: `{finding_total}`",
            f"- Flagged sources: `{findings['flagged_source_count']}`",
            f"- OHLC violations: `{findings['ohlc_invariant_violation_count']}`",
            f"- Missing values: `{findings['missing_value_count']}`",
            "",
            "The checkpoint confirms evidence availability, not data trust.",
            "",
            "```text",
            "data_trust_validated: False",
            "valid_for_decision: False",
            "operational_status: BLOCKED_RESEARCH_ONLY",
            "canonical_data_writes: 0",
            "```",
        ]))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-path", type=Path, required=True)
    parser.add_argument("--temporal-path", type=Path, required=True)
    parser.add_argument("--anomaly-path", type=Path, required=True)
    parser.add_argument("--reconciliation-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--documentation-path", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase200(args.registry_path, args.temporal_path, args.anomaly_path, args.reconciliation_path, args.output_dir, args.documentation_path)
    print("PHASE200_DATA_TRUST_CHECKPOINT: PASS")
    print("Checkpoint status:", payload["checkpoint_status"])
    print("Finding total:", payload["finding_total"])
    print("Data trust validated:", payload["data_trust_validated"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
