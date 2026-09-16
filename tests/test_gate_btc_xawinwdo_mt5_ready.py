from pathlib import Path
def test_ready(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_ready.txt').read_text().strip()=='READY_FOR_PR'
