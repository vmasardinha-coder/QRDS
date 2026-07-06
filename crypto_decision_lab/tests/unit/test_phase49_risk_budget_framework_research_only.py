from pathlib import Path
from crypto_decision_lab.scripts.phase49_risk_budget_framework_research_only import READY_GATE, build_phase49

def test_phase49_builds_risk_budget_framework(tmp_path):
    result = build_phase49(tmp_path / 'phase49')
    out = Path(result['output_dir'])
    assert result['gate'] == READY_GATE
    assert result['ready'] is True
    assert result['page_count'] == 8
    assert result['operational_status'] == 'BLOCKED_RESEARCH_ONLY'
    assert result['edge_validated'] is False
    assert result['shadow_decision_allowed'] is False
    assert result['decision_layer_allowed'] is False
    assert result['allocation_generated'] is False
    assert result['portfolio_recommendation_generated'] is False
    assert result['canonical_data_writes'] == 0
    for name in ['index.html','crypto_high_risk_bucket.html','forbidden_outputs.html','phase49_risk_budget_framework.json','phase49_manifest.csv','phase49_checksums.json']:
        assert (out / name).exists(), name
