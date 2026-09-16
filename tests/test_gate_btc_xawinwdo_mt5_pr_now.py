from pathlib import Path
def test_now(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_now.txt').read_text().strip()=='CREATE_PR_NOW'
