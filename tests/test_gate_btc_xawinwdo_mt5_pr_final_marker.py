from pathlib import Path
def test_marker(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_final_marker.txt').read_text().strip()=='OPEN_PULL_REQUEST'
