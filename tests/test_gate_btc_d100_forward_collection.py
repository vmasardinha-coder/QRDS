import copy
import contextlib
import io
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tools.gate_btc_factory import d100_forward_collection as d


class PhysicalFeedTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / 'STATUS.json'
        self.now = datetime(2026, 9, 27, 15, 0, tzinfo=timezone.utc)
        self.policy = {'tracks': [{'track': 'D100', 'collect': True, 'evolve': False, 'state': 'DATA_FEED_ONLY'}]}
        self.payload = {'status': {'error_code': 0, 'timestamp': d.stamp(self.now)}, 'data': [
            {'id': n, 'rank': n, 'symbol': 'BTC' if n == 1 else 'X' + str(n),
             'slug': 'coin-' + str(n), 'status': 'active'} for n in range(1, 101)]}
        self.calls = []
        self.fail_candle = False

    def fetch(self, url):
        self.calls.append(url)
        if url == d.CMC_URL:
            result = self.payload
        elif 'public/instruments' in url:
            result = {'code': '0', 'data': [{'instId': 'BTC-USDT-SWAP', 'state': 'live',
                                             'settleCcy': 'USDT', 'ctType': 'linear'}]}
        elif 'market/candles' in url:
            if self.fail_candle:
                raise RuntimeError('fixture missing candles')
            ts = int((self.now.replace(hour=0) - timedelta(days=1)).timestamp() * 1000)
            result = {'code': '0', 'data': [[str(ts), '100', '110', '90', '105', '10', '10', '1000', '1']]}
        elif 'funding-rate-history' in url:
            result = {'code': '0', 'data': [{'instId': 'BTC-USDT-SWAP',
                       'fundingTime': str(int((self.now - timedelta(hours=1)).timestamp() * 1000)), 'fundingRate': '0.0001'}]}
        else:
            raise AssertionError('unexpected endpoint: ' + url)
        return json.dumps(result).encode()

    def run_feed(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return d.run(self.output, self.policy, fetch=self.fetch, clock=lambda: self.now, run_id='fixture')

    def status(self):
        return json.loads(self.output.read_text())

    def test_physical_archive_and_no_scientific_credit(self):
        self.assertEqual(self.run_feed(), 0)
        s = self.status()
        self.assertEqual(s['physical_snapshot_count'], 1)
        self.assertEqual(s['latest_raw_universe_count'], 100)
        self.assertEqual(s['latest_market_data_observed_count'], 1)
        self.assertEqual(s['scientific_observations_credited'], 0)
        self.assertIsNone(s['scientific_target'])
        self.assertFalse(s['economics_enabled'])
        records = d.verify_history(self.root)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['universe_available_at_utc'], d.stamp(self.now))

    def test_same_day_retry_neither_fetches_nor_increments(self):
        self.run_feed()
        files = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file() and p.suffix != '.md'}
        self.calls.clear()
        self.assertEqual(self.run_feed(), 0)
        self.assertEqual(self.calls, [])
        self.assertEqual(self.status()['physical_snapshot_count'], 1)
        for p, original in files.items():
            if p.name != 'STATUS.json':
                self.assertEqual(p.read_bytes(), original)

    def test_next_day_append_and_hash_chain(self):
        self.run_feed()
        old = d.verify_history(self.root)[0]
        self.now += timedelta(days=1)
        self.payload['status']['timestamp'] = d.stamp(self.now)
        self.run_feed()
        records = d.verify_history(self.root)
        self.assertEqual(records[1]['previous_record_sha256'], old['record_sha256'])
        self.assertEqual(self.status()['distinct_capture_days'], 2)
        self.assertEqual(self.status()['scientific_observations_credited'], 0)

    def test_missing_days_are_not_filled(self):
        self.run_feed()
        self.now += timedelta(days=4)
        self.payload['status']['timestamp'] = d.stamp(self.now)
        self.run_feed()
        self.assertEqual(self.status()['distinct_capture_days'], 2)
        self.assertEqual(len(d.verify_history(self.root)), 2)

    def test_stale_and_future_cmc_are_rejected(self):
        for hours in [-2, 1]:
            with self.subTest(hours=hours):
                payload = copy.deepcopy(self.payload)
                payload['status']['timestamp'] = d.stamp(self.now + timedelta(hours=hours))
                with self.assertRaises(ValueError):
                    d.top100(payload, self.now)

    def test_incomplete_duplicate_and_invalid_rank_universes_rejected(self):
        variants = []
        p = copy.deepcopy(self.payload); p['data'].pop(); variants.append(p)
        p = copy.deepcopy(self.payload); p['data'][1]['id'] = 1; variants.append(p)
        p = copy.deepcopy(self.payload); p['data'][1]['rank'] = 1; variants.append(p)
        p = copy.deepcopy(self.payload); p['data'][1]['rank'] = 101; variants.append(p)
        p = copy.deepcopy(self.payload); p['status']['error_code'] = 429; variants.append(p)
        for payload in variants:
            with self.assertRaises(ValueError):
                d.top100(payload, self.now)

    def test_ambiguous_ticker_is_not_silently_mapped(self):
        self.payload['data'][1]['symbol'] = 'BTC'
        _, coverage, _, errors = d.collect_sources(self.fetch, lambda: self.now)
        self.assertFalse(errors)
        self.assertEqual(coverage[0]['source_state'], 'AMBIGUOUS_OR_UNSUPPORTED_SYMBOL_NO_SUBSTITUTION')
        self.assertFalse(any('market/candles' in u for u in self.calls))

    def test_source_failure_is_visible_and_returns_nonzero(self):
        self.fail_candle = True
        self.assertEqual(self.run_feed(), 2)
        s = self.status()
        self.assertEqual(s['status'], 'PHYSICAL_DATA_FEED_SOURCE_FAILURE')
        self.assertEqual(s['latest_source_failure_count'], 1)
        self.assertEqual(s['successful_capture_days'], 0)
        self.assertEqual(len(d.verify_history(self.root)), 1)
        self.fail_candle = False
        self.now += timedelta(seconds=10)
        self.assertEqual(self.run_feed(), 0)
        self.assertEqual(self.status()['physical_snapshot_count'], 2)
        self.assertEqual(self.status()['distinct_capture_days'], 1)

    def test_universe_failure_preserves_last_good_evidence(self):
        self.run_feed()
        self.now += timedelta(days=1)
        self.assertEqual(self.run_feed(), 2)  # fixture source timestamp now stale
        self.assertEqual(self.status()['physical_snapshot_count'], 1)
        self.assertEqual(self.status()['last_attempt_result'], 'FAILED_NO_VALID_NEW_CAPTURE')

    def test_corrupt_archive_is_not_treated_as_successful_noop(self):
        self.run_feed()
        p = next((self.root / 'archives').glob('*.gz'))
        p.write_bytes(b'corrupted')
        with self.assertRaises(ValueError):
            self.run_feed()

    def test_corrupt_chain_is_rejected(self):
        self.run_feed()
        p = next((self.root / 'snapshots').glob('*.json'))
        obj = json.loads(p.read_text()); obj['sequence'] = 999
        p.write_text(json.dumps(obj))
        with self.assertRaises(ValueError):
            self.run_feed()

    def test_unexpected_scientific_counter_is_never_reset(self):
        self.output.write_text(json.dumps({'scientific_observations_credited': 3}))
        with self.assertRaises(ValueError):
            self.run_feed()
        self.assertEqual(self.status()['scientific_observations_credited'], 3)

    def test_missing_history_refuses_counter_reset(self):
        self.run_feed()
        next((self.root / 'snapshots').glob('*.json')).unlink()
        with self.assertRaises(ValueError):
            self.run_feed()

    def test_legacy_heartbeat_is_not_credited_as_a_capture(self):
        self.output.write_text(json.dumps({'status': 'ACTIVE_FORWARD_COLLECTION',
                                          'activation_date': '2026-09-05', 'scientific_observations_credited': 0}))
        self.run_feed()
        self.assertEqual(self.status()['first_physical_capture_at_utc'], d.stamp(self.now))
        self.assertEqual(self.status()['physical_snapshot_count'], 1)

    def test_wrong_authority_does_not_collect(self):
        self.policy['tracks'][0]['evolve'] = True
        with self.assertRaises(ValueError):
            self.run_feed()
        self.assertFalse(self.calls)

    def test_recovered_contract_bytes_match_original_seal(self):
        path = Path('tools/gate_btc_factory/d100_recovered/d100_prereg_contract_v1.json')
        self.assertEqual(d.sha(path.read_bytes()), '316600073946ccb217ed81797c23c3253f034509f94f926efb6198343af88052')
        contract = json.loads(path.read_text(encoding='utf-8-sig'))
        self.assertEqual(contract['activation_gate']['required_d50_paired_prospective_observations'], 30)
        self.assertTrue(contract['economic_engine_policy']['reuse_d50_logic_without_retuning'])

    def test_workflow_rethrows_collection_failure_after_publication(self):
        text = Path('.github/workflows/gate-btc-d100-forward-collection.yml').read_text()
        self.assertIn("steps.capture.outcome != 'success'", text)
        self.assertIn("D100_SOURCE_COLLECTION_FAILED", text)
        self.assertIn('git add runtime/ledgers/d100', text)
        self.assertNotIn('should_heartbeat', text)

    def test_report_separates_physical_capture_from_scientific_block(self):
        from tools.gate_btc_reporting_operational_overlay import enrich
        self.output = self.root / 'ledgers/d100/STATUS.json'
        self.run_feed()
        report = enrich(self.root, {'reference_data_date': '2026-09-27'})
        s = report['components']['d100']
        self.assertEqual(s['physical_snapshot_count'], 1)
        self.assertEqual(s['scientific_observations_credited'], 0)
        self.assertIsNone(s['scientific_target'])
        self.assertEqual(s['collection_health_hint'], 'AMBER_BLOCKED_DEPENDENCY')
        self.assertIn('d100', report['warnings']['blocked_dependency_components'])

    def test_report_exposes_source_failure_as_red(self):
        from tools.gate_btc_reporting_operational_overlay import enrich
        self.output = self.root / 'ledgers/d100/STATUS.json'
        self.fail_candle = True
        self.run_feed()
        report = enrich(self.root, {'reference_data_date': '2026-09-27'})
        self.assertEqual(report['components']['d100']['collection_health_hint'], 'RED_FAILED_DELIVERY')
        self.assertIn('d100', report['warnings']['failed_delivery_components'])


if __name__ == '__main__':
    unittest.main()
