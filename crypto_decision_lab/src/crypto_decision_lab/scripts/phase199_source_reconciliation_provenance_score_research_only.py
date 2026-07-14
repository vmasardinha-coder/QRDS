from __future__ import annotations

import argparse
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .phase199_205_research_batch_common import (
    LOCKS,
    load_json,
    require_phase,
    utc_now,
    write_json,
    write_text,
)


def score_source(
    source: dict[str, Any],
    temporal: dict[str, Any] | None,
    anomaly: dict[str, Any] | None,
) -> dict[str, Any]:
    components = {
        "content_hash": 20 if len(str(source.get("content_sha256", ""))) == 64 else 0,
        "stable_source_id": 10 if str(source.get("source_id", "")).startswith("src_") else 0,
        "read_only_evidence": 15 if source.get("read_only_evidence") is True else 0,
        "git_provenance": 10 if source.get("tracked_by_git") is True else 0,
        "temporal_contract": 15,
        "temporal_integrity": 15,
        "structural_anomaly_evidence": 15,
    }

    if temporal and temporal.get("temporal_candidate"):
        if temporal.get("inspection_status") != "INSPECTED":
            components["temporal_contract"] = 5
        elif temporal.get("timezone_status") not in {
            "UTC_OR_OFFSET_EXPLICIT",
            "NOT_EVALUATED",
        }:
            components["temporal_contract"] = 5

        if (
            temporal.get("invalid_timestamp_count", 0) > 0
            or temporal.get("non_monotonic_timestamp_count", 0) > 0
        ):
            components["temporal_integrity"] = 0

    anomaly_flags = list((anomaly or {}).get("anomaly_flags", []))
    if anomaly_flags:
        components["structural_anomaly_evidence"] = max(0, 15 - 3 * len(anomaly_flags))

    score = int(sum(components.values()))
    if score >= 80:
        band = "HIGH_EVIDENCE_RESEARCH_ONLY"
    elif score >= 50:
        band = "REVIEW_REQUIRED_RESEARCH_ONLY"
    else:
        band = "LOW_EVIDENCE_RESEARCH_ONLY"

    return {
        "source_id": source["source_id"],
        "path": source["relative_or_absolute_path"],
        "content_sha256": source["content_sha256"],
        "source_role": source.get("source_role", "DISCOVERED_FILE"),
        "score_components": components,
        "provenance_score": score,
        "evidence_band": band,
        "anomaly_flag_count": len(anomaly_flags),
        "anomaly_flags": anomaly_flags,
        "temporal_status": (temporal or {}).get("inspection_status", "NOT_AVAILABLE"),
        "timezone_status": (temporal or {}).get("timezone_status", "NOT_EVALUATED"),
        "reconciled": True,
        "trusted_for_decision": False,
    }


def build_phase199(
    registry_path: Path,
    temporal_path: Path,
    anomaly_path: Path,
    output_dir: Path,
    documentation_path: Path | None = None,
) -> dict[str, Any]:
    registry = load_json(registry_path)
    temporal = load_json(temporal_path)
    anomaly = load_json(anomaly_path)
    require_phase(registry, 196)
    require_phase(temporal, 197)
    require_phase(anomaly, 198)

    temporal_by_id = {item["source_id"]: item for item in temporal.get("source_audits", [])}
    anomaly_by_id = {item["source_id"]: item for item in anomaly.get("source_audits", [])}

    source_scores = [
        score_source(source, temporal_by_id.get(source["source_id"]), anomaly_by_id.get(source["source_id"]))
        for source in registry.get("sources", [])
    ]

    hash_groups: dict[str, list[str]] = defaultdict(list)
    for item in source_scores:
        hash_groups[item["content_sha256"]].append(item["source_id"])

    reconciliation_groups = [
        {
            "content_sha256": content_hash,
            "source_ids": sorted(source_ids),
            "source_count": len(source_ids),
            "relationship": "IDENTICAL_CONTENT" if len(source_ids) > 1 else "UNIQUE_CONTENT",
        }
        for content_hash, source_ids in sorted(hash_groups.items())
    ]

    scores = [item["provenance_score"] for item in source_scores]
    summary = {
        "source_count": len(source_scores),
        "reconciled_source_count": sum(item["reconciled"] for item in source_scores),
        "high_evidence_count": sum(item["evidence_band"] == "HIGH_EVIDENCE_RESEARCH_ONLY" for item in source_scores),
        "review_required_count": sum(item["evidence_band"] == "REVIEW_REQUIRED_RESEARCH_ONLY" for item in source_scores),
        "low_evidence_count": sum(item["evidence_band"] == "LOW_EVIDENCE_RESEARCH_ONLY" for item in source_scores),
        "average_provenance_score": statistics.mean(scores) if scores else 0.0,
        "minimum_provenance_score": min(scores) if scores else 0,
        "maximum_provenance_score": max(scores) if scores else 0,
        "identical_content_group_count": sum(group["source_count"] > 1 for group in reconciliation_groups),
        "flagged_source_count": sum(item["anomaly_flag_count"] > 0 for item in source_scores),
    }

    payload = {
        "schema": "qrds.phase199.source_reconciliation_provenance.v1",
        "phase": 199,
        "phase_status": "PASS_RESEARCH_ONLY",
        "reconciliation_status": "SOURCE_RECONCILIATION_READY_RESEARCH_ONLY",
        "generated_at": utc_now(),
        "source_scores": source_scores,
        "reconciliation_groups": reconciliation_groups,
        "summary": summary,
        "sources_reconciled": True,
        "provenance_scored": True,
        "data_trust_validated": False,
        "valid_for_decision": False,
        "operational_use_allowed": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "next_stage": "PHASE_200_DATA_TRUST_BATCH_CHECKPOINT_RESEARCH_ONLY",
        "locks": LOCKS,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "phase199_source_reconciliation_provenance_score.json", payload)

    if documentation_path:
        rows = [
            f"| `{item['source_id']}` | {item['provenance_score']} | `{item['evidence_band']}` | {item['anomaly_flag_count']} | `{item['path']}` |"
            for item in source_scores[:100]
        ] or ["| _none_ | 0 | _none_ | 0 | _none_ |"]
        write_text(documentation_path, "\n".join([
            "# Phase 199 - Source Reconciliation and Provenance Score",
            "",
            "**Status:** `PASS_RESEARCH_ONLY`",
            "",
            f"- Sources reconciled: `{summary['reconciled_source_count']}`",
            f"- Average provenance score: `{summary['average_provenance_score']:.2f}`",
            f"- Flagged sources: `{summary['flagged_source_count']}`",
            f"- Identical-content groups: `{summary['identical_content_group_count']}`",
            "",
            "| Source | Score | Band | Flags | Path |",
            "|---|---:|---|---:|---|",
            *rows,
            "",
            "Scores are evidence summaries only. They do not approve data for decisions.",
            "",
            "```text",
            "operational_status: BLOCKED_RESEARCH_ONLY",
            "data_trust_validated: False",
            "decision_layer_allowed: False",
            "canonical_data_writes: 0",
            "```",
        ]))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry-path", type=Path, required=True)
    parser.add_argument("--temporal-path", type=Path, required=True)
    parser.add_argument("--anomaly-path", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--documentation-path", type=Path, required=True)
    args = parser.parse_args()
    payload = build_phase199(args.registry_path, args.temporal_path, args.anomaly_path, args.output_dir, args.documentation_path)
    print("PHASE199_SOURCE_RECONCILIATION: PASS")
    print("Sources:", payload["summary"]["source_count"])
    print("Average provenance score:", round(payload["summary"]["average_provenance_score"], 2))
    print("Data trust validated:", payload["data_trust_validated"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
