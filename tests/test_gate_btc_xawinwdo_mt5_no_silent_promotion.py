from pathlib import Path

def test_experiment_does_not_modify_shared_mt5_adapter():
 s=Path('tools/gate_btc_factory/mt5_shared_family_source.py').read_text()
 assert '"primary_scientific_truth": False' in s
 assert '"historical_backfill_credit": 0' in s
 assert '"factory_economics_feedback_allowed": False' in s
