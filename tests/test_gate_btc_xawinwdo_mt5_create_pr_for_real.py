from pathlib import Path
def test_real(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_create_pr_for_real.txt').read_text().strip()=='CREATE_PR_FOR_REAL'
