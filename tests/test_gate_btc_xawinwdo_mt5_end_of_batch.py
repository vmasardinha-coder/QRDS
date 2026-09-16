from pathlib import Path
def test_end(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_end_of_batch.txt').read_text().strip()=='END_IMPLEMENTATION_BATCH'
