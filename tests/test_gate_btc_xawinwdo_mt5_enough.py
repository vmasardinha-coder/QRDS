from pathlib import Path
def test_enough(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_enough.txt').read_text().strip()=='ENOUGH_OPEN_PR'
