import copy
import gzip
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gate_btc_xagent_spot_experiment as x
import gate_btc_system13_observed_panel as panel
import gate_btc_v2a_data_ledger as parent
import gate_btc_research_progress_publish as publication
import gate_btc_factory_status_export as exporter

NOW = datetime(2026, 10, 23, 2, 15, tzinfo=timezone.utc)


def records(values=(0.6, 0.6, -0.3)):
    c = x.load_contract(); result = []
    for (pid, evidence), value in zip(c["producers"].items(), values):
        ms = int((NOW - timedelta(minutes=10)).timestamp() * 1000)
        d = {"schema": "gate_btc_2.xagent_signal_observation.v1", "producer_id": pid,
             "evidence_class": evidence, "signal": value, "available_after_ms": ms,
             "capture_time_ms": ms, "close_time_ms": ms, "common_closed_bar_close_ms": ms,
             "instrument": "BTCUSDT", "source_checks": {"closed_kline": True},
             "economic_outcomes_read": False, "engine_feed": False, "orders": 0, "real_capital": 0}
        result.append(x.seal(d))
    return result


def bar(at, price):
    t = int(x.timestamp(at).timestamp() * 1000)
    return [t, str(price), str(price), str(price), str(price), "1", t + 59999, "1", 1, "1", "1", "0"]


class XagentTests(unittest.TestCase):
    def decision(self):
        return x.make_decision(records(), NOW, "a" * 40, x.load_contract())

    def test_continuous_overlay_and_no_parameter_search(self):
        d = self.decision()
        self.assertAlmostEqual(d["consensus_weight"], .3)
        self.assertAlmostEqual(d["features"]["pairwise_disagreement"], .3)
        self.assertAlmostEqual(d["candidate_weight"], .21)
        self.assertFalse(d["safety"]["engine_feed"])

    def test_negative_consensus_is_valid_cash_not_missing_data(self):
        d = x.make_decision(records((-.2, -.1, -.3)), NOW, "a" * 40, x.load_contract())
        self.assertEqual(d["status"], "DECISION_READY")
        self.assertEqual(d["candidate_weight"], 0)

    def test_missing_signal_abstains_without_zero_fill(self):
        d = x.make_decision(records((None, .6, -.3)), NOW, "a" * 40, x.load_contract())
        self.assertEqual(d["status"], "ABSTAIN_INPUT_UNAVAILABLE")
        self.assertIsNone(d["candidate_weight"])

    def test_stale_and_future_inputs_abstain(self):
        for shift in [timedelta(hours=-2), timedelta(minutes=1)]:
            rs = records(); d = {k: v for k, v in rs[0].items() if k != "record_sha256"}
            d["available_after_ms"] = int((NOW + shift).timestamp() * 1000)
            d["close_time_ms"] = d["available_after_ms"]; rs[0] = x.seal(d)
            out = x.make_decision(rs, NOW, "a" * 40, x.load_contract())
            self.assertEqual(out["status"], "ABSTAIN_INPUT_UNAVAILABLE")

    def test_hash_duplicate_and_nonfinite_rejected(self):
        rs = records(); rs[0]["signal"] = .4
        with self.assertRaisesRegex(ValueError, "HASH"):
            x.make_decision(rs, NOW, "a" * 40, x.load_contract())
        with self.assertRaises(ValueError):
            x.make_decision([records()[0]] * 3, NOW, "a" * 40, x.load_contract())
        with self.assertRaises(ValueError):
            records((math.nan, .1, .2))

    def test_no_decisions_before_contract_or_after_cutoff(self):
        for t in [NOW - timedelta(days=1), NOW.replace(hour=3), NOW.replace(minute=46)]:
            with self.assertRaisesRegex(ValueError, "WINDOW"):
                x.make_decision(records(), t, "a" * 40, x.load_contract())

    def test_paired_returns_use_exact_future_prices_and_fees(self):
        d = self.decision(); c = x.load_contract()
        proof = {"decision_record_sha256": d["record_sha256"], "commit_at_utc": NOW.isoformat()}
        out = x.outcome(d, bar(d["entry_at_utc"], 100), bar(d["exit_at_utc"], 110), NOW + timedelta(days=2), proof, c)
        self.assertAlmostEqual(out["btc_gross_return"], .1)
        self.assertAlmostEqual(out["candidate_net"], .79 + .21/1.001*1.1*.999 - 1)
        self.assertEqual(out["paired_observation"], 1)
        self.assertLess(out["candidate_stress_net"], out["candidate_net"])

    def test_early_late_seal_wrong_minute_and_bad_ohlc_rejected(self):
        d = self.decision(); proof = {"decision_record_sha256": d["record_sha256"], "commit_at_utc": NOW.isoformat()}
        cases = [(bar(d["entry_at_utc"],100), bar(d["exit_at_utc"],110), NOW, proof),
                 (bar(d["entry_at_utc"],100), bar(d["exit_at_utc"],110), NOW+timedelta(days=2), {**proof,"commit_at_utc":d["entry_at_utc"]}),
                 (bar((x.timestamp(d["entry_at_utc"])+timedelta(minutes=1)).isoformat(),100),bar(d["exit_at_utc"],110),NOW+timedelta(days=2),proof)]
        for a,b,t,p in cases:
            with self.assertRaises(ValueError):x.outcome(d,a,b,t,p,x.load_contract())
        bad=bar(d["entry_at_utc"],100);bad[2]='90'
        with self.assertRaisesRegex(ValueError,'OHLC'):x.outcome(d,bad,bar(d["exit_at_utc"],110),NOW+timedelta(days=2),proof,x.load_contract())

    def test_cash_does_not_pay_cost_and_full_exposure_reserves_entry_fee(self):
        self.assertEqual(x.event_return(0, 1.1, 10), 0)
        self.assertAlmostEqual(x.event_return(1, 1, 10), .999/1.001-1)

    def test_immutable_decision_refuses_rewrite(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'d.json';d=self.decision();x.immutable(p,d);x.immutable(p,d)
            with self.assertRaisesRegex(ValueError,'CONFLICT'):x.immutable(p,{**d,'candidate_weight':1})

    def test_published_decision_bound_to_real_git_bytes_and_time(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);subprocess.run(['git','init',str(repo)],check=True,capture_output=True)
            for k,v in [('user.name','fixture'),('user.email','fixture@example.test')]:
                subprocess.run(['git','-C',str(repo),'config',k,v],check=True)
            d=self.decision();p=repo/'runtime'/x.LANE/'decisions/2026-10-23.json';x.immutable(p,d)
            subprocess.run(['git','-C',str(repo),'add','.'],check=True)
            env={**os.environ,'GIT_AUTHOR_DATE':'2026-10-23T02:16:00Z','GIT_COMMITTER_DATE':'2026-10-23T02:16:00Z'}
            subprocess.run(['git','-C',str(repo),'commit','-m','fixture'],check=True,capture_output=True,env=env)
            sha=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD']).decode().strip()
            proof=x.publication_proof(repo,p,d,sha);self.assertEqual(proof['commit_sha'],sha)
            p.write_text('{}')
            with self.assertRaisesRegex(ValueError,'BYTES_DIFFER'):x.publication_proof(repo,p,d,sha)


class PanelTests(unittest.TestCase):
    def csv(self, rows):
        head='id,symbol,current_price,last_updated,is_stable,is_blocked,standard_ticker\n'
        return (head+'\n'.join(','.join(r) for r in rows)+'\n').encode()

    def sample(self, coin='bitcoin', symbol='BTC', price='100', at='2026-10-22T04:00:00Z'):
        return [coin,symbol,price,at,'False','False','True']

    def snapshot(self):
        return {'source_run_utc':'2026-10-22T05:00:00Z','source_data_as_of':'2026-10-21','record_sha256':'a'*64}

    def test_observed_membership_and_quote_are_not_daily_close(self):
        c=json.loads(panel.CONTRACT.read_text());rs=panel.panel_rows(self.snapshot(),self.csv([self.sample()]),c)
        self.assertEqual(rs[0]['observed_at_utc'],'2026-10-22T05:00:00+00:00')
        self.assertFalse(rs[0]['is_daily_close']);self.assertFalse(rs[0]['training_eligible'])
        self.assertEqual(rs[0]['source_data_as_of_diagnostic_only'],'2026-10-21')

    def test_missing_stale_future_quotes_retained_unavailable(self):
        c=json.loads(panel.CONTRACT.read_text())
        for price,at in [('nan','2026-10-22T04:00:00Z'),('100','2026-10-22T06:00:00Z'),('100','2026-10-20T04:00:00Z'),('100','')]:
            rs=panel.panel_rows(self.snapshot(),self.csv([self.sample(price=price,at=at)]),c)
            self.assertEqual(len(rs),1);self.assertFalse(rs[0]['eligible_by_observed_flags_and_quote'])

    def test_exact_id_not_ticker_key_and_duplicates_fail(self):
        c=json.loads(panel.CONTRACT.read_text())
        rs=panel.panel_rows(self.snapshot(),self.csv([self.sample(),self.sample('another','BTC')]),c)
        self.assertEqual(len(rs),2)
        with self.assertRaisesRegex(ValueError,'DUPLICATE'):panel.panel_rows(self.snapshot(),self.csv([self.sample(),self.sample()]),c)

    def test_source_archive_mutation_cannot_pass_parent_validation(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);meta=parent.archive_metadata(root,Path('u.gz'),self.csv([self.sample()]))
            parent.validate_archive(root,meta)
            (root/'u.gz').write_bytes(b'corrupted')
            with self.assertRaisesRegex(RuntimeError,'hash'):parent.validate_archive(root,meta)

    def test_system12_release_not_reopened_or_waived(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/'gate_btc_2/system12/READINESS.json';p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'system12_complete':False,'system13_dependency_released':False}))
            with self.assertRaisesRegex(ValueError,'NOT_RELEASED'):panel.build(root,root/'out')

    def test_panel_materialization_idempotent_and_training_stays_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);release=root/'gate_btc_2/system12/READINESS.json';release.parent.mkdir(parents=True)
            release.write_text(json.dumps({'system12_complete':True,'system13_dependency_released':True}))
            v=root/'data_quality/v2a';(v/'archives').mkdir(parents=True)
            a=v/'archives/u.gz';a.write_bytes(gzip.compress(self.csv([self.sample()]),mtime=0))
            record={**self.snapshot(),'snapshot_id':'sample','universe_archive':{'archive_path':'archives/u.gz'}}
            source=v/'snapshot.json';source.write_text(json.dumps(record))
            with patch.object(panel,'validated_records',return_value=[(1,source,record)]):
                one=panel.build(root,root/'out');two=panel.build(root,root/'out')
            self.assertEqual(one,two);self.assertFalse(two['training_ready']);self.assertFalse(two['system13_complete'])
            self.assertEqual(two['observed_membership_rows'],1)

    def test_publication_scopes_exclude_all_parent_and_capital_lanes(self):
        self.assertEqual(len(publication.SCOPES),2)
        self.assertFalse(any('b3_h1' in x or 'item3' in x for x in publication.SCOPES))

    def test_publisher_refuses_real_staged_parent_change(self):
        with tempfile.TemporaryDirectory() as t:
            repo=Path(t);subprocess.run(['git','init',str(repo)],check=True,capture_output=True)
            parent_file=repo/'runtime/ledgers/b3_h1/STATUS.json';parent_file.parent.mkdir(parents=True)
            parent_file.write_text('{"qualified":17}')
            subprocess.run(['git','-C',str(repo),'add','.'],check=True)
            with self.assertRaisesRegex(RuntimeError,'SCOPE_VIOLATION'):publication.publish(repo)

    def test_factory_export_exposes_zero_outcomes_and_incomplete_panel(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            states={'xagent_spot_continuous_v1':{'status':'AWAITING_FIRST_DECISION_WINDOW','paired_outcome_count':0},
                    'system13_observed_panel_v1':{'indexed_panel_observations':75,'training_ready':False,'system13_complete':False}}
            for key,state in states.items():
                p=root/exporter.TRACKS[key];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(state))
            result=exporter.export_tracks(root)
            for key,state in states.items():
                self.assertTrue(result[key]['exists']);self.assertEqual(result[key]['data'],state)
            self.assertEqual(result['xagent_spot_continuous_v1']['data']['paired_outcome_count'],0)
            self.assertFalse(result['system13_observed_panel_v1']['data']['system13_complete'])


if __name__ == '__main__':unittest.main()
