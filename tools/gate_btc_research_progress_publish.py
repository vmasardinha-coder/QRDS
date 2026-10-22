"""Publish only the two isolated research lanes; refuse all other staged paths."""
import argparse
import json
import subprocess
import time
from pathlib import Path

SCOPES = ("runtime/factory_autonomy/xagent_economics/F-XAGENT-DISAGREE-SPOT-CONTINUOUS-V1/",
          "runtime/gate_btc_2/system13/observed_panel_v1/")


def call(repo, *args, check=True):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and p.returncode:
        raise RuntimeError("RESEARCH_PUBLICATION_GIT_FAILED:" + args[0])
    return p


def publish(repo):
    for scope in SCOPES:
        if (repo / scope).exists():
            call(repo, "add", "--", scope.rstrip("/"))
    paths = call(repo, "diff", "--cached", "--name-only").stdout.splitlines()
    if any(not p.startswith(SCOPES) for p in paths):
        raise RuntimeError("RESEARCH_PUBLICATION_SCOPE_VIOLATION")
    if not paths:
        return {"changed": False, "sha": call(repo, "rev-parse", "HEAD").stdout.strip()}
    call(repo, "config", "user.name", "gate-btc-research-bot")
    call(repo, "config", "user.email", "gate-btc-research-bot@users.noreply.github.com")
    call(repo, "commit", "-m", "Isolated XAGENT experiment and System13 panel evidence")
    for attempt in range(4):
        call(repo, "fetch", "origin", "gate-btc-runtime")
        rebased = call(repo, "rebase", "origin/gate-btc-runtime", check=False)
        if rebased.returncode:
            call(repo, "rebase", "--abort", check=False)
            raise RuntimeError("RESEARCH_PUBLICATION_REBASE_CONFLICT")
        if call(repo, "push", "origin", "HEAD:gate-btc-runtime", check=False).returncode == 0:
            return {"changed": True, "sha": call(repo, "rev-parse", "HEAD").stdout.strip(), "paths": paths}
        time.sleep(attempt + 1)
    raise RuntimeError("RESEARCH_PUBLICATION_RETRY_EXHAUSTED")


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--repository", type=Path, required=True)
    a = p.parse_args(); print(json.dumps(publish(a.repository), sort_keys=True))
