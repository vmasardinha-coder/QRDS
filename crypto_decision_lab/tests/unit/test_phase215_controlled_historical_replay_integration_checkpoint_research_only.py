from pathlib import Path

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    locks_copy,
    write_json,
)
from crypto_decision_lab.scripts.phase215_controlled_historical_replay_integration_checkpoint_research_only import (
    build_phase215,
)


def write_junit(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            '<?xml version="1.0" encoding="utf-8"?>'
            '<testsuites><testsuite name="pytest" errors="0" '
            'failures="0" skipped="0" tests="2" time="0.1">'
            '<testcase classname="x" name="a" time="0.01"/>'
            '<testcase classname="x" name="b" time="0.01"/>'
            '</testsuite></testsuites>'
        ),
        encoding="utf-8",
    )


def test_phase215_builds_tracking_and_preserves_locks(tmp_path: Path):
    checks = [
        ("contract_passed", True),
        ("window_builder_passed", True),
        ("missing_data_policy_passed", True),
        ("historical_replay_passed", True),
        ("checkpoint_passed", True),
        ("counterfactual_audit_passed", True),
        ("stability_audit_passed", True),
        ("regime_segmentation_passed", True),
        ("evidence_scorecard_passed", True),
    ]
    phase_paths = []
    for phase, (key, value) in zip(range(206, 215), checks):
        path = tmp_path / "artifacts" / f"phase{phase}.json"
        payload = {
            "phase": phase,
            "status": f"PHASE_{phase}_PASS_RESEARCH_ONLY",
            key: value,
            "locks": locks_copy(),
        }
        if phase == 214:
            payload["score"] = 100
        write_json(path, payload)
        phase_paths.append(path)

    test_file = tmp_path / "tests" / "test_sample.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_sample():\n    assert True\n", encoding="utf-8")
    junit = tmp_path / "artifacts" / "targeted.xml"
    write_junit(junit)

    result = build_phase215(
        phase_paths,
        junit,
        [test_file],
        tmp_path / "artifacts" / "phase215.json",
        tmp_path / "docs" / "phase215.md",
        tmp_path / "docs" / "tracking",
        root=tmp_path,
    )

    assert result["window_integration_passed"] is True
    assert result["targeted_integration"]["totals"]["tests"] == 2
    assert result["global_full_suite"]["executed_at_phase215"] is False
    assert result["next_mandatory_global_full_suite"] == 225
    assert result["locks"]["canonical_data_writes"] == 0
