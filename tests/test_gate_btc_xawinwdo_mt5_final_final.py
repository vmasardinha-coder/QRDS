from pathlib import Path
def test_ff(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_final_final.txt').read_text().strip()=='FINAL_FINAL'
