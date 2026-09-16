from pathlib import Path
def test_trigger(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_trigger.txt').read_text().strip()=='PR_HEAD_FINAL'
