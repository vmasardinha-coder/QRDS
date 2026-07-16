from __future__ import annotations

import hashlib
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(os.environ.get("QRDS_PROJECT_ROOT", Path(__file__).resolve().parents[3])).resolve()
GIT_ROOT = Path(os.environ.get("QRDS_GIT_ROOT", ROOT.parent)).resolve()

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

FAMILY_ID = "ABSTENTION_QUALITY_DIVERGENCE_H8_V1"
EXPECTED_TEMPLATE_COUNT = 12
BASELINE_PHASE345_HEAD = "e416079112804e516d910ee47ea9fe16bb34e5fe"
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
            raise RuntimeError(f"Safety lock mismatch at Phase {expected_phase}: {key}={locks.get(key)!r}, expected {expected!r}.")
    if payload.get("strategy_approved") is not False:
        raise RuntimeError(f"Phase {expected_phase} unexpectedly approved a strategy.")


def phase_artifact(phase: int, slug: str) -> Path:
    return ROOT / "artifacts" / f"phase{phase}_{slug}_research_only" / f"phase{phase}_{slug}.json"


def phase_summary(phase: int, slug: str) -> Path:
    return ROOT / "docs" / "reports" / "closure_navigation_v1" / f"phase{phase}_{slug}_summary.md"


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


def portal_phase_from_path(path: Path) -> int:
    for part in path.parts:
        match = re.search(r"phase(\d+)", part, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return -1


def project_relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def discover_portals(root: Path | None = None) -> list[dict[str, Any]]:
    project_root = (root or ROOT).resolve()
    candidates: list[Path] = []
    artifacts = project_root / "artifacts"
    if artifacts.is_dir():
        candidates.extend(artifacts.glob("phase*/portal/index.html"))
        candidates.extend(artifacts.glob("**/portal/index.html"))
    unique = sorted({item.resolve() for item in candidates if item.is_file()})
    records: list[dict[str, Any]] = []
    for path in unique:
        try:
            relative = path.relative_to(project_root).as_posix()
        except ValueError:
            continue
        records.append(
            {
                "phase": portal_phase_from_path(Path(relative)),
                "relative_path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
        )
    records.sort(key=lambda item: (int(item["phase"]), item["relative_path"]))
    return records


def ensure_required_headings(text: str) -> None:
    missing = [heading for heading in REQUIRED_PORTAL_HEADINGS if heading not in text]
    if missing:
        raise RuntimeError("Portal is missing required headings: " + ", ".join(missing))
    if "VOCE ESTA AQUI" not in text:
        raise RuntimeError("Portal is missing VOCE ESTA AQUI marker.")


def html_page(*, title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang=\"pt-BR\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>{html.escape(title)}</title>
<style>
:root{{--bg:#0b1020;--card:#131b31;--line:#2b395f;--text:#f4f7ff;--muted:#b9c4df;--ok:#66e3a4;--warn:#ffd166;--bad:#ff7a90;--accent:#7db4ff}}
*{{box-sizing:border-box}} body{{margin:0;background:linear-gradient(180deg,#080d1a,#10172a);color:var(--text);font:16px/1.55 system-ui,Segoe UI,Arial,sans-serif}}
main{{max-width:1180px;margin:auto;padding:24px}} h1{{font-size:clamp(2rem,4vw,3.4rem);margin:.2rem 0}} h2{{margin-top:0;font-size:1.15rem;letter-spacing:.03em}} .hero{{border:1px solid var(--line);background:#10182c;padding:24px;border-radius:20px;margin-bottom:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}} .card{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px}} .status{{display:inline-block;padding:6px 10px;border-radius:999px;background:#291827;color:#ff9caf;font-weight:700}} .ok{{color:var(--ok)}} .warn{{color:var(--warn)}} .bad{{color:var(--bad)}} code{{background:#0a1020;padding:2px 6px;border-radius:6px}} a{{color:var(--accent)}} pre{{white-space:pre-wrap;background:#080e1c;border:1px solid var(--line);padding:16px;border-radius:14px}} ul{{padding-left:20px}} .top{{display:grid;grid-template-columns:2fr 1fr;gap:16px}} @media(max-width:800px){{.top{{grid-template-columns:1fr}}}}
</style>
</head>
<body><main>{body}</main></body></html>"""


def update_marked_block(path: Path, *, begin: str, end: str, block: str, default_title: str) -> Path:
    existing = path.read_text(encoding="utf-8-sig") if path.is_file() else default_title.rstrip() + "\n"
    replacement = f"{begin}\n{block.rstrip()}\n{end}"
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end), flags=re.DOTALL)
    if pattern.search(existing):
        updated = pattern.sub(replacement, existing)
    else:
        updated = existing.rstrip() + "\n\n" + replacement + "\n"
    return write_text(path, updated)
