from pathlib import Path
def test_final(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_final.txt').read_text().strip()=='FINAL_PRE_PR'
