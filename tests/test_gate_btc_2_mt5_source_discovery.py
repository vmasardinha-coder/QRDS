from tools.gate_btc_2_mt5_source_discovery import build

def packet(ready=True):
    return {'generated_at_utc':'2026-08-31T15:00:00Z','packet_sha256':'p','record_count':5,'readiness':'READY_SHADOW_DATA_ONLY' if ready else 'MT5_UNAVAILABLE_OR_NO_FRESH_DATA','primary_scientific_truth':False,'factory_economics_feedback_allowed':False,'safety':{'MT5_READ_ONLY':True,'NO_ORDER_SEND':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_BACKFILL':True,'NO_RETUNE':True,'H1_ECONOMICS_READ':False}}
def candidate(): return {'source_packet_sha256':'p','candidate_sha256':'c','status':'AVAILABLE_FOR_SOURCE_DISCOVERY_ONLY'}
def test_ready_is_candidate_only():
    x=build(packet(),candidate()); assert x['status']=='AVAILABLE_SOURCE_CANDIDATE'; assert x['source_admission_pass'] is False; assert x['blocks_other_sources'] is False; assert x['prospective_credit']==0 and x['scientific_promotion_credit']==0 and x['historical_backfill_credit']==0; assert x['economics_feedback_allowed'] is False
def test_offline_does_not_block_other_sources():
    x=build(packet(False),candidate()); assert x['status']=='MT5_UNAVAILABLE_FAIL_OPEN_TO_OTHER_SOURCES'; assert x['record_count']==0; assert x['blocks_other_sources'] is False
