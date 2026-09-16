from pathlib import Path
def test_open(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_open.txt').read_text().strip()=='OPEN_PR_AFTER_THIS_COMMIT'
