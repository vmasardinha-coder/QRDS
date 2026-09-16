from pathlib import Path
def test_ready(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_ready_final.txt').read_text().strip()=='PR_READY_FINAL'
