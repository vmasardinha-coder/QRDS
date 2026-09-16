from pathlib import Path
def test_it(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_this_is_it.txt').read_text().strip()=='THIS_IS_IT'
