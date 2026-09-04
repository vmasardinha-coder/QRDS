from __future__ import annotations

import json
from pathlib import Path

from tools.gate_btc_factory import invalidated_strict_namespace_handoff as handoff


def row(fid: str, namespace: str, status: str = "SCIENTIFIC_REJECTION", attempts: int = 1):
    return {
        "original_family_id": fid,
        "new_namespace": f"{namespace}::{fid}",
        "status": status,
        "attempts": attempts,
        "result_path": f"results/{namespace}__{fid}.json",
        "prospective_candidate_path": None,
        "source_gate_status": "SOURCE_GATE_GREEN_SCOPED",
    }


def test_contaminated_v1_is_reopened_even_without_strict_gate():
    existing = {"families": [row("H2218", handoff.CONTAMINATED_V1_NAMESPACE, attempts=2)]}
    prepared, invalidated = handoff.prepare_existing(existing, [])
    out = prepared["families"][0]
    assert invalidated == 1
    assert out["status"] == "WAITING_SOURCE_QUALIFICATION"
    assert out["source_gate_status"] == "INVALIDATED_2024_OVERLAP_AWAITING_STRICT_V2"
    assert out["attempts"] == 2
    assert out["result_path"].endswith("RQ_FORWARD_UNSEEN_2025_2026_V1__H2218.json")


def test_valid_2025_discovery_rejection_remains_terminal():
    existing = {"families": [row("H1962", "RQ_DISCOVERY_2025_V1")]}
    prepared, invalidated = handoff.prepare_existing(existing, [])
    out = prepared["families"][0]
    assert invalidated == 0
    assert out["status"] == "SCIENTIFIC_REJECTION"
    assert out["new_namespace"] == "RQ_DISCOVERY_2025_V1::H1962"


def test_strict_gate_does_not_reopen_valid_terminal_discovery():
    strict_gate = ({"family_ids": ["H1962"], "evaluation_namespace": handoff.STRICT_NAMESPACE}, None)
    existing = {"families": [row("H1962", "RQ_DISCOVERY_2025_V1")]}
    prepared, invalidated = handoff.prepare_existing(existing, [strict_gate])
    assert invalidated == 0
    assert prepared["families"][0]["status"] == "SCIENTIFIC_REJECTION"


def test_2024_overlap_v1_gate_is_audit_only(tmp_path: Path):
    gates = tmp_path / "source_gates"
    gates.mkdir()
    payload = {
        "evaluation_namespace": handoff.CONTAMINATED_V1_NAMESPACE,
        "windows": {
            "discovery": {"start": "2024-06-19", "end": "2025-03-24"},
            "replication": {"start": "2025-03-25", "end": "2025-12-30"},
        },
        "source": {
            "independence_mode": "TEMPORAL_HOLDOUT_NOT_READ_BY_ORIGINAL_2020_2024_EVALUATOR"
        },
    }
    path = gates / f"{handoff.CONTAMINATED_V1_PREFIX}12.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert handoff.contaminated_v1_gate_names(gates) == [path.name]


def test_strict_gate_rejects_any_pre_2025_discovery(tmp_path: Path):
    gates = tmp_path / "source_gates"
    runtime = tmp_path / "runtime" / "factory_autonomy" / "invalidated_requalification"
    gates.mkdir(parents=True)
    runtime.mkdir(parents=True)
    payload = {
        "evaluation_namespace": handoff.STRICT_NAMESPACE,
        "windows": {
            "discovery": {"start": "2024-12-31", "end": "2025-06-30"},
            "replication": {"start": "2025-07-01", "end": "2025-12-31"},
        },
    }
    path = gates / f"{handoff.STRICT_PREFIX}01.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    try:
        handoff.strict_scoped_sources(gates, runtime)
    except RuntimeError as exc:
        assert "STRICT_DISCOVERY_PRE_HOLDOUT" in str(exc)
    else:
        raise AssertionError("strict gate overlapping 2024 must fail closed")
