from pathlib import Path
def test_stop(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_stop_for_real.txt').read_text().strip()=='STOP_FOR_REAL'
