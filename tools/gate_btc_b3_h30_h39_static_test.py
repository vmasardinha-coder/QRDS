from pathlib import Path
p=Path('research/b3_h30_h39_prereg.md').read_text();s=Path('tools/gate_btc_b3_h30_h39_cross_asset.py').read_text()
assert 'H1 economics are forbidden' in p
assert "CUTOFF=pd.Timestamp('2026-08-10'" in s
assert "merge(b[s],on='timestamp'" in s
assert 'ffill' not in s.lower() and 'forward_fill' not in s.lower()
assert "'h1_economics_read':False" in s and "'engine_feed':False" in s
for i in range(30,40): assert f"'H{i}'" in s or 'FAMS=tuple' in s
print('PASS H30-H39 static isolation/exact-sync invariants')
