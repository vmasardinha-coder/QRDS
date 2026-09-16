from pathlib import Path
def test_create(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_create.txt').read_text().strip()=='PR_CREATE_AFTER_THIS'
