#!/usr/bin/env python3
"""Gate BTC 2.0 Evidence Factory MVP (EF-A0..EF-A5).

This module orchestrates scientific evidence for an already-frozen candidate.
It never generates strategies, retunes hypotheses, backfills evidence, runs
portfolio economics, promotes to real capital, or owns collectors.

The implementation is intentionally stdlib-only and fail-closed. Existing
scientific modules remain the scientific authorities; this module only checks
bound artifacts, determines evidence gaps, maintains a deterministic state
machine, emits prospective requirements, reads shared collector health, and
projects status into Executive-compatible items.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_CANDIDATE = "gate_btc.2_0.evidence_factory.candidate.v1"
SCHEMA_CHECKLIST = "gate_btc.2_0.evidence_factory.checklist.v1"
SCHEMA_ASSESSMENT = "gate_btc.2_0.evidence_factory.assessment.v1"
SCHEMA_TRANSITION = "gate_btc.2_0.evidence_factory.transition.v1"
SCHEMA_COLLECT = "gate_btc.2_0.evidence_factory.collect_more.v1"
SCHEMA_EXECUTIVE = "gate_btc.2_0.evidence_factory.executive_projection.v1"
CONTRACT_SCHEMA = "gate_btc.2_0.evidence_factory_contract.v1"

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL_BRL": 0,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
    "NO_SILENT_SOURCE_SUBSTITUTION": True,
    "NO_AUTOMATIC_REAL_CAPITAL_PROMOTION": True,
}

STATES = {
    "RESEARCH_CANDIDATE",
    "FROZEN_HYPOTHESIS",
    "HISTORICAL_EVIDENCE",
    "PIT_REQUIRED",
    "DATA_GAP",
    "SOURCE_DISCOVERY",
    "SOURCE_ADMISSION",
    "PIT_PASS",
    "ROBUSTNESS_REQUIRED",
    "REPLICATION_REQUIRED",
    "PROSPECTIVE_REQUIRED",
    "COLLECT_MORE",
    "PROSPECTIVE_EVIDENCE",
    "ECONOMICS_READY",
    "HUMAN_PROMOTION_REVIEW",
    "SCIENTIFIC_FAIL",
    "HYPOTHESIS_REFUTED",
    "INSUFFICIENT_EVIDENCE",
    "BLOCKED_SOURCE",
    "BLOCKED_TECHNICAL",
}
TERMINAL = {
    "SCIENTIFIC_FAIL",
    "HYPOTHESIS_REFUTED",
    "INSUFFICIENT_EVIDENCE",
    "BLOCKED_SOURCE",
    "BLOCKED_TECHNICAL",
    "HUMAN_PROMOTION_REVIEW",
}

ALLOWED_TRANSITIONS = {
    "RESEARCH_CANDIDATE": {"FROZEN_HYPOTHESIS", "BLOCKED_TECHNICAL"},
    "FROZEN_HYPOTHESIS": {"HISTORICAL_EVIDENCE", "PIT_REQUIRED", "DATA_GAP", "SCIENTIFIC_FAIL", "BLOCKED_TECHNICAL"},
    "HISTORICAL_EVIDENCE": {"PIT_REQUIRED", "DATA_GAP", "ROBUSTNESS_REQUIRED", "HYPOTHESIS_REFUTED", "SCIENTIFIC_FAIL"},
    "PIT_REQUIRED": {"PIT_PASS", "DATA_GAP", "HYPOTHESIS_REFUTED", "SCIENTIFIC_FAIL", "BLOCKED_TECHNICAL"},
    "DATA_GAP": {"SOURCE_DISCOVERY", "COLLECT_MORE", "BLOCKED_SOURCE", "BLOCKED_TECHNICAL"},
    "SOURCE_DISCOVERY": {"SOURCE_ADMISSION", "COLLECT_MORE", "BLOCKED_SOURCE"},
    "SOURCE_ADMISSION": {"PIT_REQUIRED", "COLLECT_MORE", "BLOCKED_SOURCE", "BLOCKED_TECHNICAL"},
    "PIT_PASS": {"ROBUSTNESS_REQUIRED", "HYPOTHESIS_REFUTED", "SCIENTIFIC_FAIL"},
    "ROBUSTNESS_REQUIRED": {"REPLICATION_REQUIRED", "HYPOTHESIS_REFUTED", "SCIENTIFIC_FAIL", "INSUFFICIENT_EVIDENCE"},
    "REPLICATION_REQUIRED": {"PROSPECTIVE_REQUIRED", "HYPOTHESIS_REFUTED", "SCIENTIFIC_FAIL", "INSUFFICIENT_EVIDENCE"},
    "PROSPECTIVE_REQUIRED": {"COLLECT_MORE", "PROSPECTIVE_EVIDENCE", "BLOCKED_SOURCE", "BLOCKED_TECHNICAL"},
    "COLLECT_MORE": {"COLLECT_MORE", "PROSPECTIVE_EVIDENCE", "PIT_REQUIRED", "SOURCE_DISCOVERY", "BLOCKED_SOURCE", "BLOCKED_TECHNICAL"},
    "PROSPECTIVE_EVIDENCE": {"COLLECT_MORE", "ECONOMICS_READY", "HYPOTHESIS_REFUTED", "SCIENTIFIC_FAIL", "INSUFFICIENT_EVIDENCE"},
    "ECONOMICS_READY": {"HUMAN_PROMOTION_REVIEW", "HYPOTHESIS_REFUTED", "SCIENTIFIC_FAIL", "INSUFFICIENT_EVIDENCE"},
}

EVIDENCE_ORDER = (
    "PIT",
    "SURVIVORSHIP",
    "LEAKAGE_CAUSALITY",
    "SOURCE_ADMISSION",
    "DATASET_SEAL",
    "ABLATION",
    "SENSITIVITY_STRESS",
    "INDEPENDENT_REPLICATION",
    "PROSPECTIVE",
    "ECONOMICS_READINESS",
    "RISK_READINESS",
)

CANONICAL_ADAPTERS = {
    "PIT_SURVIVORSHIP_STRESS": {
        "path": "tools/gate_btc_2_selector_alpha_terminal.py",
        "authority": "Selector Alpha terminal scientific proof",
    },
    "SOURCE_ADMISSION": {
        "path": "tools/gate_btc_2_source_admission.py",
        "authority": "Gate BTC 2 source-admission adapter",
    },
    "COLLECTOR_HEALTH": {
        "path": "tools/gate_btc_factory/collector_supervisor.py",
        "registry": "tools/gate_btc_factory/FACTORY_COLLECTOR_REGISTRY.v1.json",
        "authority": "Factory Collector Supervisor issue #221 / PR #232",
    },
}


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    require(isinstance(payload, dict), f"JSON object required: {path}")
    return payload


def validate_candidate(candidate: dict[str, Any]) -> None:
    required = {
        "schema", "candidate_id", "candidate_version", "hypothesis_sha256",
        "config_sha256", "code_sha256", "cutoff_utc", "d0_utc",
        "source_identity", "strategy_factory_artifact_sha256", "required_evidence",
        "safety",
    }
    require(candidate.get("schema") == SCHEMA_CANDIDATE, "candidate schema invalid")
    missing = sorted(required - set(candidate))
    require(not missing, f"candidate fields missing: {missing}")
    for key in ("hypothesis_sha256", "config_sha256", "code_sha256", "strategy_factory_artifact_sha256"):
        value = candidate.get(key)
        require(isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value), f"{key} invalid")
    require(isinstance(candidate["source_identity"], dict) and candidate["source_identity"], "source_identity required")
    require(candidate.get("safety") == SAFETY, "candidate safety boundary drift")
    evidence = candidate.get("required_evidence")
    require(isinstance(evidence, list) and evidence, "required_evidence must be non-empty")
    unknown = sorted(set(evidence) - set(EVIDENCE_ORDER))
    require(not unknown, f"unknown evidence requirements: {unknown}")
    require(candidate["cutoff_utc"].endswith("Z") and candidate["d0_utc"].endswith("Z"), "cutoff/d0 must be UTC Z")


def build_checklist(candidate: dict[str, Any]) -> dict[str, Any]:
    """EF-A0: deterministic frozen handoff -> evidence checklist."""
    validate_candidate(candidate)
    requirements = [name for name in EVIDENCE_ORDER if name in set(candidate["required_evidence"])]
    payload = {
        "schema": SCHEMA_CHECKLIST,
        "candidate_id": candidate["candidate_id"],
        "candidate_version": candidate["candidate_version"],
        "candidate_binding_sha256": canonical_hash(candidate),
        "requirements": [
            {"evidence_type": name, "required": True, "status": "MISSING", "artifact": None, "artifact_sha256": None}
            for name in requirements
        ],
        "adapter_authorities": CANONICAL_ADAPTERS,
        "safety": SAFETY,
    }
    payload["checklist_sha256"] = canonical_hash(payload)
    return payload


def validate_evidence_record(record: dict[str, Any]) -> None:
    require(record.get("evidence_type") in EVIDENCE_ORDER, "evidence_type invalid")
    require(record.get("status") in {"PASS", "FAIL", "MISSING", "COLLECT_MORE", "BLOCKED"}, "evidence status invalid")
    if record["status"] in {"PASS", "FAIL"}:
        digest = record.get("artifact_sha256")
        require(isinstance(digest, str) and len(digest) == 64, "PASS/FAIL requires artifact_sha256")
        require(bool(record.get("authority")), "PASS/FAIL requires scientific authority")
    require(record.get("retuned", False) is False, "retuned evidence forbidden")
    require(record.get("backfilled_as_prospective", False) is False, "backfilled prospective evidence forbidden")
    require(record.get("silent_source_substitution", False) is False, "silent source substitution forbidden")


def next_action_for(evidence_type: str, status: str) -> tuple[str, str]:
    if status == "FAIL":
        return "FAIL", "HYPOTHESIS_REFUTED"
    if status == "BLOCKED":
        return "COLLECT_MORE", "BLOCKED_TECHNICAL"
    if evidence_type == "PIT":
        return "COLLECT_MORE", "PIT_REQUIRED"
    if evidence_type in {"SOURCE_ADMISSION", "DATASET_SEAL"}:
        return "COLLECT_MORE", "SOURCE_DISCOVERY"
    if evidence_type in {"ABLATION", "SENSITIVITY_STRESS"}:
        return "COLLECT_MORE", "ROBUSTNESS_REQUIRED"
    if evidence_type == "INDEPENDENT_REPLICATION":
        return "COLLECT_MORE", "REPLICATION_REQUIRED"
    if evidence_type == "PROSPECTIVE":
        return "COLLECT_MORE", "PROSPECTIVE_REQUIRED"
    if evidence_type in {"ECONOMICS_READINESS", "RISK_READINESS"}:
        return "COLLECT_MORE", "PROSPECTIVE_EVIDENCE"
    return "COLLECT_MORE", "DATA_GAP"


def assess(candidate: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    """EF-A1: deterministic gap engine; negative evidence wins immediately."""
    checklist = build_checklist(candidate)
    by_type: dict[str, dict[str, Any]] = {}
    for record in records:
        validate_evidence_record(record)
        require(record["evidence_type"] not in by_type, f"duplicate evidence: {record['evidence_type']}")
        by_type[record["evidence_type"]] = record

    ordered = [row["evidence_type"] for row in checklist["requirements"]]
    for evidence_type in ordered:
        record = by_type.get(evidence_type, {"evidence_type": evidence_type, "status": "MISSING"})
        if record["status"] == "FAIL":
            decision, state = "FAIL", "HYPOTHESIS_REFUTED"
            break
        if record["status"] != "PASS":
            decision, state = next_action_for(evidence_type, record["status"])
            break
    else:
        decision, state = "PASS", "HUMAN_PROMOTION_REVIEW"

    payload = {
        "schema": SCHEMA_ASSESSMENT,
        "candidate_id": candidate["candidate_id"],
        "candidate_binding_sha256": canonical_hash(candidate),
        "checklist_sha256": checklist["checklist_sha256"],
        "decision": decision,
        "next_state": state,
        "evaluated_evidence": [by_type[k] for k in ordered if k in by_type],
        "missing_or_nonpass": [k for k in ordered if by_type.get(k, {}).get("status") != "PASS"],
        "safety": SAFETY,
    }
    payload["assessment_sha256"] = canonical_hash(payload)
    return payload


def transition(candidate_sha256: str, previous: str, target: str, reason: str, prior_transition_sha256: str | None = None) -> dict[str, Any]:
    """EF-A3: append-only, hash-linked state transition record."""
    require(previous in STATES and target in STATES, "unknown evidence state")
    require(previous not in TERMINAL, f"terminal state is immutable: {previous}")
    require(target in ALLOWED_TRANSITIONS.get(previous, set()), f"invalid transition {previous}->{target}")
    require(len(candidate_sha256) == 64, "candidate binding invalid")
    payload = {
        "schema": SCHEMA_TRANSITION,
        "candidate_binding_sha256": candidate_sha256,
        "previous_state": previous,
        "target_state": target,
        "reason": reason,
        "prior_transition_sha256": prior_transition_sha256,
        "safety": SAFETY,
    }
    payload["transition_sha256"] = canonical_hash(payload)
    return payload


def adapter_inventory(root: Path) -> dict[str, Any]:
    """EF-A2: prove canonical authorities are present; never copy their science."""
    rows = {}
    for name, descriptor in CANONICAL_ADAPTERS.items():
        path = root / descriptor["path"]
        rows[name] = {
            **descriptor,
            "present": path.is_file(),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None,
        }
        if "registry" in descriptor:
            registry = root / descriptor["registry"]
            rows[name]["registry_present"] = registry.is_file()
            rows[name]["registry_sha256"] = hashlib.sha256(registry.read_bytes()).hexdigest() if registry.is_file() else None
    return rows


def collector_health_requirement(
    candidate: dict[str, Any],
    collector_id: str,
    required_data: list[str],
    source: str,
    frequency: str,
    required_n: int,
    target_gate: str,
    earliest_decision_date: str,
    health_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    """EF-A4: consume shared supervisor health. Missing/unhealthy => COLLECT_MORE."""
    validate_candidate(candidate)
    require(required_n > 0, "required_n must be positive")
    health_row = None
    if health_payload is not None:
        require(health_payload.get("schema") == "qrds.factory.collector_health.v1", "collector health schema invalid")
        require(health_payload.get("safety") == {
            "RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True,
            "ORDERS": 0, "REAL_CAPITAL": 0, "ENGINE_FEED": False,
        }, "collector health safety drift")
        health_row = next((r for r in health_payload.get("collectors", []) if r.get("collector_id") == collector_id), None)
    healthy = bool(health_row) and health_row.get("anomaly_class") is None
    current_n = (health_row or {}).get("canonical_counter")
    enough = isinstance(current_n, int) and current_n >= required_n
    payload = {
        "schema": SCHEMA_COLLECT,
        "candidate_id": candidate["candidate_id"],
        "candidate_binding_sha256": canonical_hash(candidate),
        "decision": "PASS" if healthy and enough else "COLLECT_MORE",
        "collector_id": collector_id,
        "collector_owned_by_evidence_factory": False,
        "required_data": required_data,
        "source": source,
        "frequency": frequency,
        "required_N": required_n,
        "current_N": current_n,
        "target_gate": target_gate,
        "earliest_decision_date": earliest_decision_date,
        "collector_health": "HEALTHY" if healthy else "MISSING_OR_UNHEALTHY",
        "prospective_credit_from_backfill": 0,
        "safety": SAFETY,
    }
    payload["requirement_sha256"] = canonical_hash(payload)
    return payload


def executive_projection(candidate: dict[str, Any], assessment: dict[str, Any], collect_more: dict[str, Any] | None = None) -> dict[str, Any]:
    """EF-A5: machine-readable projection; no Executive replacement or economics."""
    validate_candidate(candidate)
    require(assessment.get("schema") == SCHEMA_ASSESSMENT, "assessment schema invalid")
    status = assessment["next_state"]
    payload = {
        "schema": SCHEMA_EXECUTIVE,
        "candidate_id": candidate["candidate_id"],
        "candidate_binding_sha256": canonical_hash(candidate),
        "items": {
            "1B": {"topic": "PIT_SURVIVORSHIP_SELECTOR_EVIDENCE", "status": status},
            "6": {"topic": "PROSPECTIVE_COUNTERS_COLLECTOR_HEALTH", "status": (collect_more or {}).get("decision", "NOT_EVALUATED")},
            "10": {"topic": "MONTE_CARLO_EVIDENCE_READINESS_ONLY", "status": "READY" if assessment["decision"] == "PASS" else "BLOCKED_BY_EVIDENCE"},
            "11": {"topic": "PROMOTION_READINESS", "status": "HUMAN_PROMOTION_REVIEW" if assessment["decision"] == "PASS" else "NOT_READY"},
            "12": {"topic": "GATE_BTC_2_EVIDENCE_FACTORY", "status": status},
            "13": {"topic": "STRATEGY_FACTORY_HANDOFF", "status": "FROZEN_CANDIDATE_BOUND"},
        },
        "automatic_promotion": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "safety": SAFETY,
    }
    payload["projection_sha256"] = canonical_hash(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--evidence", help="JSON list or {'records': [...]} evidence file")
    parser.add_argument("--collector-health")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    candidate = read_json(Path(args.candidate))
    evidence: list[dict[str, Any]] = []
    if args.evidence:
        raw = json.loads(Path(args.evidence).read_text(encoding="utf-8-sig"))
        evidence = raw if isinstance(raw, list) else raw.get("records", [])
        require(isinstance(evidence, list), "evidence records must be list")
    assessment = assess(candidate, evidence)
    output = {
        "candidate_sha256": canonical_hash(candidate),
        "checklist": build_checklist(candidate),
        "assessment": assessment,
        "adapter_inventory": adapter_inventory(Path(__file__).resolve().parents[1]),
        "executive": executive_projection(candidate, assessment),
        "safety": SAFETY,
    }
    Path(args.out).write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"decision": assessment["decision"], "next_state": assessment["next_state"], "safety": SAFETY}, sort_keys=True))


if __name__ == "__main__":
    main()
