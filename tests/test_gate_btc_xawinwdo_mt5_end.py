from pathlib import Path
def test_end(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_end.txt').read_text().strip()=='END'
