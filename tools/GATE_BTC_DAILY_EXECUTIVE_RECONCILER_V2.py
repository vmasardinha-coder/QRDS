#!/usr/bin/env python3
"""Local Daily Executive reconciler v2.

Reporting-only bridge for the Windows collection host. It reconciles the local
D50 / Data Readiness / Collection Coordinator files with the canonical QMASTER
sidecar published on the `gate-btc-runtime` branch.

Safety: RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED. No orders, no engine feed,
no portfolio mutation, no model or parameter changes.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

HOME = Path.home()
DOWNLOADS = HOME / "Downloads"
ROOTS = [
    DOWNLOADS,
    Path(r"C:\GATE_BTC_PROJECT\RUNTIME"),
    Path(os.environ.get("LOCALAPPDATA", str(HOME))) / "GATE_BTC_D50_AUTOPILOT_V2",
]
OUT = DOWNLOADS / "GATE_BTC_DAILY_EXECUTIVE_LATEST.pdf"
STATE = DOWNLOADS / "GATE_BTC_DAILY_EXECUTIVE_LATEST.txt"
DISCOVERY = DOWNLOADS / "GATE_BTC_DAILY_EXECUTIVE_DISCOVERY.txt"
QMASTER_CACHE = DOWNLOADS / "GATE_BTC_QMASTER_LATEST.txt"
REPO = "vmasardinha-coder/QRDS"
RUNTIME_REF = "gate-btc-runtime"


def candidates(pattern: str) -> list[Path]:
    found: list[Path] = []
    for root in ROOTS:
        if not root.exists():
            continue
        try:
            found.extend(p for p in root.rglob(pattern) if p.is_file())
        except (OSError, PermissionError):
            continue
    return sorted(set(found), key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)


def newest(pattern: str) -> Path | None:
    xs = candidates(pattern)
    return xs[0] if xs else None


def text(path: Path | None) -> str:
    if not path or not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def rex(s: str, pat: str, cast=lambda x: x):
    m = re.search(pat, s, re.M)
    if not m:
        return None
    try:
        return cast(m.group(1))
    except Exception:
        return None


def sync_qmaster_from_runtime() -> tuple[Path | None, str]:
    """Prefer a local canonical QMASTER; otherwise pull exact runtime bytes via gh.

    The fetch is reporting-only. Failure is fail-closed: no synthetic QMASTER is
    generated and the Executive remains WARN_INPUT_GAP.
    """
    local = newest("GATE_BTC_QMASTER_LATEST.txt")
    if local:
        return local, "LOCAL_CANONICAL"

    gh = shutil.which("gh")
    if not gh:
        return None, "GH_NOT_AVAILABLE"
    endpoint = f"repos/{REPO}/contents/runtime/GATE_BTC_QMASTER_LATEST.txt?ref={RUNTIME_REF}"
    try:
        cp = subprocess.run(
            [gh, "api", "-H", "Accept: application/vnd.github.raw+json", endpoint],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except Exception as exc:
        return None, f"GH_FETCH_EXCEPTION:{type(exc).__name__}"
    if cp.returncode != 0 or not cp.stdout.strip():
        msg = (cp.stderr or "gh api failed").strip().replace("\n", " ")[:240]
        return None, f"GH_FETCH_FAILED:{msg}"
    try:
        payload = json.loads(cp.stdout)
        if payload.get("status") != "PASS":
            return None, "REMOTE_QMASTER_NOT_PASS"
        if payload.get("research_only") is not True or payload.get("operational_status") != "NOT_APPROVED":
            return None, "REMOTE_QMASTER_SAFETY_MISMATCH"
        if payload.get("orders_generated") != 0 or payload.get("real_capital_used") != 0:
            return None, "REMOTE_QMASTER_OPERATIONAL_MISMATCH"
        QMASTER_CACHE.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return QMASTER_CACHE, "REMOTE_RUNTIME_SYNCED"
    except Exception as exc:
        return None, f"REMOTE_QMASTER_PARSE_FAILED:{type(exc).__name__}"


def load_state() -> dict:
    d50p = newest("GATE_BTC_D50_DAILY_LATEST*.txt")
    readyp = newest("GATE_BTC_DATA_READINESS_REPORT_*.txt")
    coordp = newest("GATE_BTC_COLLECTION_COORDINATOR_LATEST*.txt")
    qmp, qsync = sync_qmaster_from_runtime()

    d50, ready, coord, qraw = text(d50p), text(readyp), text(coordp), text(qmp)
    qstate = None
    if qraw:
        try:
            qstate = json.loads(qraw)
        except json.JSONDecodeError:
            qstate = None

    s = {
        "schema": "gate_btc.daily_executive_reconciler.v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "d50_path": str(d50p or ""),
        "readiness_path": str(readyp or ""),
        "coordinator_path": str(coordp or ""),
        "qmaster_path": str(qmp or ""),
        "qmaster_sync_status": qsync,
        "d50_obs": rex(d50, r"PROSPECTIVE_OBSERVATIONS=(\d+)", int),
        "d50_next": rex(d50, r"NEXT_CHECKPOINT=(\d+)", int),
        "coord_status": rex(coord, r"^STATUS=([A-Z0-9_]+)"),
        "ready_consecutive": rex(ready, r'"latest_consecutive_pass_count":\s*(\d+)', int),
        "ready_required": rex(ready, r'"required_consecutive_pass_count":\s*(\d+)', int),
        "hash_valid": rex(ready, r'"hash_chain_valid":\s*(true|false)', lambda x: x.lower() == "true"),
        "qmaster": qstate,
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "NOT_APPROVED": True,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "ENGINE_FEED": False,
    }

    for key in ["D50_CONTROL", "D50_COST_AWARE", "D50_EXIT_2SIGMA"]:
        block = re.search(r'"' + key + r'"\s*:\s*\{(.*?)\n\s*\}', d50, re.S)
        if block:
            b = block.group(1)
            s[key] = {
                "ret": rex(b, r'"total_return":\s*([-0-9.eE]+)', float),
                "dd": rex(b, r'"max_drawdown":\s*([-0-9.eE]+)', float),
                "cost": rex(b, r'"cumulative_cost_bps":\s*([-0-9.eE]+)', float),
            }

    required = [d50p, readyp, coordp, qmp]
    q_ok = bool(qstate and qstate.get("status") == "PASS")
    s["input_status"] = "PASS" if all(required) and q_ok else "WARN_INPUT_GAP"
    return s


def wrap(c, t, x, y, w, size=8, lead=10):
    words = str(t).split(); line = ""
    c.setFont("Helvetica", size)
    for word in words:
        test = (line + " " + word).strip()
        if stringWidth(test, "Helvetica", size) <= w:
            line = test
        else:
            c.drawString(x, y, line); y -= lead; line = word
    if line:
        c.drawString(x, y, line)
    return y


def render(s: dict) -> None:
    W, H = landscape(A4)
    c = canvas.Canvas(str(OUT), pagesize=(W, H))
    c.setFillColor(colors.HexColor("#12233F")); c.rect(0, H - 38, W, 38, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 12); c.drawString(30, H - 25, "GATE BTC | DAILY EXECUTIVE - LOCAL V2")
    c.setFont("Helvetica", 8); c.drawRightString(W - 30, H - 25, "RESEARCH_ONLY | SHADOW_ONLY | NOT_APPROVED | orders=0 | capital=0")
    c.setFillColor(colors.HexColor("#1F314D")); c.setFont("Helvetica-Bold", 22); c.drawString(34, H - 76, "Posicao diaria reconciliada")
    c.setFont("Helvetica", 10); c.setFillColor(colors.HexColor("#687890"))
    c.drawString(34, H - 95, "QMASTER canonico + D50 + Data Readiness; ausencia continua fail-closed e nunca e preenchida por dado antigo.")

    qm = s.get("qmaster") or {}
    cards = [
        ("COLETA", s.get("coord_status") or "N/A", "#E9F6F1"),
        ("D50", f'{s.get("d50_obs","N/A")}/{s.get("d50_next","30")}', "#FFF5DB"),
        ("READINESS", f'{s.get("ready_consecutive","N/A")}/{s.get("ready_required","7")}', "#FFF5DB"),
        ("QMASTER", qm.get("status", "GAP"), "#E9F6F1" if qm.get("status") == "PASS" else "#FBEAEA"),
    ]
    x = 34
    for title, val, fill in cards:
        c.setFillColor(colors.HexColor(fill)); c.roundRect(x, H - 190, 180, 70, 8, fill=1, stroke=0)
        c.setFillColor(colors.HexColor("#1F314D")); c.setFont("Helvetica-Bold", 8); c.drawString(x + 12, H - 141, title)
        c.setFont("Helvetica-Bold", 15); c.drawString(x + 12, H - 165, str(val)); x += 192

    y = H - 228
    c.setFillColor(colors.HexColor("#1F314D")); c.setFont("Helvetica-Bold", 11); c.drawString(34, y, "QMASTER canonico"); y -= 22
    c.setFont("Helvetica", 9)
    c.drawString(48, y, f'Data as of: {qm.get("data_as_of","N/A")} | rows: {qm.get("rows","N/A")} | symbols: {qm.get("symbols","N/A")} | sync: {s.get("qmaster_sync_status")}'); y -= 25

    c.setFont("Helvetica-Bold", 11); c.drawString(34, y, "Resultados D50"); y -= 22
    for k in ["D50_CONTROL", "D50_COST_AWARE", "D50_EXIT_2SIGMA"]:
        m = s.get(k)
        if m and m.get("ret") is not None:
            c.setFont("Helvetica", 9)
            c.drawString(48, y, f'{k}: retorno {100*m["ret"]:+.2f}% | DD {100*m["dd"]:.2f}% | custo {m["cost"]:.1f} bps'); y -= 18

    y -= 10
    c.setFont("Helvetica-Bold", 11); c.drawString(34, y, "Estado de entrada"); y -= 20
    c.setFont("Helvetica", 9)
    c.drawString(48, y, f'INPUT_STATUS={s.get("input_status")} | HASH_CHAIN_VALID={s.get("hash_valid")}'); y -= 18
    c.drawString(48, y, "Nenhum estado desta pagina autoriza capital real, ordens ou promocao operacional.")

    c.setFillColor(colors.HexColor("#E9F6F1")); c.roundRect(34, 55, 756, 54, 8, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#1F314D")); c.setFont("Helvetica-Bold", 9); c.drawString(48, 88, "Leitura automatica")
    msg = "QMASTER canonico reconciliado." if qm.get("status") == "PASS" else "QMASTER canonico ainda nao localizado; manter AMBER."
    wrap(c, msg + " D50 permanece research-only e N pequeno nao autoriza conclusao.", 48, 73, 720, 8.5, 11)
    c.save()


def write_discovery(s: dict) -> None:
    data = {
        "roots": [str(x) for x in ROOTS],
        "d50_candidates": [str(x) for x in candidates("GATE_BTC_D50_DAILY_LATEST*.txt")[:20]],
        "readiness_candidates": [str(x) for x in candidates("GATE_BTC_DATA_READINESS_REPORT_*.txt")[:20]],
        "coordinator_candidates": [str(x) for x in candidates("GATE_BTC_COLLECTION_COORDINATOR_LATEST*.txt")[:20]],
        "qmaster_candidates": [str(x) for x in candidates("GATE_BTC_QMASTER_LATEST.txt")[:20]],
        "qmaster_sync_status": s.get("qmaster_sync_status"),
    }
    DISCOVERY.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    s = load_state()
    render(s)
    STATE.write_text(json.dumps(s, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    write_discovery(s)
    print(f"STATUS={s['input_status']}")
    print(f"PDF={OUT}")
    print(f"STATE={STATE}")
    print(f"DISCOVERY={DISCOVERY}")
    print(f"QMASTER_SYNC={s['qmaster_sync_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
