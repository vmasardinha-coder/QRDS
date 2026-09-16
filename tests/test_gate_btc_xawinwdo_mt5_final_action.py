from pathlib import Path
def test_action(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_final_action.txt').read_text().strip()=='FINAL_ACTION_CREATE_PR'
