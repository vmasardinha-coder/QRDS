from pathlib import Path
def test_head(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_final_head.txt').read_text().strip()=='EXACT_PR_HEAD_FOLLOWS_THIS_COMMIT'
