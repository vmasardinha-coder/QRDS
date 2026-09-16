#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
import requests
SCHEMA='qrds.factory.grammar_scout.v2'; OPENALEX='https://api.openalex.org/works'
CHANNELS=[
{'channel_id':'B3_ADR_CROSS_LISTING_PRICE_DISCOVERY','queries':['Brazil ADR B3 price discovery','Brazilian ADR lead lag Bovespa'],'mechanism':'Cross-listed Brazilian shares and US ADRs can transmit information across distinct market clocks.','required_new_data':['B3 underlying','US ADR','FX timing','exchange calendars'],'official_free_source_candidates':['B3','CVM','SEC EDGAR','BCB']},
{'channel_id':'B3_INDEX_FUTURES_CASH_PRICE_DISCOVERY','queries':['Brazil index futures cash price discovery B3','Ibovespa futures lead lag cash market'],'mechanism':'Index futures and cash may incorporate common information at different speeds.','required_new_data':['B3 index futures','B3 cash index','auction/calendar metadata'],'official_free_source_candidates':['B3','CVM']},
{'channel_id':'B3_CROSS_ASSET_FX_COMMODITY_TRANSMISSION','queries':['Brazil equities exchange rate commodity price discovery','Bovespa dollar futures cross market lead lag'],'mechanism':'Brazilian equities, BRL and commodity-linked assets may exhibit clock-respecting information transmission.','required_new_data':['B3 equities/futures','BRL','commodity reference'],'official_free_source_candidates':['B3','BCB','CFTC','EIA','FRED']},
{'channel_id':'B3_TERM_STRUCTURE_DI_FUTURES_TRANSMISSION','queries':['Brazil DI futures term structure equity returns','Brazil interest rate futures B3 price discovery'],'mechanism':'Lagged changes in the B3 DI futures curve may transmit monetary-policy and discount-rate information to later equity/index returns.','required_new_data':['B3 DI futures expiry curve','B3 equity/index series','BCB policy calendar'],'official_free_source_candidates':['B3','BCB']},
{'channel_id':'B3_OPTIONS_IMPLIED_STATE_TRANSMISSION','queries':['Brazil Bovespa options implied volatility future returns','B3 options implied volatility price discovery'],'mechanism':'Option-implied state variables observable before the target session may contain forward-looking information distinct from underlying returns.','required_new_data':['B3 listed option chain','underlying B3 asset','expiry/strike metadata'],'official_free_source_candidates':['B3']},
{'channel_id':'B3_AUCTION_IMBALANCE_OPEN_CLOSE_TRANSMISSION','queries':['Brazil stock opening auction price discovery','B3 closing auction price discovery imbalance'],'mechanism':'Opening and closing auction states may concentrate price discovery and transmit information only to subsequent eligible observations.','required_new_data':['B3 auction trades/quotes or official auction fields','B3 calendar'],'official_free_source_candidates':['B3']},
{'channel_id':'B3_SECURITIES_LENDING_SHORT_PRESSURE','queries':['Brazil securities lending short selling future returns','Brazil BTC securities lending B3 predictive'],'mechanism':'Lagged securities-lending utilization or fee pressure may proxy short-demand constraints and be tested against strictly subsequent returns.','required_new_data':['B3 securities lending aggregates','B3 underlying prices'],'official_free_source_candidates':['B3']},
{'channel_id':'CVM_CORPORATE_EVENT_DELAYED_TRANSMISSION','queries':['Brazil CVM material facts stock price reaction','Brazil corporate disclosure delayed market reaction'],'mechanism':'Timestamped corporate disclosures can define ex-ante event grammars whose post-publication response is evaluated only after the public timestamp.','required_new_data':['CVM timestamped disclosures','B3 underlying prices','exchange calendar'],'official_free_source_candidates':['CVM','B3']},
{'channel_id':'BCB_MACRO_SURPRISE_B3_TRANSMISSION','queries':['Brazil central bank macro announcement stock market intraday','Brazil monetary policy announcement Bovespa reaction'],'mechanism':'Pre-scheduled BCB releases and decisions can define clock-auditable event windows for strictly subsequent B3 responses.','required_new_data':['BCB release calendar/value','B3 market data'],'official_free_source_candidates':['BCB','B3']},
]
TOKEN_RE=re.compile(r'[A-Z0-9_]{3,}')
def _utcnow(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def _historical_tokens(results_dir):
 out=set()
 for p in sorted(results_dir.glob('gate_btc_b3_h*_h*_result.json')):
  try:d=json.loads(p.read_text())
  except:continue
  for fam in d.get('families',[]):
   c=fam.get('contract') or fam
   for key in ('feature','direction','causal_standardization'):out.update(TOKEN_RE.findall(str(c.get(key,'')).upper()))
 return out
def _existing_channel_ids(existing_dir):
 ids=set()
 if not existing_dir or not existing_dir.exists():return ids
 for p in existing_dir.glob('*.json'):
  try:d=json.loads(p.read_text())
  except:continue
  ids.update(str(x['channel_id']) for x in d.get('proposals',[]) if x.get('channel_id'))
 return ids
def _openalex_search(query,per_page=8):
 r=requests.get(OPENALEX,params={'search':query,'per-page':per_page,'select':'id,doi,title,publication_year,primary_location'},timeout=20,headers={'User-Agent':'QRDS-research-only-grammar-scout/2.0'});r.raise_for_status();rows=[]
 for w in r.json().get('results',[]):
  src=(((w.get('primary_location') or {}).get('source') or {}).get('display_name'))
  rows.append({'openalex_id':w.get('id'),'doi':w.get('doi'),'title':w.get('title'),'publication_year':w.get('publication_year'),'source':src})
 return rows
def _relevant(row,ch):
 t=str(row.get('title') or '').lower(); cid=ch['channel_id'].lower();
 anchors={'b3','bovespa','brazil','brazilian','ibovespa','cvm','central bank','interest rate','futures','options','auction','securities lending','adr'}
 mechanism=set(re.findall(r'[a-z]{4,}',(ch['mechanism']+' '+cid).lower()))
 return bool(set(t.split())&anchors) and len(set(re.findall(r'[a-z]{4,}',t))&mechanism)>=1
def _mt5_status(path):
 if not path or not path.exists():return {'readiness':'MT5_UNAVAILABLE','available':False,'packet_sha256':None,'record_count':0}
 try:d=json.loads(path.read_text())
 except:return {'readiness':'MT5_UNAVAILABLE','available':False,'packet_sha256':None,'record_count':0}
 s=d.get('safety') or {};ok=s.get('MT5_READ_ONLY') is True and s.get('NO_ORDER_SEND') is True and s.get('ORDERS')==0 and s.get('REAL_CAPITAL')==0 and s.get('ENGINE_FEED') is False and d.get('primary_scientific_truth') is False and d.get('factory_economics_feedback_allowed') is False
 av=ok and d.get('readiness')=='READY_SHADOW_DATA_ONLY' and bool(d.get('factory_family_research_available'))
 return {'readiness':d.get('readiness') if ok else 'MT5_BOUNDARY_FAIL_CLOSED','available':av,'packet_sha256':d.get('packet_sha256') if ok else None,'record_count':int(d.get('record_count',0) or 0) if ok else 0}
def scout(results_dir,existing_dir=None,fetcher=_openalex_search,mt5_source_status=None):
 historical=_historical_tokens(results_dir);existing=_existing_channel_ids(existing_dir);mt5=_mt5_status(mt5_source_status); proposals=[]
 for ch in CHANNELS:
  evidence=[];errors=[]
  for q in ch['queries']:
   try:evidence.extend(fetcher(q))
   except Exception as exc:errors.append(f'{type(exc).__name__}:{exc}')
  seen=set();unique=[]
  for row in evidence:
   key=row.get('doi') or row.get('openalex_id') or row.get('title')
   if key and key not in seen and _relevant(row,ch):seen.add(key);unique.append(row)
  status='DUPLICATE_CHANNEL_SUPPRESSED' if ch['channel_id'] in existing else ('SCOUTED_NOT_PREREGISTERED' if unique else 'INSUFFICIENT_EXTERNAL_EVIDENCE_FAIL_CLOSED')
  overlap=sorted(set(TOKEN_RE.findall(ch['channel_id']))&historical); pid=hashlib.sha256((ch['channel_id']+'|'+'|'.join(sorted(str(x.get('doi') or x.get('openalex_id') or '') for x in unique))).encode()).hexdigest()[:16]
  proposals.append({'proposal_id':pid,'channel_id':ch['channel_id'],'status':status,'mechanism':ch['mechanism'],'required_new_data':ch['required_new_data'],'official_free_source_candidates':ch['official_free_source_candidates'],'auxiliary_mt5_source_available':mt5['available'],'auxiliary_mt5_packet_sha256':mt5['packet_sha256'],'auxiliary_mt5_record_count':mt5['record_count'],'mt5_is_primary_truth':False,'literature_evidence':unique[:12],'research_errors':errors,'historical_token_overlap':overlap,'historical_overlap_is_exclusion_input_not_performance_feedback':True,'requires_new_or_independent_unseen_data':True,'economics_read':False,'may_allocate_family_id':False,'may_change_existing_grammar':False,'may_test_threshold_grid':False})
 return {'schema':SCHEMA,'generated_at_utc':_utcnow(),'mode':'IDEATION_ONLY_NO_ECONOMICS','history_used_for':'DEDUPLICATION_AND_COVERAGE_ONLY','history_used_for_selection':False,'b3_adr_scope_required':True,'evaluation_data_policy':'FORWARD_OR_INDEPENDENT_UNSEEN_ONLY_AFTER_SEPARATE_PREREGISTRATION','root_cause_audit_dependency':'NONE_CAN_RUN_IN_PARALLEL','mt5_auxiliary_source':mt5,'mt5_unavailable_blocks_scout':False,'proposals':proposals,'safety':{'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'fail_closed':True,'h1_economics_read':False}}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--results-dir',required=True);ap.add_argument('--existing-dir');ap.add_argument('--mt5-source-status');ap.add_argument('--output',required=True);a=ap.parse_args();out=scout(Path(a.results_dir),Path(a.existing_dir) if a.existing_dir else None,mt5_source_status=Path(a.mt5_source_status) if a.mt5_source_status else None);Path(a.output).write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');return 0
if __name__=='__main__':raise SystemExit(main())
