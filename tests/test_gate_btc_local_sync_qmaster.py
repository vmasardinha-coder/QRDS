import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_local_sync_qmaster import qmaster, sync


def cmd(*args):
    subprocess.run(args, check=True, capture_output=True)


class LocalSyncAuditTests(unittest.TestCase):
    def test_fast_forward_and_qmaster_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bare, author, local = (root / name for name in ("remote.git", "author", "local"))
            cmd("git", "init", "--bare", "-b", "gate-btc-runtime", str(bare))
            cmd("git", "clone", str(bare), str(author))
            cmd("git", "-C", str(author), "config", "user.name", "test")
            cmd("git", "-C", str(author), "config", "user.email", "test@example.org")
            files = author / "runtime"
            files.mkdir()
            csv = b"date,symbol,close_usd,volume_usd,source\n2026-10-08,BTC,1,1,test\n"
            sha = hashlib.sha256(csv).hexdigest()
            (files / "GATE_BTC_QMASTER_LATEST.csv").write_bytes(csv)
            (files / "GATE_BTC_QMASTER_LATEST.txt").write_text(json.dumps({
                "status": "PASS", "research_only": True, "orders_generated": 0,
                "real_capital_used": 0, "data_as_of": "2026-10-08",
                "csv_sha256": sha, "rows": 1, "symbols": 1}))
            cmd("git", "-C", str(author), "add", ".")
            cmd("git", "-C", str(author), "commit", "-m", "initial")
            cmd("git", "-C", str(author), "push", "origin", "gate-btc-runtime")
            cmd("git", "clone", str(bare), str(local))
            (author / "new.txt").write_text("new")
            cmd("git", "-C", str(author), "add", ".")
            cmd("git", "-C", str(author), "commit", "-m", "update")
            cmd("git", "-C", str(author), "push", "origin", "gate-btc-runtime")
            self.assertEqual(sync(local, "gate-btc-runtime", False)["status"], "FAST_FORWARD_AVAILABLE")
            self.assertEqual(sync(local, "gate-btc-runtime", True)["status"], "FAST_FORWARDED")
            self.assertEqual(qmaster(local, "2026-10-08")["status"], "MATCH_REMOTE")
            (local / "runtime/GATE_BTC_QMASTER_LATEST.csv").write_bytes(b"tampered")
            self.assertEqual(qmaster(local, "2026-10-08")["status"], "FAIL")

    def test_dirty_tree_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bare, author, local = (root / name for name in ("remote.git", "author", "local"))
            cmd("git", "init", "--bare", "-b", "main", str(bare))
            cmd("git", "clone", str(bare), str(author))
            cmd("git", "-C", str(author), "config", "user.name", "test")
            cmd("git", "-C", str(author), "config", "user.email", "test@example.org")
            (author / "a").write_text("one")
            cmd("git", "-C", str(author), "add", ".")
            cmd("git", "-C", str(author), "commit", "-m", "one")
            cmd("git", "-C", str(author), "push", "origin", "main")
            cmd("git", "clone", str(bare), str(local))
            (author / "a").write_text("two")
            cmd("git", "-C", str(author), "commit", "-am", "two")
            cmd("git", "-C", str(author), "push", "origin", "main")
            (local / "a").write_text("my local work")
            self.assertEqual(sync(local, "main", True)["status"], "FAST_FORWARD_BLOCKED_DIRTY")
            self.assertEqual((local / "a").read_text(), "my local work")


if __name__ == "__main__":
    unittest.main()
