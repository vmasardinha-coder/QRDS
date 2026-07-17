from __future__ import annotations

import ast
import csv
import gzip
import hashlib
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(os.environ.get("QRDS_PROJECT_ROOT", Path(__file__).resolve().parents[3])).resolve()
GIT_ROOT = Path(os.environ.get("QRDS_GIT_ROOT", ROOT.parent)).resolve()
BASELINE_PHASE375_HEAD = "77a2e0cc022e69ae948ac401b78fce0d19e4435a"

LOCKS: dict[str, Any] = {
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "action_status": "NO_ACTION_RESEARCH_ONLY",
    "decision_layer_allowed": False,
    "canonical_data_writes": 0,
    "account_connection_allowed": False,
    "private_api_allowed": False,
    "orders_allowed": False,
    "capital_allowed": False,
    "position_size": 0,
    "capital_used": 0,
    "real_orders_created": 0,
}

ADOPTION_DECISIONS = (
    "ADOPT_AS_NONCANONICAL_RESEARCH_INPUT_ONLY",
    "PRESERVE_CANDIDATE_UNADOPTED",
)

CANDIDATE_SCHEMA = (
    "open_time_ms",
    "open_time_utc",
    "provider_count",
    "providers",
    "consensus_close",
    "spread_bps",
)

REQUIRED_PORTAL_HEADINGS = (
    "O QUE FOI COLETADO",
    "O QUE FOI TESTADO",
    "QUAL ERA A PERGUNTA",
    "O QUE O RESULTADO SIGNIFICA",
    "EXEMPLO COM R$10.000",
    "POR QUE FOI REPROVADO OU APROVADO",
    "O QUE O TESTE NAO PROVA",
    "CONCLUSAO PRATICA",
)

OBSERVED_FAILURE_CLASSES = (
    "POWERSHELL_REGEX_BACKSLASH",
    "PYTHON_REGEX_REPLACEMENT_BACKSLASH",
    "POWERSHELL_ARRAY_FLATTENING",
    "VACUOUS_ALL_TRUE_WITH_ZERO_INPUTS",
    "STALE_DECISION_REUSE",
    "FALSE_RESUME_BY_COMMIT_SUBJECT_ONLY",
    "OBSOLETE_REMOTE_BASELINE",
    "GIT_STDOUT_CONTAMINATES_HASH",
    "SCHEMA_DRIFT_BETWEEN_PHASES",
    "GENERIC_CHECKPOINT_FAILURE_WITHOUT_FAILED_CHECKS",
    "WINDOWS_POWERSHELL_PARSEFILE_REF_TYPE",
    "WINDOWS_POWERSHELL_GENERIC_LIST_COERCION",
)

FORBIDDEN_LITERAL_PATTERNS = (
    '-replace "\\","/"',
    "pattern.sub(replacement",
    "$entry[0]",
    "$entry[1]",
    "$remote -ne $expectedPhase",
    "PHASE366_MANUAL_DECISION_REUSED:",
    "$tokens=$null; $parseErrors=$null",
    "$tokens = $null",
    "System.Collections.Generic.List[object]",
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return path


def base_payload(phase: int, status: str) -> dict[str, Any]:
    return {
        "project": "QRDS/QOS/GATE BTC",
        "phase": phase,
        "generated_at_utc": utc_now_iso(),
        "status": status,
        "locks": dict(LOCKS),
        "historical_result_authorizes_execution": False,
        "strategy_approved": False,
        "forward_shadow_eligible": False,
        "forward_shadow_started": False,
        "paper_trading_started": False,
    }


def validate_phase(payload: dict[str, Any], expected_phase: int) -> None:
    if int(payload.get("phase", -1)) != expected_phase:
        raise RuntimeError(f"Expected Phase {expected_phase}, found {payload.get('phase')}.")
    locks = payload.get("locks", {})
    for key, expected in LOCKS.items():
        if locks.get(key) != expected:
            raise RuntimeError(
                f"Safety lock mismatch at Phase {expected_phase}: {key}={locks.get(key)!r}, expected {expected!r}."
            )
    if payload.get("strategy_approved") is not False:
        raise RuntimeError(f"Phase {expected_phase} unexpectedly approved a strategy.")


def resolve_recorded_path(root: Path, recorded: str | None) -> Path | None:
    if not recorded:
        return None
    normalized = str(recorded).replace("\\", "/")
    raw = Path(normalized)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend((root / raw, root.parent / raw))
        prefix = "crypto_decision_lab/"
        if normalized.lower().startswith(prefix):
            candidates.append(root / Path(normalized[len(prefix):]))
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved.is_file():
            return resolved
    return candidates[0].resolve() if candidates else None


def relative_to_project(path: Path, root: Path = ROOT) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def phase_summary(phase: int, slug: str) -> Path:
    return ROOT / "docs/reports/remediated_dataset_adoption" / f"phase{phase}_{slug}_summary.md"


def write_summary(path: Path, *, title: str, gate: str, bullets: Iterable[str]) -> Path:
    body = [f"# {title}", "", f"Gate: `{gate}`", ""]
    body.extend(f"- {item}" for item in bullets)
    body.extend([
        "", "## Permanent locks", "",
        "- Operational: `BLOCKED_RESEARCH_ONLY`",
        "- Action: `NO_ACTION_RESEARCH_ONLY`",
        "- Decision layer: `False`",
        "- Canonical data writes: `0`",
        "- Position size: `0`",
        "- Capital used: `R$ 0`",
    ])
    return write_text(path, "\n".join(body))


def parse_junit(path: Path) -> dict[str, Any]:
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(float(suite.attrib.get(key, "0") or "0"))
    totals["passed"] = totals["failures"] == 0 and totals["errors"] == 0
    return totals


def ensure_required_headings(text: str) -> None:
    missing = [heading for heading in REQUIRED_PORTAL_HEADINGS if heading not in text]
    if missing:
        raise RuntimeError("Portal is missing required headings: " + ", ".join(missing))
    if "VOCE ESTA AQUI" not in text:
        raise RuntimeError("Portal is missing VOCE ESTA AQUI marker.")


def html_page(*, title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title><style>
:root{{--bg:#0b1020;--card:#131b31;--line:#2b395f;--text:#f4f7ff;--muted:#b9c4df;--ok:#66e3a4;--warn:#ffd166;--bad:#ff7a90;--accent:#7db4ff}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(180deg,#080d1a,#10172a);color:var(--text);font:16px/1.55 system-ui,Segoe UI,Arial,sans-serif}}
main{{max-width:1180px;margin:auto;padding:24px}} h1{{font-size:clamp(2rem,4vw,3.4rem);margin:.2rem 0}} h2{{margin-top:0;font-size:1.15rem}}
.hero{{border:1px solid var(--line);background:#10182c;padding:24px;border-radius:20px;margin-bottom:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}} .card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px}}
.status{{display:inline-block;padding:6px 10px;border-radius:999px;background:#291827;color:#ff9caf;font-weight:700}} code{{background:#0a1020;padding:2px 6px;border-radius:6px}} a{{color:var(--accent)}}
pre{{white-space:pre-wrap;background:#080e1c;border:1px solid var(--line);padding:16px;border-radius:14px}} .bad{{color:var(--bad)}} .ok{{color:var(--ok)}} .warn{{color:var(--warn)}}
table{{width:100%;border-collapse:collapse}} th,td{{border:1px solid var(--line);padding:9px;text-align:left}}
</style></head><body><main>{body}</main></body></html>"""


def update_marked_block(path: Path, *, begin: str, end: str, block: str, default_title: str) -> Path:
    existing = path.read_text(encoding="utf-8-sig") if path.is_file() else default_title.rstrip() + "\n"
    replacement = f"{begin}\n{block.rstrip()}\n{end}"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), flags=re.DOTALL)
    updated = pattern.sub(lambda _match: replacement, existing) if pattern.search(existing) else existing.rstrip() + "\n\n" + replacement + "\n"
    return write_text(path, updated)


def read_gzip_header(path: Path) -> tuple[str, ...]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        return tuple(next(reader))


def stream_candidate_rows(path: Path) -> Iterable[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)


def python_syntax_check(paths: Sequence[Path]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in paths:
        try:
            ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
        except SyntaxError as exc:
            findings.append({"path": str(path), "line": exc.lineno, "message": str(exc)})
    return findings


def scan_for_observed_patterns(paths: Sequence[Path]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in paths:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        scan_text = text
        if path.name == "phase376_385_remediated_dataset_adoption_common.py" and "def utc_now_iso" in text:
            scan_text = text.split("def utc_now_iso", 1)[1]
        for literal in FORBIDDEN_LITERAL_PATTERNS:
            if literal in scan_text:
                findings.append({"path": str(path), "class": "FORBIDDEN_LITERAL", "literal": literal})
        if path.suffix == ".py" and "all(item[\"verified\"] for item in manifest)" in text and "bool(manifest) and" not in text:
            findings.append({"path": str(path), "class": "VACUOUS_ALL_TRUE_WITH_ZERO_INPUTS"})
        if path.suffix == ".py" and "raise RuntimeError(\"" in text and "failed_checks" not in text and "checkpoint" in path.name:
            findings.append({"path": str(path), "class": "GENERIC_CHECKPOINT_DIAGNOSTIC"})
    return findings
