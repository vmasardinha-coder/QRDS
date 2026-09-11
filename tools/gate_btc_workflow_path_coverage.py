#!/usr/bin/env python3
"""Find workflows whose `paths:` filter misses a module their own tools import.

The defect this catches, stated once: a workflow lists `tools/X.py` in the
`paths:` filter of its pull_request/push trigger, `X.py` imports `tools/Y.py`,
and `Y.py` is not in the list. A pull request that touches only `Y.py` then
reaches main without that workflow ever running. PR #643 entered main exactly
this way, and on 2026-09-11 the Daily Research collection was stopped by a
fail-closed guard living in `gate_btc_measurement_common.py`, a module the
collection workflow did not watch.

Reporting only: reads files, writes nothing, touches no network.

No YAML library on purpose. The contract-tests jobs run on a bare
actions/setup-python with no pip install, so a third-party import here would
either fail the job or, worse, get wrapped in a skip and protect nothing. The
reader below is deliberately narrow: it understands the exact shape these
workflows use and raises on anything else rather than returning a quiet empty
set, because a scanner that silently finds nothing is the failure mode that
matters.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

SCHEMA = "gate_btc.workflow_path_coverage.v1"

IMPORT_PATTERN = re.compile(
    r"^\s*(?:from\s+tools\.(\w+)\s+import|import\s+tools\.(\w+))", re.MULTILINE)

TRIGGERS_WITH_PATHS = ("pull_request", "push")


class CoverageError(RuntimeError):
    pass


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_item(raw: str) -> str:
    """Turn a `- 'tools/x.py'  # note` list item into `tools/x.py`."""
    item = raw.strip()
    if not item.startswith("- "):
        raise CoverageError(f"not a list item: {raw!r}")
    item = item[2:].strip()
    # A quoted value may legitimately contain '#', so only strip a comment that
    # follows unquoted text.
    if item[:1] in {"'", '"'}:
        quote = item[0]
        end = item.find(quote, 1)
        if end == -1:
            raise CoverageError(f"unterminated quote: {raw!r}")
        return item[1:end]
    return item.split("#", 1)[0].strip()


def trigger_paths(text: str) -> dict[str, list[str]]:
    """Return {trigger: paths} for the pull_request/push filters of one workflow.

    Only the `on:` block is read. A `paths:` key anywhere else in the file — a
    step input, for instance — must not be mistaken for a trigger filter, so the
    walk tracks which trigger it is inside and leaves the block when indentation
    returns to the trigger level.
    """
    lines = text.splitlines()
    start = None
    for index, line in enumerate(lines):
        if re.match(r"^on:\s*$", line) or re.match(r"^on:\s*\S", line):
            start = index
            break
    if start is None:
        return {}
    found: dict[str, list[str]] = {}
    trigger = None
    trigger_indent = None
    collecting = False
    collect_indent = None
    for line in lines[start + 1:]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        indent = _indent(line)
        if indent == 0:  # left the on: block entirely
            break
        stripped = line.strip()
        if collecting:
            if stripped.startswith("- ") and indent >= collect_indent:
                found[trigger].append(_strip_item(line))
                continue
            collecting = False
        name = stripped.split(":", 1)[0]
        if trigger_indent is None or indent == trigger_indent:
            if name in TRIGGERS_WITH_PATHS:
                trigger, trigger_indent = name, indent
                found.setdefault(trigger, [])
                continue
            if not stripped.startswith("- "):
                trigger_indent = indent if trigger_indent is None else trigger_indent
                if name not in TRIGGERS_WITH_PATHS:
                    trigger = None
                continue
        if trigger and name == "paths" and (trigger_indent is None or indent > trigger_indent):
            collecting = True
            collect_indent = indent
    return {key: value for key, value in found.items() if value}


def tool_imports(tool: Path) -> set[str]:
    """Sibling tools/ modules this file imports, as repo-relative paths."""
    found: set[str] = set()
    for match in IMPORT_PATTERN.finditer(tool.read_text(encoding="utf-8-sig")):
        name = match.group(1) or match.group(2)
        found.add(f"tools/{name}.py")
    return found


def scan(root: Path) -> list[dict[str, str]]:
    """Every (workflow, importer, missing) triple, sorted for stable output.

    The walk is TRANSITIVE, and that is the whole point. A first version looked
    only at the direct imports of listed tools; closing two gaps on 2026-09-11
    immediately revealed a third, because the module just added to the filter
    imports one of its own. A backlog that grows every time you shrink it is
    useless for planning, so the closure is taken up front: if a workflow's code
    can reach a module, that module belongs in the filter.
    """
    gaps: set[tuple[str, str, str]] = set()
    for workflow in sorted((root / ".github" / "workflows").glob("*.yml")):
        by_trigger = trigger_paths(workflow.read_text(encoding="utf-8-sig"))
        watched = {path for paths in by_trigger.values() for path in paths}
        roots = [p for p in sorted(watched)
                 if p.startswith("tools/") and p.endswith(".py") and (root / p).is_file()]
        seen: set[str] = set()
        queue = list(roots)
        while queue:
            current = queue.pop()
            if current in seen:
                continue
            seen.add(current)
            for dependency in sorted(tool_imports(root / current)):
                if not (root / dependency).is_file():
                    continue
                if dependency not in watched:
                    gaps.add((workflow.name, current, dependency))
                if dependency not in seen:
                    queue.append(dependency)
    return [{"workflow": w, "listed": l, "missing": m} for w, l, m in sorted(gaps)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    gaps = scan(args.root)
    print(json.dumps({"schema": SCHEMA, "reporting_only": True,
                      "gap_count": len(gaps), "gaps": gaps}, indent=2, sort_keys=True))
    # Listing is not itself a failure: the test owns the verdict, and the known
    # backlog lives there where it is reviewed, not in this scanner.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
