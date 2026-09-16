from pathlib import Path
def test_open(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_open_now.txt').read_text().strip()=='OPEN_NOW'
