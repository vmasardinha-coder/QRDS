"""QRDS workspace housekeeping utilities.

This module is intentionally non-operational. It only cleans local development
caches, reinforces generated-artifact ignore rules, and reports repository status.
It never touches exchange credentials, authenticated accounts, orders, signals,
allocations, or capital.
"""

from __future__ import annotations

import fnmatch
import hashlib
import html
import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

APP_MODE = "INTERACTIVE_RESEARCH_ONLY"
REPORT_NAME = "qrds-workspace-housekeeping"
SCHEMA = "qrds.workspace_housekeeping.v1"

REQUIRED_GITIGNORE_LINES: tuple[str, ...] = (
    "# QRDS generated local artifacts",
    "artifacts/",
    "crypto_decision_lab/artifacts/",
    ".pytest_cache/",
    "**/.pytest_cache/",
    "**/__pycache__/",
    "*.pyc",
    "qrds_sprint_*.sh",
)

SAFE_CACHE_DIR_NAMES: tuple[str, ...] = ("__pycache__", ".pytest_cache")
SAFE_CACHE_FILE_PATTERNS: tuple[str, ...] = ("*.pyc", "*.pyo")
GENERATED_ARTIFACT_DIRS: tuple[str, ...] = ("artifacts", "crypto_decision_lab/artifacts")

SAFETY_FLAGS: dict[str, object] = {
    "app_mode": APP_MODE,
    "research_allowed": True,
    "hypothetical_only": True,
    "api_key_required": False,
    "api_key_present": False,
    "account_connection_required": False,
    "authenticated_connection_used": False,
    "orders_allowed": False,
    "orders_generated": False,
    "real_orders_generated": False,
    "real_capital_used": False,
    "trading_signal_generated": False,
    "executable_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "portfolio_decision_generated": False,
    "operational_decision_allowed": False,
}


@dataclass(frozen=True)
class HousekeepingResult:
    schema: str
    report_name: str
    generated_at: str
    repo_root: str
    dry_run: bool
    clean_artifacts: bool
    gitignore_updated: bool
    gitignore_missing_before: list[str]
    removed_path_count: int
    removed_paths: list[str]
    skipped_artifact_paths: list[str]
    git_status_short: list[str]
    untracked_count: int
    untracked_sprint_installers: list[str]
    suspicious_untracked: list[str]
    report_payload_sha256: str
    json_path: str
    markdown_path: str
    html_path: str
    gate_answer: str
    policy_lock: str
    app_mode: str
    research_allowed: bool
    hypothetical_only: bool
    api_key_required: bool
    api_key_present: bool
    account_connection_required: bool
    authenticated_connection_used: bool
    orders_allowed: bool
    orders_generated: bool
    real_orders_generated: bool
    real_capital_used: bool
    trading_signal_generated: bool
    executable_signal_generated: bool
    recommendation_generated: bool
    allocation_generated: bool
    portfolio_decision_generated: bool
    operational_decision_allowed: bool
    safety_flags: dict[str, object]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_sha256(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def normalize_repo_root(repo_root: str | Path) -> Path:
    root = Path(repo_root).expanduser().resolve()
    if not (root / "crypto_decision_lab" / "src" / "crypto_decision_lab").exists():
        raise FileNotFoundError(f"QRDS repo root not found: {root}")
    return root


def _is_inside_git_dir(path: Path) -> bool:
    return ".git" in path.parts


def discover_cache_paths(repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    for current, dirs, files in os.walk(repo_root):
        current_path = Path(current)
        if _is_inside_git_dir(current_path):
            dirs[:] = []
            continue

        for name in list(dirs):
            if name in SAFE_CACHE_DIR_NAMES:
                paths.append(current_path / name)
                # No need to descend into a dir that will be removed.
                dirs.remove(name)

        for filename in files:
            if any(fnmatch.fnmatch(filename, pattern) for pattern in SAFE_CACHE_FILE_PATTERNS):
                paths.append(current_path / filename)
    return sorted(set(paths), key=lambda p: str(p))


def remove_paths(paths: Iterable[Path], *, dry_run: bool) -> list[str]:
    removed: list[str] = []
    for path in paths:
        if not path.exists():
            continue
        removed.append(str(path))
        if dry_run:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
    return removed


def ensure_gitignore(repo_root: Path, *, dry_run: bool) -> tuple[bool, list[str]]:
    gitignore = repo_root / ".gitignore"
    existing = gitignore.read_text(encoding="utf-8").splitlines() if gitignore.exists() else []
    existing_set = {line.strip() for line in existing}
    missing = [line for line in REQUIRED_GITIGNORE_LINES if line.strip() not in existing_set]
    if missing and not dry_run:
        prefix = "\n" if existing and existing[-1].strip() else ""
        with gitignore.open("a", encoding="utf-8") as fh:
            fh.write(prefix)
            for line in missing:
                fh.write(f"{line}\n")
    return bool(missing), missing


def git_status(repo_root: Path) -> list[str]:
    try:
        proc = subprocess.run(
            ["git", "status", "--short"],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return ["GIT_STATUS_UNAVAILABLE"]
    if proc.returncode != 0:
        return [f"GIT_STATUS_ERROR: {proc.stderr.strip()}"]
    return [line for line in proc.stdout.splitlines() if line.strip()]


def classify_status(status_lines: Sequence[str]) -> tuple[list[str], list[str]]:
    sprint_installers: list[str] = []
    suspicious: list[str] = []
    for line in status_lines:
        if not line.startswith("?? "):
            continue
        path = line[3:].strip()
        if fnmatch.fnmatch(Path(path).name, "qrds_sprint_*.sh"):
            sprint_installers.append(path)
        elif path.startswith("artifacts/") or path.startswith("crypto_decision_lab/artifacts/"):
            # Should become ignored after .gitignore update; keep out of suspicious list.
            continue
        elif "__pycache__" in path or ".pytest_cache" in path or path.endswith((".pyc", ".pyo")):
            continue
        else:
            suspicious.append(path)
    return sprint_installers, suspicious


def artifact_paths(repo_root: Path) -> list[Path]:
    return [repo_root / rel for rel in GENERATED_ARTIFACT_DIRS if (repo_root / rel).exists()]


def gate_answer_for(suspicious_untracked: Sequence[str], dry_run: bool) -> str:
    if dry_run:
        return "WORKSPACE_HOUSEKEEPING_DRY_RUN_RESEARCH_ONLY"
    if suspicious_untracked:
        return "WORKSPACE_HOUSEKEEPING_COMPLETED_WITH_UNTRACKED_REVIEW_REQUIRED_RESEARCH_ONLY"
    return "WORKSPACE_HOUSEKEEPING_COMPLETED_POLICY_LOCK_ACTIVE_RESEARCH_ONLY"


def render_markdown(result: dict[str, object]) -> str:
    status_lines = result.get("git_status_short", [])
    removed_paths = result.get("removed_paths", [])
    suspicious = result.get("suspicious_untracked", [])
    installers = result.get("untracked_sprint_installers", [])
    missing_before = result.get("gitignore_missing_before", [])

    def bullet(items: object, empty: str = "None") -> str:
        seq = list(items) if isinstance(items, list) else []
        if not seq:
            return f"- {empty}\n"
        return "".join(f"- `{item}`\n" for item in seq)

    return f"""# QRDS/QOS Workspace Housekeeping

Research-only workspace hygiene report. This page cleans development caches and reports Git status; it cannot unlock trading, allocation, orders, or real-capital use.

**Gate answer:** `{result['gate_answer']}`  
**Policy lock:** `{result['policy_lock']}`  
**Mode:** `{result['app_mode']}`  
**Dry run:** `{result['dry_run']}`  
**Clean artifacts:** `{result['clean_artifacts']}`  

## Summary

| Field | Value |
|---|---:|
| Removed paths | {result['removed_path_count']} |
| Gitignore updated | {result['gitignore_updated']} |
| Git status rows | {len(status_lines)} |
| Untracked sprint installers | {len(installers)} |
| Suspicious untracked | {len(suspicious)} |

## Removed cache paths

{bullet(removed_paths, 'No cache paths removed')}

## Gitignore lines added or missing before this run

{bullet(missing_before, 'No missing gitignore lines')}

## Untracked sprint installers

These are safe to leave untracked because `.gitignore` now ignores `qrds_sprint_*.sh` installer files.

{bullet(installers, 'No untracked sprint installers detected')}

## Suspicious untracked files requiring review

{bullet(suspicious, 'No suspicious untracked files detected')}

## Git status --short

```text
{chr(10).join(status_lines) if status_lines else 'clean or ignored-only'}
```

## Safety flags

| Flag | Value |
|---|---:|
""" + "\n".join(f"| `{k}` | `{v}` |" for k, v in SAFETY_FLAGS.items()) + "\n"


def render_html(result: dict[str, object]) -> str:
    status_lines = result.get("git_status_short", [])
    suspicious = result.get("suspicious_untracked", [])
    installers = result.get("untracked_sprint_installers", [])
    removed_paths = result.get("removed_paths", [])

    def rows(items: object) -> str:
        seq = list(items) if isinstance(items, list) else []
        if not seq:
            return "<tr><td>None</td></tr>"
        return "".join(f"<tr><td><code>{html.escape(str(item))}</code></td></tr>" for item in seq)

    status_pre = html.escape("\n".join(status_lines) if status_lines else "clean or ignored-only")
    safety_rows = "".join(
        f"<tr><td><code>{html.escape(str(k))}</code></td><td>{html.escape(str(v))}</td></tr>"
        for k, v in SAFETY_FLAGS.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>QRDS Workspace Housekeeping</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f6f7fb; color: #18202f; }}
    header {{ background: #162033; color: white; padding: 28px 34px; }}
    main {{ padding: 24px 34px; max-width: 1180px; margin: auto; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin: 20px 0; }}
    .card {{ background: white; border-radius: 12px; padding: 18px; box-shadow: 0 1px 6px rgba(0,0,0,.08); }}
    .label {{ color: #5d687c; font-size: 13px; }}
    .value {{ font-size: 24px; font-weight: 700; margin-top: 8px; }}
    .good {{ color: #0b6b3a; }} .warn {{ color: #9a5b00; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 12px; overflow: hidden; margin: 14px 0 26px; }}
    th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #edf0f5; vertical-align: top; }}
    th {{ background: #eef2f8; }}
    code, pre {{ background: #eef2f8; padding: 2px 5px; border-radius: 5px; }}
    pre {{ padding: 14px; overflow:auto; }}
  </style>
</head>
<body>
  <header>
    <div>QRDS/QOS • Gate BTC • Research-only</div>
    <h1>Workspace Housekeeping</h1>
    <p>Local hygiene report for caches, generated artifacts, sprint installers, and Git status. This layer cannot unlock operational use.</p>
  </header>
  <main>
    <h2>Gate answer</h2>
    <p><code>{html.escape(str(result['gate_answer']))}</code></p>
    <p><strong>Policy lock:</strong> {html.escape(str(result['policy_lock']))} • <strong>Mode:</strong> {html.escape(str(result['app_mode']))}</p>
    <div class="grid">
      <div class="card"><div class="label">Removed paths</div><div class="value">{result['removed_path_count']}</div></div>
      <div class="card"><div class="label">Gitignore updated</div><div class="value">{result['gitignore_updated']}</div></div>
      <div class="card"><div class="label">Untracked sprint installers</div><div class="value">{len(installers)}</div></div>
      <div class="card"><div class="label">Suspicious untracked</div><div class="value {'warn' if suspicious else 'good'}">{len(suspicious)}</div></div>
    </div>
    <h2>Suspicious untracked files requiring review</h2><table>{rows(suspicious)}</table>
    <h2>Untracked sprint installers</h2><table>{rows(installers)}</table>
    <h2>Removed cache paths</h2><table>{rows(removed_paths)}</table>
    <h2>Git status --short</h2><pre>{status_pre}</pre>
    <h2>Safety flags</h2><table><tr><th>flag</th><th>value</th></tr>{safety_rows}</table>
    <p>Generated at {html.escape(str(result['generated_at']))} • SHA256 {html.escape(str(result['report_payload_sha256']))}</p>
  </main>
</body>
</html>
"""


def build_workspace_housekeeping(
    repo_root: str | Path,
    output_dir: str | Path = "artifacts/workspace_housekeeping",
    *,
    dry_run: bool = False,
    clean_artifacts: bool = False,
    update_gitignore: bool = True,
) -> HousekeepingResult:
    root = normalize_repo_root(repo_root)
    out = Path(output_dir)
    if not out.is_absolute():
        out = root / "crypto_decision_lab" / out
    out.mkdir(parents=True, exist_ok=True)

    cache_paths = discover_cache_paths(root)
    artifact_candidates = artifact_paths(root)
    skipped_artifacts = [str(p) for p in artifact_candidates]
    paths_to_remove = list(cache_paths)
    if clean_artifacts:
        paths_to_remove.extend(artifact_candidates)
        skipped_artifacts = []

    removed = remove_paths(paths_to_remove, dry_run=dry_run)
    gitignore_updated = False
    missing_before: list[str] = []
    if update_gitignore:
        gitignore_updated, missing_before = ensure_gitignore(root, dry_run=dry_run)

    status_lines = git_status(root)
    installers, suspicious = classify_status(status_lines)

    payload: dict[str, object] = {
        "schema": SCHEMA,
        "report_name": REPORT_NAME,
        "generated_at": utc_now_iso(),
        "repo_root": str(root),
        "dry_run": dry_run,
        "clean_artifacts": clean_artifacts,
        "gitignore_updated": gitignore_updated,
        "gitignore_missing_before": missing_before,
        "removed_path_count": len(removed),
        "removed_paths": removed,
        "skipped_artifact_paths": skipped_artifacts,
        "git_status_short": status_lines,
        "untracked_count": sum(1 for line in status_lines if line.startswith("?? ")),
        "untracked_sprint_installers": installers,
        "suspicious_untracked": suspicious,
        "gate_answer": gate_answer_for(suspicious, dry_run),
        "policy_lock": "ACTIVE",
        **SAFETY_FLAGS,
        "safety_flags": SAFETY_FLAGS,
    }
    payload["report_payload_sha256"] = stable_sha256(payload)

    json_path = out / "workspace_housekeeping.json"
    markdown_path = out / "workspace_housekeeping.md"
    html_path = out / "index.html"
    payload["json_path"] = str(json_path.relative_to(root / "crypto_decision_lab"))
    payload["markdown_path"] = str(markdown_path.relative_to(root / "crypto_decision_lab"))
    payload["html_path"] = str(html_path.relative_to(root / "crypto_decision_lab"))

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    html_path.write_text(render_html(payload), encoding="utf-8")

    return HousekeepingResult(**payload)  # type: ignore[arg-type]


__all__ = [
    "APP_MODE",
    "REQUIRED_GITIGNORE_LINES",
    "SAFETY_FLAGS",
    "HousekeepingResult",
    "build_workspace_housekeeping",
    "classify_status",
    "discover_cache_paths",
    "ensure_gitignore",
]
