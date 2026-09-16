from pathlib import Path
def test_commit(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_commit.txt').read_text().strip()=='FINAL_PR_COMMIT'
