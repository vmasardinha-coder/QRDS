from pathlib import Path
def test_seal(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_last_last.txt').read_text().strip()=='SEALED_IMMEDIATELY_BEFORE_PR'
