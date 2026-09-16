from pathlib import Path
def test_final_lock(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_last.txt').read_text().strip()=='FINAL_LOCK'
