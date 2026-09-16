from pathlib import Path
def test_go(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_go.txt').read_text().strip()=='GO_PR'
