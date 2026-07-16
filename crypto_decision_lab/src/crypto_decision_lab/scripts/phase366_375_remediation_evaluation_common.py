from __future__ import annotations

import csv
import gzip
import hashlib
import html
import io
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

ROOT = Path(os.environ.get("QRDS_PROJECT_ROOT", Path(__file__).resolve().parents[3])).resolve()
GIT_ROOT = Path(os.environ.get("QRDS_GIT_ROOT", ROOT.parent)).resolve()
BASELINE_PHASE365_HEAD = "e287076656a76398e1e13effc1abf12a3af3055e"

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

VALID_EXECUTION_REVIEW_DECISIONS = (
    "APPROVE_ONE_FROZEN_REMEDIATION_EVALUATION",
    "REJECT_REAL_DATA_REMEDIATION_EVALUATION",
)

QUALITY_METRIC_NAMES = (
    "TOTAL_UNION_HOURS",
    "STRICT_ALL_PROVIDER_HOURS",
    "VALID_CONSENSUS_HOURS",
    "RAW_VALID_HOUR_RATIO",
    "REMEDIATED_VALID_HOUR_RATIO",
    "RAW_TIMESTAMP_ALIGNMENT_DEFECT_COUNT",
    "REMEDIATED_TIMESTAMP_ALIGNMENT_DEFECT_COUNT",
    "PROVIDER_COUNT_DISTRIBUTION",
    "RAW_STRICT_SPREAD_P95_BPS",
    "REMEDIATED_SPREAD_P95_BPS",
)

FORBIDDEN_CLOSED_FAMILY_METRIC_NAMES = (
    "RETURN",
    "PNL",
    "PROFIT",
    "SHARPE",
    "SORTINO",
    "WIN_RATE",
    "EXPECTANCY",
    "DRAWDOWN",
    "BUY_SIGNAL",
    "SELL_SIGNAL",
    "POSITION_SIZE",
    "ALLOCATION",
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


def phase_summary(phase: int, slug: str) -> Path:
    return ROOT / "docs/reports/data_remediation_v2" / f"phase{phase}_{slug}_summary.md"


def write_summary(path: Path, *, title: str, gate: str, bullets: Iterable[str]) -> Path:
    body = [f"# {title}", "", f"Gate: `{gate}`", ""]
    body.extend(f"- {item}" for item in bullets)
    body.extend(
        [
            "",
            "## Permanent locks",
            "",
            "- Operational: `BLOCKED_RESEARCH_ONLY`",
            "- Action: `NO_ACTION_RESEARCH_ONLY`",
            "- Decision layer: `False`",
            "- Position size: `0`",
            "- Capital used: `R$ 0`",
        ]
    )
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


def read_csv_gz(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def deterministic_csv_gz_bytes(rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> bytes:
    raw = io.StringIO(newline="")
    writer = csv.DictWriter(raw, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    payload = raw.getvalue().encode("utf-8")
    out = io.BytesIO()
    with gzip.GzipFile(fileobj=out, mode="wb", mtime=0) as handle:
        handle.write(payload)
    return out.getvalue()


def write_deterministic_csv_gz(path: Path, rows: Sequence[dict[str, Any]], fieldnames: Sequence[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(deterministic_csv_gz_bytes(rows, fieldnames))
    return path


def percentile(values: Sequence[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(v) for v in values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def iso_from_ms(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000.0, tz=timezone.utc).isoformat().replace("+00:00", "Z")
