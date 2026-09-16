from pathlib import Path
def test_head(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_head_final_final.txt').read_text().strip()=='SEALED_EXACT_HEAD'
