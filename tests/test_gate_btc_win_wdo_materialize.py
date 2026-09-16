import importlib.util, pathlib
P=pathlib.Path(__file__).parents[1]/'tools/gate_btc_factory/win_wdo_materialize.py'
s=importlib.util.spec_from_file_location('m',P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
def test_frozen_identity_and_gap():
 assert m.FAMILY=='XAWINWDO_REGIME_001'; assert m.GAP=='2021-06-10'
def test_parser_rejects_non_contract_xml():
 assert m.rows_from_xml(b'<root><ticker>WINXYZ</ticker><close>1</close></root>','2020-01-02','x')==[]
def test_parser_accepts_exact_expiry_and_numeric_fields():
 x=b'<root><r><TckrSymb>WINF20</TckrSymb><ClsgPric>100</ClsgPric><TradQty>50</TradQty></r></root>'
 r=m.rows_from_xml(x,'2020-01-02','x'); assert len(r)==1 and r[0]['ticker']=='WINF20' and r[0]['liquidity']==50
