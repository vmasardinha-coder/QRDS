from pathlib import Path
def test_marker(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_ci_marker.txt').read_text().strip()=='IMPLEMENTATION_READY_FOR_EXACT_HEAD_PR_CI'
