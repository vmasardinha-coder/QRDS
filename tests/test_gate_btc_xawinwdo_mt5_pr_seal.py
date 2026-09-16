from pathlib import Path
def test_seal(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_seal.txt').read_text().strip()=='PR_HEAD_SEALED'
