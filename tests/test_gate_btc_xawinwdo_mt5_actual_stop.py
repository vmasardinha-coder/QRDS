from pathlib import Path
def test_stop(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_actual_stop.txt').read_text().strip()=='ACTUAL_STOP'
