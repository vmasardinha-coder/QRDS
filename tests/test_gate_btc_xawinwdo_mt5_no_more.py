from pathlib import Path
def test_no_more(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_no_more.txt').read_text().strip()=='NO_MORE'
