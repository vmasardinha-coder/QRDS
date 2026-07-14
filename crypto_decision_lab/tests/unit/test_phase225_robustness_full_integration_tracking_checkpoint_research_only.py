from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    locks_copy,
    write_json,
)
from crypto_decision_lab.scripts.phase225_robustness_full_integration_tracking_checkpoint_research_only import (
    build_phase225_from_full_suite,
)


def test_phase225_builds_tracking_from_passing_full_suite(tmp_path: Path):
    keys = [
        "provenance_completeness_passed",
        "multi_source_agreement_diagnostic_passed",
        "contamination_sensitivity_passed",
        "window_boundary_perturbation_passed",
        "robustness_checkpoint_passed",
        "benchmark_comparison_passed",
        "calibration_diagnostic_passed",
        "cost_slippage_sensitivity_passed",
        "robustness_scorecard_passed",
    ]
    paths = []
    for phase, key in zip(range(216, 225), keys):
        path = tmp_path / "artifacts" / f"phase{phase}.json"
        payload = {
            "phase": phase,
            "status": "PASS_RESEARCH_ONLY",
            key: True,
            "locks": locks_copy(),
        }
        if phase == 224:
            payload["score"] = 100
        write_json(path, payload)
        paths.append(path)

    full_suite = {
        "passed": True,
        "test_file_count": 463,
        "manifest_before": [],
        "manifest_after": [],
        "manifest_stable": True,
        "shard_count": 3,
        "all_shards_completed": True,
        "shards": [
            {"shard": 1, "junit": {"tests": 454, "failures": 0, "errors": 0, "skipped": 0}},
            {"shard": 2, "junit": {"tests": 454, "failures": 0, "errors": 0, "skipped": 0}},
            {"shard": 3, "junit": {"tests": 454, "failures": 0, "errors": 0, "skipped": 0}},
        ],
        "totals": {"tests": 1362, "failures": 0, "errors": 0, "skipped": 0},
        "restored_tracked_paths": [],
        "removed_generated_untracked_paths": [],
        "removed_test_processes": [],
        "timeout_seconds_per_shard": 5400,
    }

    result = build_phase225_from_full_suite(
        paths,
        full_suite,
        tmp_path / "artifacts" / "phase225.json",
        tmp_path / "docs" / "phase225.md",
        tmp_path / "docs" / "tracking",
        root=tmp_path,
    )
    assert result["window_integration_passed"] is True
    assert result["global_full_suite_passed"] is True
    assert result["checkpoint_status"] == (
        "FULL_INTEGRATION_216_225_PASS_RESEARCH_ONLY"
    )
    assert result["next_tracking_checkpoint"] == 235
    assert result["next_mandatory_global_full_suite"] == 245
    assert result["data_trust_validated"] is False
    assert result["locks"]["canonical_data_writes"] == 0
    assert (
        tmp_path
        / "docs"
        / "tracking"
        / "QRDS_ROADMAP_226_235_RESEARCH_ONLY.md"
    ).is_file()
