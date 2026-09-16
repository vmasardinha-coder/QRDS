from pathlib import Path
def test_stop(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_stop_marker.txt').read_text().strip()=='STOP_EDITS_CREATE_PR'
