from tools.gate_btc_factory.win_wdo_independent_runner import SAFETY,FAMILY

def test_isolation_and_fail_closed_contract():
    assert FAMILY=='XAWINWDO_REGIME_001'
    assert SAFETY['h1_h31_untouched'] is True
    assert SAFETY['existing_counter_credit']==0
    assert SAFETY['retroactive_credit']==0
    assert SAFETY['no_retune'] and SAFETY['no_backfill']
    assert SAFETY['economics_opened_without_gates'] is False
