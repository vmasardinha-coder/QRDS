from pathlib import Path
def test_boundary(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_boundary.txt').read_text().strip()=='NO_MORE_COMMITS_AFTER_THIS_EXCEPT_CI_FIXES'
