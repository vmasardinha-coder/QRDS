from pathlib import Path
def test_end(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_end_final.txt').read_text().strip()=='FINAL_END_BEFORE_PR'
