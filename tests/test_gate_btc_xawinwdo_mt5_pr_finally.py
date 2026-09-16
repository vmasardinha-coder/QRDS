from pathlib import Path
def test_finally(): assert Path('tools/gate_btc_factory/xawinwdo_mt5_pr_finally.txt').read_text().strip()=='FINALLY_OPEN_PR'
