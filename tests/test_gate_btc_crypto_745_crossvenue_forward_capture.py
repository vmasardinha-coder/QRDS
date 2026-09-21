import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

PATH=Path('tools/gate_btc_factory/crypto_745_crossvenue_forward_capture.py')
spec=importlib.util.spec_from_file_location('cv',PATH)
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


def ev(ts, price='100'):
    return {'ts_ms':ts,'price':price,'trade_id':str(ts)}


def admission(path):
    obj={
        'outcomes_read':False,'economics_read':False,'evidence_sha256':'abc123',
        'channels':[{'channel_id':c.CHANNEL_ID,'adjudication_decision':'SOURCE_COST_QUALIFIED'}]
    }
    Path(path).write_text(json.dumps(obj))


def iso(ms):
    return datetime.fromtimestamp(ms/1000, tz=timezone.utc).isoformat().replace('+00:00','Z')


class FakeClock:
    def __init__(self, seconds): self.t=float(seconds)
    def now(self): return self.t
    def sleep(self, seconds): self.t += max(0.0, float(seconds))


class FakePoll:
    def __init__(self, clock, boundary_ms):
        self.clock=clock; self.boundary_ms=boundary_ms; self.n=0
    def __call__(self):
        self.n += 1
        now_ms=int(self.clock.now()*1000)
        # The close events do not exist in any response before they occur.
        okx=[]; cb=[]
        if now_ms >= self.boundary_ms-1200:
            okx.append({'instId':'BTC-USDT-SWAP','ts':str(self.boundary_ms-900),'px':'100','tradeId':'okx-close'})
            cb.append({'time':iso(self.boundary_ms-800),'price':'100','trade_id':101})
        if now_ms >= self.boundary_ms+5200:
            okx.append({'instId':'BTC-USDT-SWAP','ts':str(self.boundary_ms+5100),'px':'101','tradeId':'okx-entry'})
        okx_obj={'code':'0','data':okx}
        return (json.dumps(okx_obj).encode(),okx_obj),(json.dumps(cb).encode(),cb)


class CrossVenueForwardTests(unittest.TestCase):
    def test_select_close_requires_five_second_freshness(self):
        xs=[ev(94000),ev(97000),ev(99900)]
        self.assertEqual(c.select_last_at_or_before(xs,100000)['ts_ms'],99900)
        self.assertIsNone(c.select_last_at_or_before([ev(94999)],100000))

    def test_select_entry_requires_five_second_delay(self):
        xs=[ev(104999),ev(105100),ev(109900)]
        self.assertEqual(c.select_first_at_or_after(xs,105000)['ts_ms'],105100)
        self.assertIsNone(c.select_first_at_or_after([ev(110001)],105000))

    def test_live_buffer_opens_before_boundary_and_retains_close(self):
        boundary_ms=120000
        clock=FakeClock((boundary_ms/1000)-8)
        packet=c.collect_live_boundary_packet(
            boundary_ms,poll_seconds=1.0,now_fn=clock.now,sleep_fn=clock.sleep,
            poll_fn=FakePoll(clock,boundary_ms),
        )
        self.assertEqual(packet['capture_mode'],'LIVE_PREBOUNDARY_BUFFER_ONLY')
        self.assertFalse(packet['history_endpoint_used'])
        self.assertEqual(packet['execution_close']['ts_ms'],boundary_ms-900)
        self.assertEqual(packet['source_close']['ts_ms'],boundary_ms-800)
        self.assertEqual(packet['entry']['ts_ms'],boundary_ms+5100)
        self.assertLessEqual(packet['window_start_ms'],boundary_ms-5000)
        self.assertTrue(packet['execution_close']['first_seen_receipt_ms'] >= packet['window_start_ms'])

    def test_missed_prebuffer_fails_closed_instead_of_reconstruction(self):
        boundary_ms=120000
        clock=FakeClock((boundary_ms/1000)-5)
        with self.assertRaisesRegex(RuntimeError,'LIVE_PREBUFFER_MISSED_FAIL_CLOSED'):
            c.collect_live_boundary_packet(
                boundary_ms,now_fn=clock.now,sleep_fn=clock.sleep,
                poll_fn=FakePoll(clock,boundary_ms),
            )

    def test_future_boundary_skips_minute_if_prebuffer_cannot_be_opened(self):
        self.assertEqual(c.choose_first_future_boundary(100.0),120)
        self.assertEqual(c.choose_first_future_boundary(114.5),180)

    def test_pending_and_finalize_do_not_compute_economics(self):
        prev={'boundary_ms':60000,'source_close':ev(59900),'execution_close':ev(59800)}
        cur={
            'boundary_ms':120000,'decision_ms':125000,
            'source_close':ev(119900),'execution_close':ev(119800),'entry':ev(125100),
        }
        pending=c.pending_from(prev,cur)
        self.assertEqual(pending['exit_target_ms'],185100)
        nxt={'okx_events':[ev(185200)]}
        out=c.finalize_pending(pending,nxt)
        self.assertTrue(out['eligible_for_future_evaluation'])
        self.assertNotIn('return',out)
        self.assertNotIn('pnl',out)

    def test_source_cost_admission_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'a.json'
            p.write_text(json.dumps({'outcomes_read':False,'economics_read':False,'evidence_sha256':'x','channels':[]}))
            with self.assertRaisesRegex(RuntimeError,'SOURCE_COST_NOT_QUALIFIED'):
                c.qualified_source_cost(p)

    def test_manifest_keeps_v1_zero_credit_and_accepts_v2_without_history(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            old={
                'schema':'qrds.factory.crypto_745_crossvenue_forward_partition.v1',
                'channel_id':c.CHANNEL_ID,'economics_read':False,
                'source_cost_evidence_sha256':'abc123','eligible_observation_count':0,
                'observations':[{'observation_id':'60000','eligible_for_future_evaluation':False}],
            }
            new={
                'schema':'qrds.factory.crypto_745_crossvenue_forward_partition.v2',
                'channel_id':c.CHANNEL_ID,'economics_read':False,'history_endpoint_used':False,
                'source_cost_evidence_sha256':'abc123','eligible_observation_count':1,
                'observations':[{'observation_id':'120000','eligible_for_future_evaluation':True}],
            }
            (root/'old.json').write_text(json.dumps(old))
            (root/'new.json').write_text(json.dumps(new))
            m=c.build_manifest(root)
            self.assertEqual(m['partition_count'],2)
            self.assertEqual(m['eligible_unique_observation_count'],1)
            self.assertFalse(m['checkpoint_ready_for_dataset_binding'])
            self.assertFalse(m['economics_read_allowed'])

    def test_manifest_rejects_v2_history_repair(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            bad={
                'schema':'qrds.factory.crypto_745_crossvenue_forward_partition.v2',
                'channel_id':c.CHANNEL_ID,'economics_read':False,'history_endpoint_used':True,
                'source_cost_evidence_sha256':'abc123','eligible_observation_count':0,'observations':[],
            }
            (root/'bad.json').write_text(json.dumps(bad))
            with self.assertRaisesRegex(RuntimeError,'HISTORY_REPAIR_PROHIBITED'):
                c.build_manifest(root)

    def test_permanent_safety_locks(self):
        self.assertTrue(c.SAFETY['RESEARCH_ONLY'])
        self.assertTrue(c.SAFETY['SHADOW_ONLY'])
        self.assertTrue(c.SAFETY['NOT_APPROVED'])
        self.assertFalse(c.SAFETY['ENGINE_FEED'])
        self.assertEqual(c.SAFETY['ORDERS'],0)
        self.assertEqual(c.SAFETY['REAL_CAPITAL'],0)
        self.assertTrue(c.SAFETY['NO_BACKFILL'])
        self.assertTrue(c.SAFETY['NO_LATE_SEAL'])
        self.assertTrue(c.SAFETY['NO_COUNTER_RESET'])
        self.assertTrue(c.SAFETY['NO_RETUNE'])
        self.assertTrue(c.SAFETY['FAIL_CLOSED'])

if __name__=='__main__':unittest.main()
