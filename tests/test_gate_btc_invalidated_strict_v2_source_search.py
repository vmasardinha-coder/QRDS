import hashlib
import json
from pathlib import Path

from tools.gate_btc_factory.invalidated_strict_v2_source_search import (
    STRICT_MINIMUM_SESSIONS,
    STRICT_NAMESPACE,
    _strict_gate_adjudication,
)


def _gate(tmp_path: Path, *, namespace=STRICT_NAMESPACE, sessions=322, discovery_start="2025-01-01"):
    runtime = tmp_path / "runtime"
    dataset = runtime / "factory_autonomy" / "invalidated_requalification" / "datasets" / "strict.csv"
    dataset.parent.mkdir(parents=True)
    dataset.write_text("timestamp,open,high,low,close\n", encoding="utf-8")
    gate = {
        "qualified": True,
        "free_or_official_auditable": True,
        "publication_semantics_proven": True,
        "revision_semantics_proven": True,
        "identity_qa_pass": True,
        "schema_qa_pass": True,
        "point_in_time_valid": True,
        "independent_unseen_evaluation_data": True,
        "no_historical_backfill_credit": True,
        "economics_pre_read": False,
        "evaluation_namespace": namespace,
        "dataset_relative_path": "runtime/factory_autonomy/invalidated_requalification/datasets/strict.csv",
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "source": {"eligible_session_count": sessions},
        "windows": {
            "discovery": {"start": discovery_start, "end": "2025-12-31"},
            "replication": {"start": "2026-01-01", "end": "2026-08-09"},
        },
    }
    path = tmp_path / "SOURCE_GATE.json"
    path.write_text(json.dumps(gate), encoding="utf-8")
    return path, runtime


def test_strict_v2_floor_is_322():
    assert STRICT_MINIMUM_SESSIONS == 322
    assert STRICT_NAMESPACE == "RQ_STRICT_FORWARD_UNSEEN_2025_2026_V2"


def test_exact_strict_gate_can_pass(tmp_path):
    path, runtime = _gate(tmp_path, sessions=322)
    out = _strict_gate_adjudication(path, runtime)
    assert out["valid"] is True
    assert out["minimum_sessions_required"] == 322


def test_legacy_161_floor_cannot_pass_strict_v2(tmp_path):
    path, runtime = _gate(tmp_path, sessions=161)
    out = _strict_gate_adjudication(path, runtime)
    assert out["valid"] is False
    assert out["reason"] == "STRICT_V2_MINIMUM_322_SESSIONS_NOT_MET"


def test_contaminated_v1_namespace_cannot_authorize_v2(tmp_path):
    path, runtime = _gate(tmp_path, namespace="RQ_FORWARD_UNSEEN_2025_2026_V1", sessions=383)
    out = _strict_gate_adjudication(path, runtime)
    assert out["valid"] is False
    assert out["reason"] == "NON_STRICT_V2_NAMESPACE_FORBIDDEN"


def test_discovery_overlap_with_2024_is_forbidden(tmp_path):
    path, runtime = _gate(tmp_path, sessions=383, discovery_start="2024-06-19")
    out = _strict_gate_adjudication(path, runtime)
    assert out["valid"] is False
    assert out["reason"] == "DISCOVERY_START_BEFORE_2025_FORBIDDEN"
