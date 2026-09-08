from tools.gate_btc_factory.b3_v3_physical_archive_extent_probe import execute

class Raw:
    def __init__(self,b): self.b=b
    def read(self,n,decode_content=True): return self.b[:n]
class Resp:
    def __init__(self,positive=False):
        self.status_code=200; self.raw=Raw(b'PK\x03\x04' if positive else b'')
        self.headers={'content-type':'application/octet-stream','content-length':'4' if positive else '0'}
        if positive: self.headers['content-disposition']='attachment; filename=X_NEGOCIOSAVISTA_DRV.zip'
    def __enter__(self): return self
    def __exit__(self,*a): return False
class Session:
    def get(self,url,**kw): return Resp('2022-12-16' in url)

def prereg():
    return {
      'schema':'gate_btc.b3.v3.physical_archive_extent_prereg.v1','created_at_utc':'x','generation':'H2730-H2739',
      'frozen_probe_dates':['2020-12-18','2021-12-17','2022-12-16','2023-12-15','2024-12-20'],
      'adjudication_rules':{'all_five_years_positive':'ALL','some_years_positive':'SOME','no_years_positive':'NONE'},
      'safety':{'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_BACKFILL':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True,'H1_ECONOMICS_READ':False}}

def test_partial_transport_never_grants_credit():
    d=execute(Session(),prereg())
    assert d['positive_transport_dates']==['2022-12-16']
    assert d['adjudication']=='SOME'
    assert d['source_gate_green'] is False and d['source_gate_credit']==0
    assert d['economics_read'] is False and d['data_gap_definitive'] is False
    assert d['safety']['FAIL_CLOSED'] is True and d['safety']['ORDERS']==0
