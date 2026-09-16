from pathlib import Path
def test_immediate(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_immediate.txt').read_text().strip()=='IMMEDIATE_PR'
