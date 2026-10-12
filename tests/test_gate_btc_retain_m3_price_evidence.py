import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from tools.gate_btc_retain_m3_price_evidence import retain

class RetainEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='M3 evidence ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        (self.root / '.gitignore').write_text('*.zip\n')
    def archive(self, day='2026-10-11', epoch=True):
        scope = 'epochs/after_gap_2026-10-05/' if epoch else ''
        p = self.root / ('runtime/ledgers/momentum_m3_economics/' + scope + 'source_prices/' + day + '/required_prices.zip')
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'original sealed archive')
        p.with_name('MANIFEST.json').write_text(json.dumps({'prices_zip_sha256': hashlib.sha256(p.read_bytes()).hexdigest()}))
        return p
    def staged(self):
        return subprocess.check_output(['git', '-C', str(self.root), 'diff', '--cached', '--name-only'], text=True).splitlines()
    def test_ignored_original_archive_survives_git_publication_unchanged(self):
        p = self.archive()
        original = p.read_bytes()
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        self.assertNotIn(str(p.relative_to(self.root)), self.staged())
        retain(self.root)
        rel = str(p.relative_to(self.root))
        self.assertIn(rel, self.staged())
        self.assertEqual(subprocess.check_output(['git', '-C', str(self.root), 'show', ':' + rel]), original)
        self.assertEqual(p.read_bytes(), original)
    def test_tampered_archive_rejected_before_any_archive_staging(self):
        self.archive('2026-10-10')
        p = self.archive()
        p.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'SEALED_M3_PRICE_ARCHIVE_CHANGED'):
            retain(self.root)
        self.assertEqual(self.staged(), [])
    def test_transient_and_unrelated_zip_not_staged(self):
        p = self.archive(epoch=False)
        (self.root / 'current_prices.zip').write_bytes(b'transient')
        (self.root / 'other.zip').write_bytes(b'unrelated')
        self.assertEqual(retain(self.root), [str(p.relative_to(self.root))])
        self.assertEqual(self.staged(), [str(p.relative_to(self.root))])
    def test_missing_archive_not_reconstructed_or_credited(self):
        root = self.root / 'runtime/ledgers/momentum_m3_economics/epochs/after_gap_2026-10-05/source_prices/2026-10-09'
        root.mkdir(parents=True)
        (root / 'MANIFEST.json').write_text('{}')
        self.assertEqual(retain(self.root), [])
        self.assertEqual(self.staged(), [])
        self.assertFalse((root / 'required_prices.zip').exists())

if __name__ == '__main__':
    unittest.main()
