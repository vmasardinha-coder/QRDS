import subprocess
import tempfile
import unittest
from pathlib import Path

LANE = 'runtime/factory_sources/crypto_forward'

class SparseCryptoPublicationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='crypto sparse ')
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.repo = self.base / 'incumbent'
        self.git(self.base, 'init', '-q', str(self.repo))
        self.git(self.repo, 'config', 'user.name', 'test')
        self.git(self.repo, 'config', 'user.email', 'test@example.invalid')
        for rel in [LANE + '/SOURCE_ADMISSION.json', LANE + '/ACCESSIBLE_SOURCE_ADMISSION.json',
                    LANE + '/full_local/audits/original.json', 'runtime/ledgers/d50/LEDGER.json',
                    'runtime/factory_population/FAMILIES.json']:
            p = self.repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('original\n')
        self.git(self.repo, 'add', '.')
        self.git(self.repo, 'commit', '-qm', 'original runtime')
        self.original = self.git(self.repo, 'rev-parse', 'HEAD').strip()
        self.worktree = self.base / 'publication'
        self.git(self.repo, 'worktree', 'add', '--no-checkout', '--detach', str(self.worktree), 'HEAD')
        self.git(self.worktree, 'sparse-checkout', 'set', '--cone', LANE)
        self.git(self.worktree, 'checkout', '--force', 'HEAD')
    def git(self, repo, *args):
        return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.STDOUT, text=True)
    def test_materializes_source_journals_without_other_ledgers(self):
        self.assertTrue((self.worktree / LANE / 'full_local/audits/original.json').exists())
        self.assertTrue((self.worktree / LANE / 'ACCESSIBLE_SOURCE_ADMISSION.json').exists())
        self.assertFalse((self.worktree / 'runtime/ledgers/d50/LEDGER.json').exists())
        self.assertFalse((self.worktree / 'runtime/factory_population/FAMILIES.json').exists())
    def test_publication_commit_preserves_unmaterialized_ledger_bytes(self):
        p = self.worktree / LANE / 'full_local/audits/new.json'
        p.write_text('new source proof\n')
        self.git(self.worktree, 'add', LANE)
        self.git(self.worktree, 'commit', '-qm', 'append source')
        self.assertEqual(self.git(self.worktree, 'show', 'HEAD:runtime/ledgers/d50/LEDGER.json'), 'original\n')
        self.assertEqual(self.git(self.worktree, 'show', 'HEAD:' + LANE + '/full_local/audits/original.json'), 'original\n')
        self.assertEqual(self.git(self.worktree, 'diff', '--name-only', self.original, 'HEAD').strip(),
                         LANE + '/full_local/audits/new.json')
    def test_retry_reset_keeps_sparse_scope_and_latest_source(self):
        p = self.repo / LANE / 'FULL_LOCAL_LATEST.json'
        p.write_text('concurrent proof\n')
        self.git(self.repo, 'add', LANE)
        self.git(self.repo, 'commit', '-qm', 'concurrent runtime')
        new_head = self.git(self.repo, 'rev-parse', 'HEAD').strip()
        self.git(self.worktree, 'reset', '--hard', new_head)
        self.assertEqual((self.worktree / LANE / 'FULL_LOCAL_LATEST.json').read_text(), 'concurrent proof\n')
        self.assertFalse((self.worktree / 'runtime/ledgers/d50/LEDGER.json').exists())
    def test_incumbent_dirty_file_and_checkout_remain_untouched(self):
        ledger = self.repo / 'runtime/ledgers/d50/LEDGER.json'
        ledger.write_text('operator working change\n')
        before = self.git(self.repo, 'status', '--porcelain')
        self.git(self.worktree, 'reset', '--hard', self.original)
        self.assertEqual(ledger.read_text(), 'operator working change\n')
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), before)
        self.assertTrue((self.repo / 'runtime/factory_population/FAMILIES.json').exists())

if __name__ == '__main__':
    unittest.main()
