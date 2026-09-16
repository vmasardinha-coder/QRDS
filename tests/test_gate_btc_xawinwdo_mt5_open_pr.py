from pathlib import Path
def test_open(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_open_pr.txt').read_text().strip()=='OPEN_PR_NEXT_ACTION'
