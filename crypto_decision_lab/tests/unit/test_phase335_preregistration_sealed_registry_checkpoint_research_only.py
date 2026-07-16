from crypto_decision_lab.scripts import (
    phase335_preregistration_sealed_registry_checkpoint_research_only as module,
)
from tests.unit._phase326_335_fixtures import (
    accepted_chain,
    patch_roots,
    payload,
    phase325_fixture,
    write_json,
    write_junit,
)


def test_phase335_allows_only_next_window_registry_opening(
    monkeypatch, tmp_path
):
    patch_roots(monkeypatch, tmp_path, module)
    values = {325: phase325_fixture(), 326: payload(326)}
    values.update(accepted_chain())
    paths = {
        phase: write_json(tmp_path / f"p{phase}.json", value)
        for phase, value in values.items()
    }
    result = module.build_checkpoint(
        paths,
        targeted_junit_path=write_junit(
            tmp_path / "artifacts/phase335/targeted.xml"
        ),
        artifact_path=tmp_path / "artifacts/phase335/checkpoint.json",
        documentation_path=tmp_path / "docs/integration/phase335.md",
        tracking_dir=tmp_path / "docs/tracking",
    )
    assert result["registry_opening_eligible_next_window"] is True
    assert result["registry_open"] is False
    assert result["historical_evaluation_started"] is False
    assert result["new_family_opened"] is False
    assert result["strategy_approved"] is False
    assert (
        tmp_path / "docs/tracking/qrds_progress_snapshot_phase335.json"
    ).is_file()
