#!/usr/bin/env python3
"""Synchronize disposable local checkouts; never executes collectors or edits spools."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

ORIGIN = "https://github.com/vmasardinha-coder/QRDS.git"


def git(path, *args, check=True):
    p = subprocess.run(["git", "-C", str(path), *args], capture_output=True)
    if check and p.returncode:
        raise RuntimeError("GIT_FAILED " + " ".join(args[:2]) + ": " +
                           p.stderr.decode("utf-8", errors="replace")[-1500:])
    return p


def normalize(data):
    return data.replace(b"\r\n", b"\n")


def recover_null_shallow(path, backup):
    """Only recover the observed all-NUL corruption; preserve bytes for rollback."""
    metadata = path / ".git"
    shallow = metadata / "shallow"
    if not shallow.exists():
        return False
    raw = shallow.read_bytes()
    if not raw or b"\x00" not in raw:
        return False
    if raw.strip(b"\x00\r\n"):
        raise RuntimeError("UNRECOGNIZED_SHALLOW_CORRUPTION")
    refs = set()
    for kind in ("heads", "remotes"):
        base = metadata / "refs" / kind
        for ref in base.rglob("*"):
            if ref.is_file():
                value = ref.read_text().strip()
                if re.fullmatch(r"[0-9a-f]{40}", value):
                    refs.add(value)
    packed = metadata / "packed-refs"
    if packed.exists():
        for line in packed.read_text().splitlines():
            fields = line.split()
            if len(fields) == 2 and fields[1].startswith(("refs/heads/", "refs/remotes/")):
                if not re.fullmatch(r"[0-9a-f]{40}", fields[0]):
                    raise RuntimeError("INVALID_PACKED_REF")
                refs.add(fields[0])
    if not refs:
        raise RuntimeError("NO_VERIFIABLE_SHALLOW_BOUNDARIES")
    backup.mkdir(parents=True, exist_ok=True)
    (backup / "shallow.original").write_bytes(raw)
    candidate = shallow.with_suffix(".qrds-recovery")
    candidate.write_text("".join(x + "\n" for x in sorted(refs)), encoding="ascii")
    os.replace(candidate, shallow)
    try:
        for sha in refs:
            if git(path, "cat-file", "-t", sha).stdout.strip() != b"commit":
                raise RuntimeError("SHALLOW_BOUNDARY_NOT_COMMIT")
        git(path, "rev-parse", "--verify", "HEAD")
    except Exception:
        shallow.write_bytes(raw)
        raise
    return True


def sync(path, branch, backup_root, origin=ORIGIN):
    if branch not in ("main", "gate-btc-runtime"):
        raise ValueError("UNEXPECTED_BRANCH")
    path = Path(path)
    backup = Path(backup_root) / (path.name + "_" + str(time.time_ns()))
    if not path.exists():
        p = subprocess.run(["git", "clone", "--depth", "1", "--branch", branch,
                            origin, str(path)], capture_output=True)
        if p.returncode:
            raise RuntimeError(p.stderr.decode(errors="replace"))
    if not (path / ".git").is_dir():
        raise RuntimeError("EXPECTED_STANDALONE_CHECKOUT")
    if git(path, "remote", "get-url", "origin").stdout.decode().strip() != origin:
        raise RuntimeError("UNEXPECTED_ORIGIN")
    repaired = recover_null_shallow(path, backup)
    before = git(path, "rev-parse", "HEAD").stdout.decode().strip()
    # Git's informational stderr never becomes a PowerShell terminating exception.
    git(path, "fetch", "--depth", "1", "origin",
        "+refs/heads/" + branch + ":refs/remotes/origin/" + branch)
    target = "refs/remotes/origin/" + branch
    changed = git(path, "status", "--porcelain=v1", "-z").stdout
    preserved = []
    for entry in changed.split(b"\x00"):
        if not entry:
            continue
        state = entry[:2].decode()
        name = entry[3:].decode("utf-8")
        if state not in (" M", "M ", "??"):
            raise RuntimeError("LOCAL_CHANGE_REQUIRES_REVIEW " + state + " " + name)
        file = path / name
        if not file.is_file() or file.is_symlink():
            raise RuntimeError("LOCAL_CHANGE_REQUIRES_REVIEW " + name)
        current = file.read_bytes()
        remote = git(path, "show", target + ":" + name, check=False)
        if remote.returncode or normalize(current) != normalize(remote.stdout):
            raise RuntimeError("DIVERGENT_LOCAL_FILE_PRESERVED " + name)
        destination = backup / "already_upstream" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(current)
        preserved.append({"path": name, "sha256": hashlib.sha256(current).hexdigest()})
    # Reset only clean files or exact equivalents already present upstream.
    # Spool evidence lives outside these disposable code/runtime checkouts.
    git(path, "reset", "--hard", target)
    after = git(path, "rev-parse", "HEAD").stdout.decode().strip()
    if git(path, "status", "--porcelain=v1", "-z").stdout:
        raise RuntimeError("POST_SYNC_CHECKOUT_NOT_CLEAN")
    receipt = {"branch": branch, "before": before, "after": after,
               "null_shallow_recovered": repaired, "preserved_upstream_files": preserved,
               "backup": str(backup), "status": "SYNC_PASS", "collector_executed": False}
    backup.mkdir(parents=True, exist_ok=True)
    (backup / "receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", type=Path, required=True)
    ap.add_argument("--branch", choices=("main", "gate-btc-runtime"), required=True)
    ap.add_argument("--backup-root", type=Path, required=True)
    args = ap.parse_args()
    print(json.dumps(sync(args.path, args.branch, args.backup_root), sort_keys=True))


if __name__ == "__main__":
    main()
