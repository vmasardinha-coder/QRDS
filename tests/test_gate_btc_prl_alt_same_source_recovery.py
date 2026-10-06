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

if __name__=='__main__':unittest.main()
