from pathlib import Path
def test_head(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_head_final.txt').read_text().strip()=='HEAD_FINAL'
