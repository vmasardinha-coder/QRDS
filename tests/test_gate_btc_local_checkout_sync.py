import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools.gate_btc_local_checkout_sync import sync, git, normalize


class LocalCheckoutSyncTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.origin = self.root / "origin"
        self.checkout = self.root / "checkout"
        self.origin.mkdir()
        git(self.origin, "init", "-b", "main")
        git(self.origin, "config", "user.name", "Test")
        git(self.origin, "config", "user.email", "test@example.invalid")
        (self.origin / "a.txt").write_bytes(b"original\n")
        git(self.origin, "add", ".")
        git(self.origin, "commit", "-m", "first")
        self.url = self.origin.as_uri()
        self.backups = self.root / "backups"
        self.call()

    def tearDown(self):
        # Windows Git objects are read-only; clear that flag before cleanup.
        import os, stat
        for p in self.root.rglob("*"):
            if p.is_file():
                os.chmod(p, stat.S_IWRITE | stat.S_IREAD)
        self.temp.cleanup()

    def call(self):
        return sync(self.checkout, "main", self.backups, self.url)

    def advance(self, name="a.txt", data=b"new\n"):
        (self.origin / name).write_bytes(data)
        git(self.origin, "add", ".")
        git(self.origin, "commit", "-m", "advance")

    def test_informational_fetch_stderr_is_success_and_spool_untouched(self):
        spool = self.root / "spool"; spool.mkdir()
        evidence = spool / "event.json"; evidence.write_bytes(b'{"original":true}')
        self.advance()
        result = self.call()
        self.assertEqual(result["status"], "SYNC_PASS")
        self.assertEqual(normalize((self.checkout / "a.txt").read_bytes()), b"new\n")
        self.assertEqual(evidence.read_bytes(), b'{"original":true}')

    def test_null_shallow_is_backed_up_and_recovered(self):
        shallow = self.checkout / ".git/shallow"
        raw = b"\x00" * 1025; shallow.write_bytes(raw)
        self.advance()
        result = self.call()
        self.assertTrue(result["null_shallow_recovered"])
        self.assertEqual((Path(result["backup"]) / "shallow.original").read_bytes(), raw)
        self.assertNotIn(b"\x00", shallow.read_bytes())
        self.assertEqual(git(self.checkout, "status", "--porcelain").stdout, b"")

    def test_equivalent_tracked_and_untracked_upstream_changes_are_preserved(self):
        self.advance(data=b"new\n")
        self.advance("helper.py", b"ready = True\n")
        (self.checkout / "a.txt").write_bytes(b"new\r\n")
        (self.checkout / "helper.py").write_bytes(b"ready = True\r\n")
        result = self.call()
        self.assertEqual(len(result["preserved_upstream_files"]), 2)
        self.assertEqual((Path(result["backup"]) / "already_upstream/a.txt").read_bytes(), b"new\r\n")

    def test_divergent_local_file_blocks_reset_and_is_unchanged(self):
        before = git(self.checkout, "rev-parse", "HEAD").stdout
        (self.checkout / "a.txt").write_bytes(b"unique local change\n")
        self.advance()
        with self.assertRaisesRegex(RuntimeError, "DIVERGENT_LOCAL_FILE_PRESERVED"):
            self.call()
        self.assertEqual((self.checkout / "a.txt").read_bytes(), b"unique local change\n")
        self.assertEqual(git(self.checkout, "rev-parse", "HEAD").stdout, before)

    def test_unknown_untracked_file_blocks_reset(self):
        (self.checkout / "untracked.txt").write_bytes(b"evidence\n")
        with self.assertRaisesRegex(RuntimeError, "DIVERGENT_LOCAL_FILE_PRESERVED"):
            self.call()
        self.assertEqual((self.checkout / "untracked.txt").read_bytes(), b"evidence\n")

    def test_unknown_metadata_corruption_is_not_rewritten(self):
        shallow = self.checkout / ".git/shallow"
        raw = b"\x00unexpected"; shallow.write_bytes(raw)
        with self.assertRaisesRegex(RuntimeError, "UNRECOGNIZED_SHALLOW_CORRUPTION"):
            self.call()
        self.assertEqual(shallow.read_bytes(), raw)

    def test_failed_fetch_never_resets_or_changes_working_file(self):
        before = git(self.checkout, "rev-parse", "HEAD").stdout
        invalid = self.root / "missing"
        git(self.checkout, "remote", "set-url", "origin", invalid.as_uri())
        with self.assertRaises(RuntimeError):
            sync(self.checkout, "main", self.backups, invalid.as_uri())
        self.assertEqual(git(self.checkout, "rev-parse", "HEAD").stdout, before)
        self.assertEqual(normalize((self.checkout / "a.txt").read_bytes()), b"original\n")


if __name__ == "__main__":
    unittest.main()
