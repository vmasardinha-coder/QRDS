from pathlib import Path
def test_last_head(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_last_head.txt').read_text().strip()=='LAST_HEAD'
