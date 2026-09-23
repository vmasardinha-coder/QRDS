import json
from pathlib import Path


def test_repair_contract_requires_runtime_verification():
    d = json.loads(Path('artifacts/gate_btc_2/XAGENT_SCHEDULE_FALLBACK_REPAIR_CONTRACT_20260923.json').read_text())
    assert 'post_merge_runtime_inspected' in d['repair_complete_when']
    assert 'merge_only' in d['do_not_count_as_complete']
    assert d['scientific_change'] is False
    assert d['backfill'] is False
    assert d['retune'] is False
