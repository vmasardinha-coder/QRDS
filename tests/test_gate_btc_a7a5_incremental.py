import copy,json,tempfile,unittest,zipfile
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
from tools import gate_btc_a7a5_swap_history as a

def response(obj):return SimpleNamespace(status_code=200,content=json.dumps(obj).encode())
def events():
    with zipfile.ZipFile(a.SEED_PATH) as z:return json.loads(z.read('ALL_EVENTS.json'))

class LiveSession:
    def __init__(self,bad=None):
        self.bad=bad;self.posts=0;self.gets=0
        old=[x for x in events() if x['block_timestamp'][:10]<='2026-10-14'];self.all=old
        last=max((x for x in old if x['block_timestamp'][:10]=='2026-10-14'),key=a.key)
        fresh=[]
        for i in range(1,4):
            x=copy.deepcopy(last);x['block_number']+=1000*i;x['block_hash']='0x'+str(i)*64
            x['transaction_hash']='0x'+str(i+3)*64;x['block_timestamp']=f'2026-10-{14+i}T17:00:00.000000Z';fresh.append(x)
        self.live=list(reversed(fresh))+[copy.deepcopy(last)]
        if bad=='overlap':self.live[-1]['data']='0x'+'0'*256
        if bad=='gap':self.live=[x for x in self.live if x['block_timestamp'][:10]!='2026-10-16']
        self.all=old+fresh
        _,closes=a.aggregate(self.all,'2026-10-17');self.by_block={x['block_number']:x for x in closes};self.by_hash={x['block_hash']:x for x in closes}
    def get(self,url,timeout):
        self.gets+=1
        if '/tokens/' in url:
            with zipfile.ZipFile(a.SEED_PATH) as z:return response(json.loads(z.read('TOKEN0.json' if url.endswith(a.BASE) else 'TOKEN1.json')))
        return response({'items':self.live,'next_page_params':{'unused':'must not fetch'}})
    def post(self,url,json,timeout):
        self.posts+=1
        if isinstance(json,list):
            if self.bad=='batch_limit' and len(json)>2:return SimpleNamespace(status_code=500,content=b'batch too large')
            if self.bad=='always500':return SimpleNamespace(status_code=500,content=b'upstream unavailable')
            out=[self.one(x) for x in reversed(json)]
            if self.bad=='ids':out[0]['id']=out[-1]['id']
            if self.bad=='missing':out.pop()
            if self.bad=='rpc':out[0]={'id':out[0]['id'],'jsonrpc':'2.0','error':{'code':-1}}
            return response(out)
        return response(self.one(json))
    def one(self,request):
        method=request['method'];params=request['params']
        if method=='eth_chainId':value='0x1'
        elif method=='eth_call':value='0x'+'0'*24+(a.BASE if params[0]['data']=='0x0dfe1681' else a.QUOTE)[2:]
        elif method=='eth_getBlockByNumber':
            x=self.by_block[int(params[0],16)]
            value={'hash':x['block_hash'],'number':hex(x['block_number']),'timestamp':hex(int(datetime.fromisoformat(x['block_timestamp'].replace('Z','+00:00')).timestamp())),'transactions':[x['transaction_hash']]}
            if self.bad=='block':value['hash']='0xwrong'
        else:
            x=self.by_hash[params[0]['blockHash']]
            value=[{'removed':False,'address':a.POOL,'blockNumber':hex(x['block_number']),'blockHash':x['block_hash'],'transactionHash':x['transaction_hash'],'logIndex':hex(x['index']),'data':x['data'],'topics':[t for t in x['topics'] if t]}]
            if self.bad=='log':value[0]['data']='0xwrong'
        return {'jsonrpc':'2.0','id':request['id'],'result':value}

class IncrementalTests(unittest.TestCase):
    def run_capture(self,session,d):return a.collect(session,'2026-10-17',d,datetime(2026,10,18,tzinfo=timezone.utc))
    def test_all_200_closes_reverified_with_out_of_order_batch_responses(self):
        with tempfile.TemporaryDirectory() as d:
            session=LiveSession();rows,e=self.run_capture(session,d)
            self.assertEqual(len(rows),200);self.assertEqual(rows[-1]['date'],'2026-10-17')
            self.assertEqual(session.gets,3);self.assertEqual(session.posts,43)
            self.assertTrue(e['pinned_physical_seed_reused']);self.assertTrue(e['all_200_closing_blocks_and_logs_reverified_live'])
            self.assertEqual(e['canonical_closing_blocks_and_logs_verified'],200)
            self.assertEqual(e['historical_scientific_credit'],0)
    def test_bad_seed_hash_cannot_fall_back_silently(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.zip';p.write_bytes(b'changed')
            session=LiveSession()
            with patch.object(a,'SEED_PATH',p),self.assertRaisesRegex(ValueError,'SEED_ARCHIVE_HASH'):self.run_capture(session,d)
    def test_missing_or_changed_overlap_rejected(self):
        seed,_=a.seed_events(a.SEED_PATH)
        with self.assertRaisesRegex(ValueError,'OVERLAP_REQUIRED'):a.join_seed([],seed)
        with tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(ValueError,'OVERLAP_MISMATCH'):self.run_capture(LiveSession('overlap'),d)
    def test_missing_physical_day_not_filled(self):
        with tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(ValueError,'MISSING_200_PHYSICAL'):self.run_capture(LiveSession('gap'),d)
    def test_duplicate_missing_ids_or_rpc_error_rejected(self):
        for bad in ['ids','missing','rpc']:
            with self.subTest(bad=bad),tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(ValueError,'RPC_BATCH'):self.run_capture(LiveSession(bad),d)
    def test_seed_never_bypasses_fresh_canonical_proof(self):
        for bad in ['block','log']:
            with self.subTest(bad=bad),tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(ValueError,'CANONICAL_CLOSING'):self.run_capture(LiveSession(bad),d)
    def test_http500_batch_is_split_without_skipping_any_closing_proof(self):
        with tempfile.TemporaryDirectory() as d:
            rows,e=self.run_capture(LiveSession('batch_limit'),d)
            self.assertEqual(len(rows),200);self.assertEqual(e['canonical_closing_blocks_and_logs_verified'],200)
            self.assertTrue(any(x.get('http_status')==500 for x in e['raw_manifest']))
    def test_http500_at_smallest_batch_fails_closed(self):
        with tempfile.TemporaryDirectory() as d,self.assertRaisesRegex(ValueError,'A7A5_SOURCE_HTTP_500'):self.run_capture(LiveSession('always500'),d)

if __name__=='__main__':unittest.main()
