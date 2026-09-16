from pathlib import Path
def test_stop(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_stop.txt').read_text().strip()=='STOP_AND_CREATE_PR'
