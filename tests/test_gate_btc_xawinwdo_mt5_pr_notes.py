from pathlib import Path
def test_notes():
 s=Path('tools/gate_btc_factory/xawinwdo_mt5_pr_notes.md').read_text(); assert 'XAWINWDO_REGIME_001' in s; assert 'broader Factory admission remains a separate decision' in s; assert 'Existing B3 materializer' in s
