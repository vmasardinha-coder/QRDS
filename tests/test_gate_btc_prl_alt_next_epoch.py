import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tools import gate_btc_prl_alt_next_epoch as next_epoch

class NextEpochTests(unittest.TestCase):
    def test_old_epoch_is_intact_and_next_month_is_separate(self):
        for lane in ('prl50','alt'):
            with self.subTest(lane=lane),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)
                old=root/'epochs/monthly_20260930'
                (old/'snapshots').mkdir(parents=True)
                (old/'ANCHOR.json').write_text('{}')
                prior=old/'snapshots/2026-10-04.json'
                prior.write_text('{}')
                bytes_before=prior.read_bytes()
                wait=next_epoch.plan(root,lane,datetime(2026,10,7,12,tzinfo=timezone.utc))
                self.assertEqual(wait['status'],'WAITING_NEXT_APPROVED_MONTH_END')
                self.assertFalse(wait['can_append'])
                self.assertEqual(wait['interrupted_epoch_snapshot_count'],1)
                self.assertEqual(prior.read_bytes(),bytes_before)
                self.assertEqual(next_epoch.plan(root,lane,datetime(2026,10,7,12,tzinfo=timezone.utc))['status'],
                                 'WAITING_NEXT_APPROVED_MONTH_END')
                ready=next_epoch.plan(root,lane,datetime(2026,11,1,12,tzinfo=timezone.utc))
                self.assertEqual(ready['status'],'NEEDS_CURRENT_SOURCE')
                self.assertEqual(ready['next_required_cutoff'],'2026-10-31')
                self.assertEqual(ready['current_epoch_snapshot_count'],0)
                self.assertEqual(prior.read_bytes(),bytes_before)
                self.assertTrue((root/'epochs/monthly_20261031/ANCHOR.json').exists())
                self.assertEqual(next_epoch.config(lane)[2].load_json(old/'PRESERVED_GAP.json')['economic_credit'],0)

class DeliveryFailureTests(unittest.TestCase):
    def test_preserved_snapshot_keys_are_portable_across_windows_and_linux(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);old=root/'epochs/monthly_20260930'
            (old/'snapshots').mkdir(parents=True);(old/'ANCHOR.json').write_text('{}')
            (old/'snapshots/2026-10-04.json').write_text('{}')
            next_epoch.plan(root,'alt',datetime(2026,11,1,12,tzinfo=timezone.utc))
            marker=next_epoch.alt.load_json(old/'PRESERVED_GAP.json')
            self.assertEqual(set(marker['preserved_files_sha256']),
                             {'ANCHOR.json','snapshots/2026-10-04.json'})

    def test_failure_preserves_snapshots_and_retry_plan(self):
        for lane in ('prl50','alt'):
            with self.subTest(lane=lane),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);old=root/'epochs/monthly_20260930'
                (old/'snapshots').mkdir(parents=True)
                (old/'ANCHOR.json').write_text('{}')
                previous=old/'snapshots/2026-10-04.json';previous.write_text('{}')
                at=datetime(2026,11,1,12,tzinfo=timezone.utc)
                next_epoch.plan(root,lane,at)
                before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('snapshots/*.json')}
                failed=next_epoch.failure(root,lane,at)
                self.assertEqual(failed['status'],'FAILED_CURRENT_SOURCE_RETRYABLE')
                self.assertEqual(failed['current_epoch_snapshot_count'],0)
                self.assertFalse(failed['economic_result_valid'])
                self.assertEqual(failed['orders_generated'],0)
                self.assertEqual(before,{str(p.relative_to(root)):p.read_bytes() for p in root.rglob('snapshots/*.json')})
                retry=next_epoch.plan(root,lane,at)
                self.assertEqual(retry['status'],'NEEDS_CURRENT_SOURCE')
                self.assertEqual(retry['next_required_cutoff'],'2026-10-31')

    def test_failure_does_not_replace_calendar_wait(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);old=root/'epochs/monthly_20260930'
            (old/'snapshots').mkdir(parents=True);(old/'ANCHOR.json').write_text('{}')
            (old/'snapshots/2026-10-04.json').write_text('{}')
            state=next_epoch.failure(root,'alt',datetime(2026,10,7,12,tzinfo=timezone.utc))
            self.assertEqual(state['status'],'WAITING_NEXT_APPROVED_MONTH_END')



class AltMonthlyCalendarTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        old = self.root / 'epochs/monthly_20260930'
        (old / 'snapshots').mkdir(parents=True)
        (old / 'ANCHOR.json').write_text('{}')
        (old / 'snapshots/2026-10-04.json').write_text('{}')
        self.epoch = self.root / 'epochs/monthly_20261031'
        self.port = self.root / 'port.csv'
        self.master = self.root / 'master.csv'
        self.contract, _, self.archive = next_epoch.config('alt')

    @staticmethod
    def write_csv(path, rows):
        with path.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def inputs(self, signal, execution, asset, closes):
        self.write_csv(self.port, [
            dict(strategy=s, data_as_of=signal, execution_eligible_from=execution,
                 signal_period=signal[:7], regime='RISK_ON', asset=asset, weight='0.3')
            for s in self.archive.STRATEGIES
        ])
        self.write_csv(self.master, [
            dict(date=day, symbol=symbol, close_usd=price) for day, symbol, price in closes
        ])

    def run_day(self, day, clock):
        return next_epoch.process(self.root, 'alt', self.port, self.master, day, '42',
                                  datetime.fromisoformat(clock + 'T12:00:00+00:00'))

    def first(self):
        self.inputs('2026-10-31', '2026-11-01', 'AKE', [('2026-10-31', 'AKE', 100)])
        self.run_day('2026-10-31', '2026-11-01')

    def test_observed_daily_change_does_not_release_frozen_ake(self):
        self.first()
        self.inputs('2026-11-01', '2026-11-02', 'SOL', [('2026-11-01', 'SOL', 100)])
        with self.assertRaisesRegex(RuntimeError, 'missing exact snapshot prices:.*AKE'):
            self.run_day('2026-11-01', '2026-11-02')
        self.assertFalse((self.epoch / 'snapshots/2026-11-01.json').exists())
        self.inputs('2026-11-01', '2026-11-02', 'SOL', [('2026-11-01', 'AKE', 105)])
        result = self.run_day('2026-11-01', '2026-11-02')
        row = self.archive.load_json(self.epoch / 'snapshots/2026-11-01.json')
        self.assertEqual(row['signals']['QOS_Moderada']['signal_date'], '2026-10-31')
        self.assertEqual(row['observed_signals']['QOS_Moderada']['signal_date'], '2026-11-01')
        self.assertEqual(row['selected_alt_closes'], {'AKE': 105})
        self.assertFalse(result['delivery']['economic_result_valid'])
        self.assertEqual(self.archive.load_json(self.epoch / 'EVALUATION.json')['completed_journeys'], 0)

    def test_contaminated_archive_is_blocked_without_rewriting_proofs(self):
        self.first()
        self.inputs('2026-11-01', '2026-11-02', 'SOL', [('2026-11-01', 'AKE', 105)])
        self.run_day('2026-11-01', '2026-11-02')
        path = self.epoch / 'snapshots/2026-11-01.json'
        row = self.archive.load_json(path)
        row['signals'] = row['observed_signals']
        row['row_sha256'] = self.archive.payload_sha(row, 'row_sha256')
        self.archive.write_json(path, row)
        proofs = {p: p.read_bytes() for p in (*self.archive.snapshot_paths(self.epoch),
                                            self.epoch / 'EVALUATION.json', self.epoch / 'TRADES.json')}
        for now, status in [('2026-11-03', 'BLOCKED_INVALID_ALT_MONTHLY_PATH_NO_BACKFILL'),
                            ('2026-11-04', 'FAILED_MISSING_CONFIRMED_DAILY_CLOSE_NO_BACKFILL')]:
            result = next_epoch.plan(self.root, 'alt', datetime.fromisoformat(now + 'T12:00:00+00:00'))
            self.assertEqual(result['status'], status)
            self.assertEqual(result['alt_path_error'], 'ALT_INTRAMONTH_SIGNAL_CHANGED:2026-11-01')
            self.assertFalse(result['can_append'])
            self.assertFalse(result['economic_result_valid'])
        self.assertEqual(proofs, {p: p.read_bytes() for p in proofs})

    def test_real_rollover_keeps_previous_holdings_through_next_close(self):
        from datetime import date, timedelta
        self.first()
        for d in range(1, 30):
            day = date(2026, 11, d)
            tomorrow = day + timedelta(days=1)
            self.inputs(day.isoformat(), tomorrow.isoformat(), 'SOL', [(day.isoformat(), 'AKE', 100)])
            self.run_day(day.isoformat(), tomorrow.isoformat())
        self.inputs('2026-11-30', '2026-12-01', 'SOL', [('2026-11-30', 'AKE', 100)])
        self.run_day('2026-11-30', '2026-12-01')
        self.inputs('2026-12-01', '2026-12-02', 'SOL', [('2026-12-01', 'SOL', 100)])
        with self.assertRaisesRegex(RuntimeError, 'missing rollover exit prices:.*AKE'):
            self.run_day('2026-12-01', '2026-12-02')
        self.inputs('2026-12-01', '2026-12-02', 'SOL',
                    [('2026-12-01', 'AKE', 101), ('2026-12-01', 'SOL', 100)])
        result = self.run_day('2026-12-01', '2026-12-02')
        self.assertTrue(result['delivery']['economic_result_valid'])
        self.assertEqual(self.archive.load_json(self.epoch / 'EVALUATION.json')['completed_journeys'], 2)


if __name__=='__main__':unittest.main()
