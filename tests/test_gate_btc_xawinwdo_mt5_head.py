from pathlib import Path
def test_head(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_head.txt').read_text().strip()=='THIS_COMMIT_PRECEDES_PR_CREATION'
