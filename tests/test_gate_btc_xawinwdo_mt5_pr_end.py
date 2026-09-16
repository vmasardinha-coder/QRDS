from pathlib import Path
def test_end(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_end.txt').read_text().strip()=='END_PRE_PR_COMMITS'
