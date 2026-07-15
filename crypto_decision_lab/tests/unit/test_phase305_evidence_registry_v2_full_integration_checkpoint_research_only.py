from pathlib import Path

from crypto_decision_lab.scripts import phase305_evidence_registry_v2_full_integration_checkpoint_research_only as phase305
from crypto_decision_lab.scripts.phase301_305_evidence_v2_common import base_payload, write_json


def _payload(phase: int):
    return base_payload(phase, "TEST_RESEARCH_ONLY")


def test_phase305_consolidates_checkpoint_without_promoting_strategy(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(phase305, "ROOT", tmp_path)

    p301 = _payload(301)
    p301.update({
        "gate": "P301", "complete": True, "forward_evidence_credit": 0,
        "historical_backfill_to_forward_clock": False, "max_candle_rows": 20000,
        "successful_candle_providers": ["BINANCE", "OKX"],
    })
    p302 = _payload(302)
    p302.update({
        "gate": "P302", "artifact_fingerprint": "2" * 64, "feature_count": 18,
        "future_leakage_allowed": False, "features_use_closed_or_settled_data_only": True,
    })
    p303 = _payload(303)
    p303.update({
        "gate": "P303", "artifact_fingerprint": "3" * 64, "registry_closed": True,
        "experiment_budget": 24, "hypotheses": [{"hypothesis_id": f"H{i}"} for i in range(24)],
    })
    p304 = _payload(304)
    p304.update({
        "gate": "P304", "modal_hypothesis_id": "H0", "selection_stable": False,
        "multiple_testing": {"rejected_count": 0},
        "outer_metrics_10bps": {"mean_per_10000_brl": -12.5, "lower_95_per_10000_brl": -25.0},
        "strategy_approved": False, "forward_shadow_eligible": False,
    })

    paths = []
    for phase, payload in ((301, p301), (302, p302), (303, p303), (304, p304)):
        path = tmp_path / f"phase{phase}.json"
        write_json(path, payload)
        paths.append(path)

    fake_full = {
        "passed": True, "test_file_count": 529, "totals": {"tests": 1440, "failures": 0, "errors": 0, "skipped": 0},
        "manifest_stable": True, "reused_file_count": 10, "executed_file_count": 519,
    }
    monkeypatch.setattr(phase305, "run_resumable_full_suite", lambda *args, **kwargs: fake_full)

    artifact = tmp_path / "artifacts/phase305/checkpoint.json"
    payload = phase305.build_checkpoint(
        phase301_path=paths[0], phase302_path=paths[1], phase303_path=paths[2], phase304_path=paths[3],
        artifact_path=artifact, documentation_path=tmp_path / "docs/integration/phase305.md",
        tracking_dir=tmp_path / "docs/tracking", full_suite_output_dir=tmp_path / "artifacts/phase305/full_suite",
    )

    assert payload["window_integration_passed"] is True
    assert payload["strategy_approved"] is False
    assert payload["forward_shadow_eligible"] is False
    assert payload["forward_evidence_credit"] == 0
    assert payload["locks"]["decision_layer_allowed"] is False
    assert payload["locks"]["position_size"] == 0
    assert artifact.is_file()
    assert (tmp_path / "docs/tracking/QRDS_ARCHITECTURE_MERMAID_PHASE305.md").is_file()
    assert (tmp_path / "docs/tracking/qrds_progress_snapshot_phase305.json").is_file()
