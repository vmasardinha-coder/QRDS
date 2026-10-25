"""Exercise the actual workflow publisher against a concurrent runtime writer."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest


WORKFLOW = Path(__file__).resolve().parents[1] / '.github/workflows/gate-btc-crypto-forward-public-capture.yml'
ROOT = 'runtime/factory_sources/crypto_forward'


class PublicationRetryTests(unittest.TestCase):
    def test_concurrent_source_publication_is_preserved_and_reports_are_recomputed(self):
        script = WORKFLOW.read_text().split('      - name: Publish append-only sealed prospective pair\n', 1)[1]
        script = textwrap.dedent(script.split('        run: |\n', 1)[1].split('      - uses:', 1)[0])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_git = shutil.which('git')
            def git(*args, cwd=root):
                return subprocess.run([real_git, *args], cwd=cwd, check=True, capture_output=True, text=True)
            remote = root / 'remote.git'
            seed = root / 'seed'
            git('init', '--bare', str(remote))
            git('init', str(seed))
            git('config', 'user.name', 'test', cwd=seed)
            git('config', 'user.email', 'test@example.invalid', cwd=seed)
            data = seed / ROOT
            (data / 'full_local').mkdir(parents=True)
            (data / 'full_local/source.txt').write_text('old-source')
            (data / 'SOURCE_ADMISSION.json').write_text('old-report')
            git('add', '.', cwd=seed)
            git('commit', '-m', 'seed', cwd=seed)
            git('branch', '-M', 'gate-btc-runtime', cwd=seed)
            git('remote', 'add', 'origin', str(remote), cwd=seed)
            git('push', 'origin', 'gate-btc-runtime', cwd=seed)
            git('symbolic-ref', 'HEAD', 'refs/heads/gate-btc-runtime', cwd=remote)
            publisher = root / 'publisher'
            concurrent = root / 'concurrent'
            git('clone', str(remote), str(publisher))
            git('clone', str(remote), str(concurrent))
            git('config', 'user.name', 'concurrent', cwd=concurrent)
            git('config', 'user.email', 'concurrent@example.invalid', cwd=concurrent)
            pair = publisher / 'out/pair'
            pair.mkdir(parents=True)
            (pair / 'T.json').write_text('sealed-signal')
            (pair / 'T_PLUS_1.json').write_text('sealed-outcome')
            bin_dir = root / 'bin'
            bin_dir.mkdir()
            # Simulate the source publisher winning exactly the first push race.
            wrapper = bin_dir / 'git'
            wrapper.write_text('#!' + sys.executable + '\n' + textwrap.dedent('''
                import os, pathlib, subprocess, sys
                real=os.environ['QRDS_REAL_GIT']; marker=pathlib.Path(os.environ['QRDS_RACE_MARKER'])
                if 'push' in sys.argv[1:] and not marker.exists():
                    marker.touch(); repo=pathlib.Path(os.environ['QRDS_CONCURRENT'])
                    base=repo/'runtime/factory_sources/crypto_forward'
                    (base/'full_local/source.txt').write_text('new-source')
                    (base/'SOURCE_ADMISSION.json').write_text('concurrent-report')
                    for args in [('add','.'),('commit','-m','concurrent source'),('push','origin','gate-btc-runtime')]:
                        subprocess.run([real,*args],cwd=repo,check=True)
                sys.exit(subprocess.run([real,*sys.argv[1:]]).returncode)
            '''))
            wrapper.chmod(0o755)
            # Derivers are tested independently; this stand-in exposes which base
            # snapshot the real shell retry gives them on each attempt.
            derive = bin_dir / 'python'
            derive.write_text('#!' + sys.executable + '\n' + textwrap.dedent('''
                import pathlib, sys
                args=sys.argv; root=pathlib.Path('runtime-tree/runtime/factory_sources/crypto_forward')
                source=(root/'full_local/source.txt').read_text()
                if 'crypto_full_local_publication.py' in args[1]:
                    output=root/'SOURCE_ADMISSION.json'
                else:
                    output=pathlib.Path(args[args.index('--out')+1])
                output.write_text(source)
            '''))
            derive.chmod(0o755)
            env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ['PATH'],
                       QRDS_REAL_GIT=real_git, QRDS_RACE_MARKER=str(root/'raced'),
                       QRDS_CONCURRENT=str(concurrent), GITHUB_RUN_ID='12345')
            result = subprocess.run(['bash', '-c', script], cwd=publisher, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            verification = root / 'verification'
            git('clone', str(remote), str(verification))
            final = verification / ROOT
            self.assertEqual((final/'full_local/source.txt').read_text(), 'new-source')
            self.assertEqual((final/'SOURCE_ADMISSION.json').read_text(), 'new-source')
            self.assertEqual((final/'ACCESSIBLE_BLIND_LEDGER.json').read_text(), 'new-source')
            self.assertEqual((final/'audits/12345-T.json').read_text(), 'sealed-signal')
            self.assertEqual((final/'audits/12345-T1.json').read_text(), 'sealed-outcome')
            self.assertTrue((root/'raced').exists())


if __name__ == '__main__':
    unittest.main()
