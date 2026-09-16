from pathlib import Path
def test_note(): assert 'PR CI is authoritative' in Path('tools/gate_btc_factory/xawinwdo_mt5_branch_sha_note.txt').read_text()
