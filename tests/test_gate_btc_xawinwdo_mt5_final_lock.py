from pathlib import Path
def test_lock(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_final_lock.txt').read_text().strip()=='FINAL_LOCKED_HEAD'
