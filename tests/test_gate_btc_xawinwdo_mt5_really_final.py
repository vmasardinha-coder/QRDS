from pathlib import Path
def test_really_final(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_really_final.txt').read_text().strip()=='REALLY_FINAL_CREATE_PR'
