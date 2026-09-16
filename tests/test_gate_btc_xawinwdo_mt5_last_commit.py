from pathlib import Path
def test_last(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_last_commit.txt').read_text().strip()=='LAST_COMMIT_BEFORE_PR'
