from pathlib import Path

def test_h14_h29_batch_h1_firewall_contract():
    s=Path('tools/gate_btc_b3_h14_h29_batch.py').read_text()
    assert "CUTOFF=pd.Timestamp('2026-08-10'" in s
    assert "'h1_economics_read':False" in s
    assert "'h1_contaminated':False" in s
    assert "'orders_generated':0" in s
    assert "'real_capital_used':0" in s
    assert "for asset in ('WIN','WDO')" in s
