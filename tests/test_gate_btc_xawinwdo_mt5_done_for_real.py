from pathlib import Path
def test_done(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_done_for_real.txt').read_text().strip()=='DONE_FOR_REAL'
