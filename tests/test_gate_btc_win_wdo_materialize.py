import importlib.util,pathlib
P=pathlib.Path(__file__).parents[1]/'tools/gate_btc_factory/win_wdo_materialize.py'
s=importlib.util.spec_from_file_location('m',P); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)
def row(d,t,c=100,liq=10):return {'date':d,'ticker':t,'root':t[:3],'close':c,'liquidity':liq,'liquidity_field':'FinInstrmQty','leaf_sha256':'x'}
def test_frozen_identity_gap_embargo():
 assert m.FAMILY=='XAWINWDO_REGIME_001' and m.GAP=='2021-06-10' and m.EMBARGO==60
def test_nearest_expiry_tie():
 assert m.expiry_key('WINV24','2024-09-01') < m.expiry_key('WINZ24','2024-09-01')
def test_t_minus_one_selection_and_no_cross_expiry_return():
 raw=[]
 for d in ('2024-09-02','2024-09-03','2024-09-04'):
  raw += [row(d,'WINV24',100 if d!='2024-09-04' else 101,20),row(d,'WINZ24',100,20),row(d,'WDOV24',5 if d!='2024-09-04' else 5.1,20),row(d,'WDOZ24',5,20)]
 e=m.select_series(raw)
 assert e and e[0]['WIN_ticker']=='WINV24' and e[0]['WDO_ticker']=='WDOV24'
def test_partition_has_60_session_embargo():
 e=[]
 for i in range(1000):e.append({'date':f'{i:04d}','WIN_ticker':'WINZ30','WDO_ticker':'WDOZ30','WIN_close':100+i,'WDO_close':5+i/100,'WIN_ret':.01,'WDO_ret':.01})
 p=m.partition(e); assert len(p['discovery'])==500 and len(p['validation'])==240 and len(p['holdout'])==140
def test_targets_1_5_20_60_and_no_cross_expiry():
 p=[]
 for i in range(70):p.append({'date':str(i),'WIN_ticker':'WINZ30','WDO_ticker':'WDOZ30','WIN_close':100+i,'WDO_close':5+i/100,'WIN_ret':.01,'WDO_ret':.01})
 q=m.add_targets(p); assert q[0]['next_1_session_WIN'] is not None and q[0]['next_60_session_WDO'] is not None
 p[10]['WIN_ticker']='WINF31'; q=m.add_targets(p); assert q[0]['next_20_session_WIN'] is None
def test_official_parser_schema_fixture():
 x=b'<root><r><TckrSymb>WINF20</TckrSymb><FrstPric>99</FrstPric><MinPric>98</MinPric><MaxPric>101</MaxPric><LastPric>100</LastPric><FinInstrmQty>50</FinInstrmQty></r></root>'
 t,g,ok,r=m.b3.parse_xml(x,'x','sha'); assert ok and len(r)==1 and r[0]['ticker_symbol']=='WINF20' and r[0]['volume_field']=='FinInstrmQty'
