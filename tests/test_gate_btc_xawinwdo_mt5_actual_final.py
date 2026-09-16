from pathlib import Path
def test_final(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_actual_final.txt').read_text().strip()=='FINAL_HEAD_FOR_PR'
