from pathlib import Path
def test_done(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_done.txt').read_text().strip()=='DONE_IMPLEMENTATION'
