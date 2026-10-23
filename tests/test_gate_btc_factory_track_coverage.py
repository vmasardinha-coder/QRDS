import json
import tempfile
import unittest
import os
import shutil
import subprocess
from pathlib import Path

from tools.gate_btc_factory_status_export import export_tracks


class FactoryTrackCoverageTests(unittest.TestCase):
    def test_source_readiness_is_separate_from_panel_and_never_implies_training(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            self.write(root,'runtime/gate_btc_2/system13/observed_panel_v1/SOURCE_READINESS.json',
                {'eligible_members':215,'exact_binding_candidates':91,'training_ready':False,
                 'qualified_system13_ohlcv_assets':0})
            tracks=export_tracks(root)
            self.assertEqual(tracks['system13_source_readiness_v1']['data']['exact_binding_candidates'],91)
            self.assertFalse(tracks['system13_source_readiness_v1']['data']['training_ready'])
            self.assertFalse(tracks['system13_observed_panel_v1']['exists'])
    def write(self, root, path, data):
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data))

    def fixture(self, root):
        base = 'runtime/ledgers/'
        self.write(root, base + 'momentum_m1_m2/STATUS.json', {'observed_snapshots': 47})
        self.write(root, base + 'momentum_m1_m2_economics/ECONOMICS_STATUS.json', {'status': 'LEGACY', 'return_observations': 99})
        self.write(root, base + 'momentum_m1_m2_economics/ACTIVE_EPOCH.json', {'relative_path': 'epochs/hold_20260928'})
        self.write(root, base + 'momentum_m1_m2_economics/epochs/hold_20260928/ECONOMICS_STATUS.json', {'status': 'ECONOMICS_ACTIVE_HOLD_GROSS_ONLY', 'return_observations': 12, 'net_return': None})
        self.write(root, base + 'momentum_m3/STATUS.json', {'observed_snapshots': 28})
        self.write(root, base + 'momentum_m3_economics/STATUS.json', {'active_epoch': 'epochs/after_gap_2026-10-05', 'return_observations': 10})
        self.write(root, base + 'momentum_m3_economics/epochs/after_gap_2026-10-05/STATUS.json', {'status': 'ECONOMICS_ACTIVE_HOLD_GROSS_ONLY', 'return_observations': 5, 'net_return': None})
        self.write(root, base + 'delta_v12_engine/STATUS.json', {'status': 'ACTIVE_PROSPECTIVE_SHADOW', 'observed_days': 12})
        self.write(root, base + 'delta_v13_engine/STATUS.json', {'status': 'ACTIVE_PROSPECTIVE_SHADOW', 'observed_days': 18})
        self.write(root, base + 'v16_family/STATUS.json', {'status': 'DEFINITION_COMPLETE_PROSPECTIVE_EVIDENCE_PENDING'})
        self.write(root, base + 'v16b/STATUS.json', {'status': 'TERMINAL_BLOCKED_NOT_PROMOTABLE', 'canonical_cycle_count': 0})
        self.write(root, base + 'v16b1/STATUS.json', {'status': 'PROSPECTIVE_ORCHESTRATOR_ACTIVE', 'canonical_cycle_count': 0})
        for child in ('v16c', 'v16d', 'v16e'):
            self.write(root, base + child + '/STATUS.json', {'status': 'WAITING_DEPENDENCY', 'canonical_cycle_count': 0})

    def test_signal_and_active_economic_clocks_are_separate_without_input_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.fixture(root)
            before = {p: p.read_bytes() for p in root.rglob('*.json')}
            tracks = export_tracks(root)
            self.assertEqual(tracks['m1_m2']['data']['observed_snapshots'], 47)
            self.assertEqual(tracks['m1_m2_economics']['data']['return_observations'], 12)
            self.assertEqual(tracks['m3_signal']['data']['observed_snapshots'], 28)
            self.assertEqual(tracks['m3_economics']['data']['return_observations'], 5)
            self.assertIsNone(tracks['m3_economics']['data']['net_return'])
            self.assertIn('epochs/after_gap_2026-10-05', tracks['m3_economics']['path'])
            self.assertEqual(before, {p: p.read_bytes() for p in root.rglob('*.json')})

    def test_v12_v13_and_v16_parent_child_states_remain_distinct(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.fixture(root)
            # Bind the real main-branch V12 closure just as production does.
            tracks = export_tracks(root)
            self.assertEqual(tracks['v12']['data']['status'], 'CLOSED_NO_FURTHER_OBSERVATIONS_POSSIBLE')
            self.assertEqual(tracks['v12']['data']['observed_days'], 12)
            self.assertEqual(tracks['v13']['data']['observed_days'], 18)
            self.assertEqual(tracks['v16b']['data']['status'], 'TERMINAL_BLOCKED_NOT_PROMOTABLE')
            self.assertEqual(tracks['v16b1']['data']['status'], 'PROSPECTIVE_ORCHESTRATOR_ACTIVE')
            for child in ('v16b1', 'v16c', 'v16d', 'v16e'):
                self.assertEqual(tracks[child]['data']['canonical_cycle_count'], 0)

    def test_missing_selected_economics_are_explicit_and_never_fall_back(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); self.fixture(root)
            for path in ('momentum_m1_m2_economics/epochs/hold_20260928/ECONOMICS_STATUS.json',
                         'momentum_m3_economics/epochs/after_gap_2026-10-05/STATUS.json'):
                (root / 'runtime/ledgers' / path).unlink()
            tracks = export_tracks(root)
            for key in ('m1_m2_economics', 'm3_economics'):
                self.assertFalse(tracks[key]['exists'])
                self.assertEqual(tracks[key]['status'], 'MISSING')
                self.assertNotIn('data', tracks[key])

    def test_declared_zero_credit_m3_gap_is_visible_without_legacy_economics(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);self.fixture(root)
            base='runtime/ledgers/momentum_m3_economics/'
            (root/base/'epochs/after_gap_2026-10-05/STATUS.json').unlink()
            self.write(root,base+'STATUS.json',{
                'schema':'gate_btc.momentum_m3_economics_status.v2',
                'status':'SOURCE_GAP_ZERO_CREDIT','active_epoch':'epochs/after_gap_2026-10-05',
                'current_epoch_return_observations':0,'current_epoch_nav':None,
                'legacy_return_observations':99,'legacy_nav':123,'gap_cutoff':'2026-10-05'})
            before={p:p.read_bytes() for p in root.rglob('*.json')}
            entry=export_tracks(root)['m3_economics']
            self.assertFalse(entry['exists']);self.assertNotIn('data',entry)
            self.assertEqual(entry['status'],'WAIT_ACTIVE_EPOCH_ECONOMIC_EVIDENCE')
            self.assertEqual(entry['epoch_lifecycle']['current_epoch_return_observations'],0)
            self.assertFalse(entry['epoch_lifecycle']['historical_credit_transferred'])
            self.assertNotIn('legacy_nav',entry['epoch_lifecycle'])
            self.assertEqual(before,{p:p.read_bytes() for p in root.rglob('*.json')})
            # A pointer alone or a nonzero missing epoch never becomes evidence.
            state=json.loads((root/base/'STATUS.json').read_text())
            state['current_epoch_return_observations']=1
            self.write(root,base+'STATUS.json',state)
            self.assertEqual(export_tracks(root)['m3_economics']['status'],'MISSING')

    @unittest.skipUnless(os.name == 'posix', 'Publication workflow executes on Linux')
    def test_publication_recomputes_after_concurrent_writer_without_losing_ledgers(self):
        repo=Path(__file__).resolve().parents[1]
        workflow=(repo/'.github/workflows/gate-btc-factory-status-export.yml').read_text()
        part=workflow.split('- name: Persist status only',1)[1].split('run: |',1)[1]
        script='\n'.join(line[10:] for line in part.splitlines() if line.startswith('          '))
        script=script.replace('${{ github.run_id }}','1234')
        real_git=shutil.which('git')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);remote=root/'remote.git';producer=root/'producer';runtime=root/'runtime_repo'
            def git(*args,cwd=None):
                return subprocess.run([real_git,*map(str,args)],cwd=cwd,check=True,capture_output=True,text=True).stdout.strip()
            git('init','--bare',remote);git('clone',remote,producer)
            git('config','user.name','test',cwd=producer);git('config','user.email','test@example.invalid',cwd=producer)
            git('checkout','-b','gate-btc-runtime',cwd=producer)
            self.write(producer,'runtime/ledgers/momentum_m1_m2/STATUS.json',{'observed_snapshots':1})
            git('add','.',cwd=producer);git('commit','-m','anchor',cwd=producer);git('push','origin','gate-btc-runtime',cwd=producer)
            git('clone','--branch','gate-btc-runtime',remote,runtime)
            main=root/'main_repo';(main/'tools').mkdir(parents=True)
            for name in ['gate_btc_factory_status_export.py','gate_btc_reporting_authority.py']:
                shutil.copyfile(repo/'tools'/name,main/'tools'/name)
            bin_dir=root/'bin';bin_dir.mkdir();wrapper=bin_dir/'git';marker=root/'raced'
            # The first push races with a real writer changing a ledger and the
            # same derived report. The next attempt must use the new parent/data.
            wrapper.write_text('#!/bin/sh\nif [ "$1" = "push" ] && [ ! -f "$RACE_MARKER" ]; then\n'
                '  touch "$RACE_MARKER"\n'
                "  printf '%s\\n' '{\"observed_snapshots\":2}' > \"$RACE_PRODUCER/runtime/ledgers/momentum_m1_m2/STATUS.json\"\n"
                "  printf '%s\\n' '{\"other_writer\":true}' > \"$RACE_PRODUCER/runtime/GATE_BTC_FACTORY_STATUS_LATEST.json\"\n"
                '  "$REAL_GIT" -C "$RACE_PRODUCER" add .\n'
                '  "$REAL_GIT" -C "$RACE_PRODUCER" commit -m competing-writer >/dev/null\n'
                '  "$REAL_GIT" -C "$RACE_PRODUCER" push origin gate-btc-runtime >/dev/null\n'
                'fi\nexec "$REAL_GIT" "$@"\n')
            wrapper.chmod(0o755)
            env={**os.environ,'PATH':str(bin_dir)+os.pathsep+os.environ['PATH'],
                 'REAL_GIT':real_git,'RACE_MARKER':str(marker),'RACE_PRODUCER':str(producer)}
            result=subprocess.run(['bash','-euo','pipefail','-c',script],cwd=runtime,env=env,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            report=json.loads(git('show','gate-btc-runtime:runtime/GATE_BTC_FACTORY_STATUS_LATEST.json',cwd=remote))
            ledger=json.loads(git('show','gate-btc-runtime:runtime/ledgers/momentum_m1_m2/STATUS.json',cwd=remote))
            self.assertEqual(ledger['observed_snapshots'],2)
            self.assertEqual(report['tracks']['m1_m2']['data']['observed_snapshots'],2)
            ancestor=git('rev-parse','HEAD',cwd=producer)
            git('merge-base','--is-ancestor',ancestor,'gate-btc-runtime',cwd=remote)
            self.assertTrue(marker.is_file())

    def test_absent_new_track_is_reported_missing(self):
        with tempfile.TemporaryDirectory() as td:
            tracks = export_tracks(Path(td))
            for key in ('m1_m2_economics', 'm3_signal', 'm3_economics', 'v13',
                        'v16_family', 'v16b1', 'v16c', 'v16d', 'v16e'):
                self.assertFalse(tracks[key]['exists'])
                self.assertEqual(tracks[key]['status'], 'MISSING')


if __name__ == '__main__':
    unittest.main()


