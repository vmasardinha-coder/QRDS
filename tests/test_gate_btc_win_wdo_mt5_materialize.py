import importlib.util
from pathlib import Path
P=Path(__file__).parents[1]/'tools/gate_btc_factory/win_wdo_mt5_materialize.py'; S=importlib.util.spec_from_file_location('m',P); m=importlib.util.module_from_spec(S); S.loader.exec_module(m)
def test_embargo_boundaries_are_frozen():
 rows=[{'i':i} for i in range(1000)]; s=m.split(rows)
 assert s['discovery'][0]['i']==0 and s['discovery'][-1]['i']==439
 assert s['validation'][0]['i']==560 and s['validation'][-1]['i']==739
 assert s['holdout'][0]['i']==860
def test_expiry_identity_excludes_continuous_and_options():
 assert m.PAT.fullmatch('WINZ25') and m.PAT.fullmatch('WDOF23')
 assert not m.PAT.fullmatch('WIN$N') and not m.PAT.fullmatch('WDOF26C6000')
