from pathlib import Path
def test_marker(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_final_head_marker.txt').read_text().strip()=='FINAL_HEAD_NO_MORE_FILES'
