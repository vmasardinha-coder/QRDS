import json
from tools.gate_btc_factory.autonomous_grammar_scout import scout,CHANNELS
def _write_result(path):
 path.write_text(json.dumps({'status':'CLOSED_NO_SURVIVOR','families':[{'contract':{'feature':'OPEN_RETURN','direction':'CONTINUATION','causal_standardization':'ROLLING_20_PRIOR_SESSIONS_MEDIAN_MAD'}}]}))
def fake_fetcher(query):
 return [{'openalex_id':'W'+str(abs(hash(query))),'doi':None,'title':'Brazil B3 futures options auction securities lending interest rate price discovery '+query,'publication_year':2024,'source':'Journal'}]
def test_scout_is_blind_and_expanded(tmp_path):
 r=tmp_path/'results';r.mkdir();_write_result(r/'gate_btc_b3_h170_h179_result.json');out=scout(r,fetcher=fake_fetcher)
 assert out['mode']=='IDEATION_ONLY_NO_ECONOMICS' and out['history_used_for_selection'] is False
 assert len(CHANNELS)>=8
 assert any(x['channel_id']=='B3_TERM_STRUCTURE_DI_FUTURES_TRANSMISSION' for x in out['proposals'])
 assert all(x['economics_read'] is False and x['may_allocate_family_id'] is False for x in out['proposals'])
def test_factory_007_channels_are_ideation_only(tmp_path):
 expected={
  'BCB_FOCUS_EXPECTATIONS_REVISION_B3_TRANSMISSION',
  'B3_INDEX_REBALANCE_ANNOUNCEMENT_TRANSMISSION',
  'BCB_FX_SWAP_AUCTION_B3_TRANSMISSION',
  'CVM_FUND_FLOW_B3_TRANSMISSION',
  'B3_FOREIGN_INVESTOR_FLOW_TRANSMISSION',
 }
 assert expected <= {x['channel_id'] for x in CHANNELS}
 r=tmp_path/'results';r.mkdir();out=scout(r,fetcher=fake_fetcher)
 rows=[x for x in out['proposals'] if x['channel_id'] in expected]
 assert len(rows)==5
 assert all(x['economics_read'] is False for x in rows)
 assert all(x['may_allocate_family_id'] is False and x['may_change_existing_grammar'] is False and x['may_test_threshold_grid'] is False for x in rows)
def test_existing_channel_is_suppressed_but_new_remains(tmp_path):
 r=tmp_path/'results';r.mkdir();_write_result(r/'gate_btc_b3_h170_h179_result.json');e=tmp_path/'existing';e.mkdir();(e/'old.json').write_text(json.dumps({'proposals':[{'channel_id':'B3_ADR_CROSS_LISTING_PRICE_DISCOVERY'}]}));out=scout(r,e,fake_fetcher)
 adr=next(x for x in out['proposals'] if x['channel_id']=='B3_ADR_CROSS_LISTING_PRICE_DISCOVERY'); assert adr['status']=='DUPLICATE_CHANNEL_SUPPRESSED'
 assert any(x['status']=='SCOUTED_NOT_PREREGISTERED' for x in out['proposals'] if x['channel_id']!='B3_ADR_CROSS_LISTING_PRICE_DISCOVERY')
def test_irrelevant_literature_fails_closed(tmp_path):
 r=tmp_path/'results';r.mkdir();
 def noise(q):return [{'openalex_id':'N','title':'Anti obesity pharmaceutical trial in mice','publication_year':2024,'source':'X','doi':None}]
 out=scout(r,fetcher=noise);assert all(x['status']=='INSUFFICIENT_EXTERNAL_EVIDENCE_FAIL_CLOSED' for x in out['proposals'])
