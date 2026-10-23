"""Materialize pinned H1 Git blobs; keep existing history and worktrees intact."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(r"C:\actions-runner\qrds-local-shadow\code_canonical")
OUT = Path(r"C:\GATE_BTC_PROJECT\RUNTIME\B3_H1_CANONICAL\canonical_collector")
FILES = [
    "tools/gate_btc_b3_h1_daily.py",
    "tools/gate_btc_b3_h1_parser.py",
    "tools/gate_btc_factory/H1_PROSPECTIVE_SCHEDULE_AMENDMENT_20261007.v1.json",
    "tools/gate_btc_h1_schedule_extension.py",
    "tools/gate_btc_factory/H1_PROSPECTIVE_SCHEDULE_EXTENSION_20261022.v1.json",
]
EXPECTED_AMENDMENT = "9a78b234c6f00d64af9e9de1ad2d9aa3b6a28018965f35dcbbd1b0f58f3cdb3a"
EXPECTED_EXTENSION = "6e74e6357c3609491179b765c15b02d4fdadf26e2d4ff9add45546b31f325ce3"


def git(*args):
    p = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="replace")[-600:])
    return p.stdout


def main():
    head = git("rev-parse", "HEAD").decode().strip()
    blobs = {path: git("show", head + ":" + path) for path in FILES}
    for name, expected in [(FILES[2], EXPECTED_AMENDMENT), (FILES[4], EXPECTED_EXTENSION)]:
        if hashlib.sha256(blobs[name]).hexdigest() != expected:
            raise RuntimeError("H1_FROZEN_CONTRACT_GIT_BLOB_HASH_MISMATCH:" + name)
    for name, raw in blobs.items():
        target = OUT / Path(name).relative_to("tools")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists() or target.read_bytes() != raw:
            candidate = target.with_suffix(target.suffix + ".partial")
            candidate.write_bytes(raw)
            candidate.replace(target)
        if target.read_bytes() != raw:
            raise RuntimeError("H1_LOCAL_BLOB_MATERIALIZATION_MISMATCH:" + name)
    print(json.dumps({"status": "PASS", "main_head": head,
                      "amendment_sha256": EXPECTED_AMENDMENT,
                      "extension_sha256": EXPECTED_EXTENSION,
                      "collector": str(OUT / "gate_btc_b3_h1_daily.py"),
                      "collector_executed": False, "counter_changed": False}))


if __name__ == "__main__":
    main()
