import csv
import gzip
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tools import gate_btc_prl_alt_same_source_recovery as recovery

class CurrentSignalRecoveryTests(unittest.TestCase):
    def test_new_epoch_uses_qualified_archive_with_exact_overlap(self):
        day=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            qos=root/'qos'
            older=qos/'cycles'/'2026-09-30'
            older.mkdir(parents=True)
            (older/'SIGNAL_STATE.json').write_text('{}')
            (older/'BLOCKED.json').write_text('{}')
            cycle=qos/'cycles'/day
            cycle.mkdir(parents=True)
            state={'state_sha256':'frozen-signal','candidate_symbols':['AR'],
                   'candidate_source_lock':{'AR':'binance_spot_daily_archive'},
                   'qos_picks':{'QOS_Moderada':['AR'],'QOS_Ultra':['AR']},
                   'source_epoch':{'source_lock':'binance_spot_daily_archive',
                                   'remapped_symbols':['AR']}}
            (cycle/'SIGNAL_STATE.json').write_text(json.dumps(state))
            evidence=qos/'source_evidence'/day/day
            evidence.mkdir(parents=True)
            raw=gzip.compress(b'{}')
            (evidence/'RAW_SOURCES.json.gz').write_bytes(raw)
            manifest={'cutoff':day,'signal_state_sha256':'frozen-signal',
                      'raw_sha256':recovery.sha(raw),'missing_candidates':[],
                      'source_substitution':False,'research_only':True,
                      'orders_generated':0,
                      'quotes':[{'symbol':'AR','date':day,'close_usd':100.,
                                 'source':'binance_spot_daily_archive'}]}
            manifest['manifest_sha256']=recovery.sha(recovery.packed(manifest))
            (evidence/'PRICES.json').write_text(json.dumps(manifest))
            master=root/'master.csv'
            master.write_text('date,symbol,close_usd,source\n'+day+',AR,100,cdd\n')
            out=root/'out.csv'
            result=recovery.recover(master,qos,day,out,root/'receipt.json')
            self.assertEqual(result['qos_signal_date'],day)
            self.assertEqual(result['qualified_new_epoch_transport'],['AR'])
            with out.open(newline='') as handle:
                row=next(csv.DictReader(handle))
            self.assertEqual(row['source'],'binance_spot_daily_archive')
            self.assertEqual(row['close_usd'],'100.0')



import csv
import gzip
import hashlib
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
import tempfile
import unittest

from tools import gate_btc_prl_alt_same_source_recovery as recovery


class AltRolloverRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.day=(datetime.now(timezone.utc).date()-timedelta(days=1)).isoformat()
        self.previous=(datetime.fromisoformat(self.day).date()-timedelta(days=1)).isoformat()
        self.qos=self.root/'qos';cycle=self.qos/'cycles'/self.day;cycle.mkdir(parents=True)
        state=dict(state_sha256='signal',candidate_symbols=['AR','STX'],
                   candidate_source_lock={'AR':'cdd','STX':'cdd'},
                   qos_picks={'QOS_Moderada':['AR'],'QOS_Ultra':['AR']})
        (cycle/'SIGNAL_STATE.json').write_text(json.dumps(state))
        self.evidence=self.qos/'source_evidence'/self.day/self.day;self.evidence.mkdir(parents=True)
        raw=gzip.compress(b'{}');(self.evidence/'RAW_SOURCES.json.gz').write_bytes(raw)
        self.manifest=dict(cutoff=self.day,signal_state_sha256='signal',raw_sha256=recovery.sha(raw),
                           source_substitution=False,research_only=True,orders_generated=0,
                           quotes=[dict(symbol=s,date=self.day,close_usd=p,source='cdd')
                                   for s,p in [('AR',100.),('STX',.3259)]])
        self.save_manifest()
        self.master=self.root/'master.csv';self.master.write_text('date,symbol,close_usd,source\n'+self.day+',AR,100,cdd\n')
        self.consumer=self.root/'alt';epoch=self.consumer/'epochs/monthly_20261031'
        (epoch/'snapshots').mkdir(parents=True)
        row=dict(snapshot_date=self.previous,signals={s:dict(picks=[dict(asset='STX',weight=.1),dict(asset='BTC',weight=.1)])
                 for s in ['QOS_Moderada','QOS_Ultra']},rollover_exit_assets=[],research_only=True,
                 shadow_only=True,not_approved=True,engine_feed=False,orders_generated=0,real_capital_used=0)
        digest=hashlib.sha256(json.dumps(row,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        row['row_sha256']=digest
        self.row_path=epoch/'snapshots'/f'{self.previous}.json';self.row_path.write_text(json.dumps(row))
        (epoch/'STATUS.json').write_text(json.dumps(dict(latest_snapshot_date=self.previous,latest_row_sha256=digest)))
        (self.consumer/'STATUS.json').write_text(json.dumps(dict(schema='gate_btc.prl_alt_next_epoch_status.v1',
             authorization_id='ALT_TRAIL40_10_20261031_USER_20261006',current_epoch='monthly_20261031',latest_snapshot_date=self.previous)))
        self.out=self.root/'out.csv';self.receipt=self.root/'receipt.json'

    def save_manifest(self):
        m=dict(self.manifest);m['manifest_sha256']=recovery.sha(recovery.packed(m))
        (self.evidence/'PRICES.json').write_text(json.dumps(m))

    def test_sealed_non_qos_pick_supplies_exact_rollover_exit(self):
        before=self.row_path.read_bytes()
        result=recovery.recover(self.master,self.qos,self.day,self.out,self.receipt,self.consumer)
        self.assertEqual(result['added_symbols'],['STX'])
        self.assertEqual(result['required_rollover_symbols'],['STX'])
        self.assertFalse(result['source_substitution'])
        self.assertEqual(result['scientific_credit_added'],0)
        with self.out.open() as handle:
            rows=list(csv.DictReader(handle))
        self.assertEqual(next(r for r in rows if r['symbol']=='STX')['close_usd'],'0.3259')
        self.assertEqual(before,self.row_path.read_bytes())

    def test_missing_sealed_rollover_price_is_not_fabricated(self):
        self.manifest['quotes']=self.manifest['quotes'][:1];self.save_manifest()
        with self.assertRaisesRegex(ValueError,'COVERAGE_MISSING'):
            recovery.recover(self.master,self.qos,self.day,self.out,self.receipt,self.consumer)
        self.assertFalse(self.out.exists())

    def test_wrong_source_is_not_accepted_for_rollover(self):
        self.manifest['quotes'][1]['source']='different-venue';self.save_manifest()
        with self.assertRaisesRegex(ValueError,'LOCKED_SOURCE'):
            recovery.recover(self.master,self.qos,self.day,self.out,self.receipt,self.consumer)

    def test_tampered_consumer_cannot_expand_recovery_scope(self):
        row=json.loads(self.row_path.read_text());row['signals']['QOS_Ultra']['picks'].append(dict(asset='EVIL',weight=.1))
        self.row_path.write_text(json.dumps(row))
        with self.assertRaisesRegex(ValueError,'CONSUMER_HASH'):
            recovery.recover(self.master,self.qos,self.day,self.out,self.receipt,self.consumer)

    def test_existing_conflicting_price_remains_fail_closed(self):
        self.master.write_text(self.master.read_text()+self.day+',STX,99,cdd\n')
        with self.assertRaisesRegex(ValueError,'PRICE_CONFLICT'):
            recovery.recover(self.master,self.qos,self.day,self.out,self.receipt,self.consumer)

    def test_default_prl_recovery_scope_remains_frozen_qos_picks(self):
        result=recovery.recover(self.master,self.qos,self.day,self.out,self.receipt)
        self.assertEqual(result['added_symbols'],[])
        self.assertNotIn('STX',self.out.read_text())

    def test_existing_alt_receipt_path_binds_the_consumer_without_workflow_change(self):
        target=self.root/'alt_trail40_10'
        self.consumer.rename(target);self.consumer=target
        receipt=target/'source_evidence'/f'{self.day}.json'
        result=recovery.recover(self.master,self.qos,self.day,self.out,receipt)
        self.assertEqual(result['added_symbols'],['STX'])
        self.assertEqual(result['required_rollover_symbols'],['STX'])


if __name__=='__main__':unittest.main()
