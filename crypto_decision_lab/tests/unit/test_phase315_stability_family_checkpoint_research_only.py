from crypto_decision_lab.scripts import phase315_stability_family_checkpoint_research_only as module
from tests.unit._phase306_315_fixtures import (
    patch_roots,
    payload,
    phase304_payload,
    write_json,
    write_junit,
)


def test_phase315_integrated_checkpoint_preserves_no_action(monkeypatch, tmp_path):
    patch_roots(monkeypatch, tmp_path, module)
    paths = {}
    paths[304] = write_json(tmp_path / "artifacts/phase304.json", phase304_payload())
    paths[305] = write_json(
        tmp_path / "artifacts/phase305.json",
        payload(
            305,
            global_full_suite={
                "passed": True,
                "test_file_count": 544,
                "totals": {"tests": 1451, "failures": 0, "errors": 0},
                "manifest_stable": True,
            },
        ),
    )
    for phase in range(306, 311):
        paths[phase] = write_json(tmp_path / f"artifacts/phase{phase}.json", payload(phase))
    paths[311] = write_json(
        tmp_path / "artifacts/phase311.json",
        payload(
            311,
            candidate_hypothesis_id="OI_MOM_H8_T005",
            candidate_eligible=False,
            eligibility_gate_count=9,
            passed_gate_count=2,
            failed_gate_count=7,
            failed_gate_ids=["G01", "G02"],
        ),
    )
    paths[312] = write_json(tmp_path / "artifacts/phase312.json", payload(312, freeze_created=False))
    paths[313] = write_json(
        tmp_path / "artifacts/phase313.json",
        payload(313, evidence_clock_started=False, forward_evidence_credit=0),
    )
    paths[314] = write_json(
        tmp_path / "artifacts/phase314.json",
        payload(
            314,
            scientific_decision="CLOSE_CURRENT_FAMILY_RESEARCH_ONLY",
            candidate_eligible=False,
        ),
    )
    junit = write_junit(tmp_path / "artifacts/phase315/targeted.xml", tests=10)
    result = module.build(
        phase305_path=paths[305],
        phase304_path=paths[304],
        phase306_path=paths[306],
        phase307_path=paths[307],
        phase308_path=paths[308],
        phase309_path=paths[309],
        phase310_path=paths[310],
        phase311_path=paths[311],
        phase312_path=paths[312],
        phase313_path=paths[313],
        phase314_path=paths[314],
        targeted_junit_path=junit,
        artifact_path=tmp_path / "artifacts/phase315/checkpoint.json",
        documentation_path=tmp_path / "docs/reports/integration/phase315.md",
        tracking_dir=tmp_path / "docs/reports/project_tracking",
    )
    assert result["phase"] == 315
    assert result["targeted_tests"]["passed"] is True
    assert result["current_family_decision"] == "CLOSE_CURRENT_FAMILY_RESEARCH_ONLY"
    assert result["strategy_approved"] is False
    assert result["forward_evidence_credit"] == 0
    assert result["locks"]["decision_layer_allowed"] is False
