from pathlib import Path
def test_lock(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_lock.txt').read_text().strip()=='LOCKED_FOR_PR'
