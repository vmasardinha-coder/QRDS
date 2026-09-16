from pathlib import Path
def test_last(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_last_one.txt').read_text().strip()=='LAST_ONE'
