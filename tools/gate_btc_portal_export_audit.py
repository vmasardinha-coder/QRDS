"""Audit the original Portal export without rewriting NAVs or filling gaps."""
import argparse,hashlib,json,math
from datetime import date
from pathlib import Path

KEYS=['A_100','A_300','B_100','B_300','C_100','C_300','D_100','D_300',
      'G_100','G_300','G_COMBINED','G7_100','G7_300','GR7C_100','GR7D_100','GR7F_100',
      'GR7C_300','GR7D_300','GR7F_300','H_100','I_100','I_300','watchlist']
def close(a,b,tol=.001):
 return math.isfinite(float(a)) and math.isfinite(float(b)) and abs(float(a)-float(b))<=tol

def ledger_audit(rows):
 if not rows:raise ValueError('EMPTY_LEDGER')
 gaps=[]
 for i,r in enumerate(rows):
  if not math.isfinite(r['navMarkToMarket']) or r['navMarkToMarket']<=0:raise ValueError('INVALID_NAV')
  if not i:continue
  old=rows[i-1];days=(date.fromisoformat(r['data'])-date.fromisoformat(old['data'])).days
  if days<=0:raise ValueError('DUPLICATE_OR_UNSORTED_DATE')
  value=100*(r['navMarkToMarket']/old['navMarkToMarket']-1)
  if not close(value,r['retornoDia']):raise ValueError('INTERVAL_RETURN_MISMATCH:'+r['data'])
  if days!=1:gaps.append(dict(start=old['data'],end=r['data'],missing_days=days-1))
 return gaps

def snapshot_comparison(summary,rows):
 ref=summary['benchmarkBtc'].get('referenciaPareadaSnapshot',{}).get('janelaLedger',{})
 gross=100*(rows[-1]['navMarkToMarket']/rows[0]['navMarkToMarket']-1)
 if not ref:return dict(status='SNAPSHOT_BTC_UNAVAILABLE',gross_ledger_pct=gross)
 start,end=ref.get('precoInicio'),ref.get('precoFim')
 if not isinstance(start,(float,int)) or not isinstance(end,(float,int)) or start<=0 or end<=0:raise ValueError('INVALID_SNAPSHOT_BTC_PRICE')
 btc=100*(end/start-1)
 if not close(btc,ref['btcPct'],.011):raise ValueError('SNAPSHOT_BTC_RETURN_MISMATCH')
 exact=ref['diaInicio']==rows[0]['data'] and ref['diaFim']==rows[-1]['data']
 return dict(status='SAME_DATES_SNAPSHOT_REFERENCE' if exact else 'SNAPSHOT_START_DIFFERS_FROM_LEDGER',
             strategy_start=rows[0]['data'],strategy_end=rows[-1]['data'],btc_start=ref['diaInicio'],btc_end=ref['diaFim'],
             gross_ledger_pct=gross,btc_snapshot_pct=btc,
             difference_snapshot_pp=gross-btc if exact else None,
             reference_only_difference_pp=gross-btc,
             timing_note='Provider snapshot reference; exact execution timestamps and fills are not established.')

def audit(raw):
 d=json.loads(raw);summaries=d['resumoLedger']
 if len(summaries)!=len(KEYS):raise ValueError('UNEXPECTED_PORTAL_BOOK_SET')
 views=[];count=0;gap_count=0
 for key,s in zip(KEYS,summaries):
  rows=d['dados']['ledger_diario_'+key+'_v1']['registros'];gaps=ledger_audit(rows)
  count+=len(rows);gap_count+=len(gaps)
  if s['diasDeHistoricoNoLedger']!=len(rows) or s['dataUltimaAtualizacao']!=rows[-1]['data']:raise ValueError('SUMMARY_CUTOFF_OR_COUNT_MISMATCH')
  if not close(s['navAtual'],rows[-1]['navMarkToMarket'],1e-6):raise ValueError('SUMMARY_NAV_MISMATCH')
  gross=100*(rows[-1]['navMarkToMarket']/rows[0]['navMarkToMarket']-1)
  if not close(gross,s['retornoAcumuladoJanelaLedgerPct'],.011):raise ValueError('SUMMARY_WINDOW_RETURN_MISMATCH')
  compare=snapshot_comparison(s,rows)
  views.append(dict(key=key,name=s['estrategia'],cutoff=rows[-1]['data'],rows=len(rows),gaps=gaps,comparison=compare,
                    utc_reference=s['janelas']['janelaLedger'],costs=s['custos']))
 by={k:{r['data']:r for r in d['dados']['ledger_diario_'+k+'_v1']['registros']} for k in ('G_100','G_300','G_COMBINED')}
 for day,r in by['G_COMBINED'].items():
  if not all(day in by[k] for k in ('G_100','G_300')):raise ValueError('COMBINED_COMPONENT_DATE_MISSING')
  value=(by['G_100'][day]['navMarkToMarket']+by['G_300'][day]['navMarkToMarket'])/2
  if not close(value,r['navMarkToMarket'],1e-6):raise ValueError('COMBINED_NAV_MISMATCH')
 declared=d['integridadeLedger']
 if declared['ledgersVerificados']!=len(views) or declared['registrosVerificados']!=count:raise ValueError('DECLARED_AUDIT_COUNT_MISMATCH')
 return dict(schema='gate_btc.portal_export_audit.v1',status='PASS',source_sha256=hashlib.sha256(raw).hexdigest(),
             exported_at=d['geradoEm'],books=len(views),rows=count,interval_returns_verified=True,combined_nav_verified=True,
             gaps=gap_count,snapshot_same_date_books=sum(v['comparison']['status']=='SAME_DATES_SNAPSHOT_REFERENCE' for v in views),
             snapshot_different_start_books=sum(v['comparison']['status']=='SNAPSHOT_START_DIFFERS_FROM_LEDGER' for v in views),
             source_unchanged=True,estimated_missing_rows=0,orders=0,real_capital=0,views=views)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 result=audit(a.source.read_bytes());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k!='views'}))
