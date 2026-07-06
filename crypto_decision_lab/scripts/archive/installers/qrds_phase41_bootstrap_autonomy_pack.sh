#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
SRC_DIR="$PROJECT_DIR/src/crypto_decision_lab"
SCRIPTS_PKG="$SRC_DIR/scripts"
TEST_DIR="$PROJECT_DIR/tests/unit"
REPORT="$PROJECT_DIR/docs/reports/PROJECT_STATUS_QRDS_GATE_BTC.md"
ARCHIVE_DIR="$PROJECT_DIR/scripts/archive/installers"

GATE="PHASE41_GUIDED_RESEARCH_PORTAL_HELP_SYSTEM_READY_RESEARCH_ONLY"
PHASE="phase41_guided_research_portal_help_system"
OPERATIONAL_STATUS="BLOCKED_RESEARCH_ONLY"

cd "$ROOT_DIR"

if [[ ! -d "$PROJECT_DIR" ]]; then
  echo "[QRDS][Phase41][ERROR] Missing crypto_decision_lab at $PROJECT_DIR"
  exit 2
fi

mkdir -p "$SCRIPTS_PKG" "$TEST_DIR" "$ARCHIVE_DIR" "$(dirname "$REPORT")"

touch "$SCRIPTS_PKG/__init__.py"

cat > "$SCRIPTS_PKG/phase41_guided_research_portal_help_system.py" <<'PY'
from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE41_GUIDED_RESEARCH_PORTAL_HELP_SYSTEM_READY_RESEARCH_ONLY"
PHASE = "phase41_guided_research_portal_help_system"

RESEARCH_LOCK = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

PAGES = [
    ("index.html", "Help system overview", "Entrada principal do sistema de ajuda research-only."),
    ("start_here.html", "Start here", "Comece por aqui: estado atual, limites e como ler o portal."),
    ("how_to_read.html", "How to read", "Como interpretar painéis sem transformar diagnóstico em decisão."),
    ("metric_dictionary.html", "Metric dictionary", "Dicionário visual de métricas e significado de pesquisa."),
    ("reading_paths.html", "Reading paths", "Trilhas de leitura por objetivo: auditoria, regime, risco e evidência."),
    ("candidate_status.html", "Candidate status", "Histórico dos candidatos: Phase 26 teve 4; Phases 27–29 deixaram 0 estáveis."),
    ("what_not_to_infer.html", "What not to infer", "O que não concluir: sem compra, venda, alocação, sinal ou decisão."),
    ("audit_checklist.html", "Audit checklist", "Checklist humano para revisar dados, evidência, limites e segurança."),
    ("help_center.html", "Help center", "Central de ajuda do portal QRDS Gate BTC."),
    ("safety_lock.html", "Safety lock", "Travas permanentes research-only e bloqueios operacionais."),
]

CSS = """
:root{--bg:#07111f;--panel:#0f1d31;--panel2:#13243c;--text:#e7edf8;--muted:#a7b4c8;--line:#28415f;--ok:#75e0a7;--warn:#f4c971;--bad:#ff8a8a}
*{box-sizing:border-box}body{margin:0;font-family:Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial;background:radial-gradient(circle at top left,#163153,#07111f 40%,#050912);color:var(--text)}
.layout{display:grid;grid-template-columns:280px 1fr;min-height:100vh}.side{padding:24px;border-right:1px solid var(--line);background:rgba(8,18,33,.88);position:sticky;top:0;height:100vh;overflow:auto}.brand{font-weight:800;font-size:20px;margin-bottom:6px}.sub{color:var(--muted);font-size:13px;line-height:1.4}.nav{margin-top:22px;display:grid;gap:8px}.nav a{color:var(--text);text-decoration:none;padding:10px 12px;border:1px solid var(--line);border-radius:12px;background:rgba(255,255,255,.03)}.nav a:hover{background:rgba(255,255,255,.08)}
.main{padding:34px;max-width:1180px}.hero{padding:26px;border:1px solid var(--line);border-radius:22px;background:linear-gradient(135deg,rgba(24,52,88,.9),rgba(10,21,38,.9));box-shadow:0 20px 60px rgba(0,0,0,.25)}h1{margin:0 0 10px;font-size:34px}h2{margin-top:28px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-top:18px}.card{border:1px solid var(--line);border-radius:18px;background:rgba(15,29,49,.9);padding:18px}.badge{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:6px 10px;font-size:12px;margin:4px 6px 4px 0}.ok{color:var(--ok)}.warn{color:var(--warn)}.bad{color:var(--bad)}code{background:#091326;border:1px solid var(--line);border-radius:8px;padding:2px 6px}.footer{color:var(--muted);margin-top:28px;font-size:13px}
@media(max-width:800px){.layout{grid-template-columns:1fr}.side{position:relative;height:auto}.main{padding:20px}h1{font-size:27px}}
"""

@dataclass(frozen=True)
class BuildResult:
    gate: str
    ready: bool
    output_dir: str
    page_count: int
    focused_gate: str
    operational_status: str
    edge_validated: bool
    canonical_data_writes: int

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()

def _nav(active: str) -> str:
    links = "\n".join(f'<a href="{file}">{title}</a>' for file, title, _ in PAGES)
    return f"""
    <aside class="side">
      <div class="brand">QRDS Gate BTC</div>
      <div class="sub">Guided Research Portal Help System<br>research-only • no signal • no recommendation</div>
      <div class="nav">{links}</div>
    </aside>
    """

def _page_html(file: str, title: str, desc: str) -> str:
    cards = [
        ("Research-only", "Esta página explica o portal sem criar decisão operacional.", "ok"),
        ("Edge", "edge_validated: False; operational edge: False.", "warn"),
        ("Operational", "operational_status: BLOCKED_RESEARCH_ONLY.", "bad"),
        ("Canonical writes", "canonical_data_writes: 0.", "ok"),
    ]
    if file == "candidate_status.html":
        extra = """
        <h2>Candidate lifecycle</h2>
        <div class="card">
          <p><b>Phase 26:</b> 4 candidatos de pesquisa apareceram.</p>
          <p><b>Phases 27–29:</b> 0 candidatos estáveis após anti-overfit/retest.</p>
          <p><b>Estado oficial:</b> pool operacional = 0 / indefinido.</p>
        </div>
        """
    elif file == "what_not_to_infer.html":
        extra = """
        <h2>Forbidden inference</h2>
        <div class="card">
          <p>Não inferir compra, venda, alocação, sinal, recomendação, safe-apply, promoção canônica ou decisão operacional.</p>
        </div>
        """
    else:
        extra = """
        <h2>Reading rule</h2>
        <div class="card">
          <p>Use esta tela para entender o significado de pesquisa dos painéis. A decisão humana, se existir fora do QRDS, permanece responsabilidade do usuário.</p>
        </div>
        """
    card_html = "\n".join(f'<div class="card"><span class="badge {cls}">{name}</span><p>{body}</p></div>' for name, body, cls in cards)
    return f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} • QRDS Gate BTC</title><link rel="stylesheet" href="assets/phase41.css"></head>
<body><div class="layout">{_nav(file)}
<main class="main"><section class="hero"><h1>{title}</h1><p>{desc}</p>
<span class="badge ok">{READY_GATE}</span><span class="badge bad">BLOCKED_RESEARCH_ONLY</span><span class="badge warn">edge_validated: False</span></section>
<div class="grid">{card_html}</div>{extra}
<div class="footer">QRDS Gate BTC • Phase 41 • research-only • generated {datetime.now(timezone.utc).isoformat()}</div>
</main></div></body></html>"""

def build_phase41(output_dir: str | Path | None = None) -> dict:
    project = Path.cwd()
    if project.name != "crypto_decision_lab" and (project / "crypto_decision_lab").is_dir():
        project = project / "crypto_decision_lab"
    out = Path(output_dir) if output_dir else project / "artifacts" / PHASE
    out.mkdir(parents=True, exist_ok=True)
    (out / "assets").mkdir(exist_ok=True)
    (out / "assets" / "phase41.css").write_text(CSS, encoding="utf-8")

    manifest_rows = []
    for file, title, desc in PAGES:
        path = out / file
        path.write_text(_page_html(file, title, desc), encoding="utf-8")
        manifest_rows.append({"file": file, "title": title, "description": desc, "research_only": "true"})

    safety = {
        "gate": READY_GATE,
        "ready": True,
        "page_count": len(PAGES),
        "required_pages_present": len([p for p, _, _ in PAGES if (out / p).exists()]),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **RESEARCH_LOCK,
    }
    (out / "phase41_safety_status.json").write_text(json.dumps(safety, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase41_navigation.json").write_text(json.dumps([{"file": r["file"], "title": r["title"]} for r in manifest_rows], indent=2), encoding="utf-8")

    with (out / "phase41_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["file", "title", "description", "research_only"])
        w.writeheader()
        w.writerows(manifest_rows)

    checksums = {}
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "phase41_checksums.json":
            checksums[str(path.relative_to(out))] = _sha256(path)
    (out / "phase41_checksums.json").write_text(json.dumps(checksums, indent=2, sort_keys=True), encoding="utf-8")

    zip_path = out / "QRDS_PHASE41_GUIDED_RESEARCH_PORTAL_HELP_SYSTEM_RESEARCH_ONLY.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(out.rglob("*")):
            if path.is_file() and path != zip_path:
                z.write(path, path.relative_to(out))

    result = BuildResult(
        gate=READY_GATE,
        ready=True,
        output_dir=str(out),
        page_count=len(PAGES),
        focused_gate=READY_GATE,
        operational_status="BLOCKED_RESEARCH_ONLY",
        edge_validated=False,
        canonical_data_writes=0,
    )
    (out / "phase41_build_result.json").write_text(json.dumps(result.__dict__, indent=2, sort_keys=True), encoding="utf-8")
    return result.__dict__

def main(argv: list[str] | None = None) -> int:
    result = build_phase41()
    print("QRDS Phase 41 • Guided Research Portal Help System")
    print(result["gate"])
    print(f'Pages: {result["page_count"]}')
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
PY

cat > "$TEST_DIR/test_phase41_guided_research_portal_help_system.py" <<'PY'
from pathlib import Path

from crypto_decision_lab.scripts.phase41_guided_research_portal_help_system import READY_GATE, build_phase41

def test_phase41_builds_guided_help_system(tmp_path):
    result = build_phase41(tmp_path / "phase41")
    out = Path(result["output_dir"])
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["page_count"] == 10
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0
    for name in [
        "index.html",
        "start_here.html",
        "how_to_read.html",
        "metric_dictionary.html",
        "reading_paths.html",
        "candidate_status.html",
        "what_not_to_infer.html",
        "audit_checklist.html",
        "help_center.html",
        "safety_lock.html",
        "phase41_manifest.csv",
        "phase41_safety_status.json",
        "phase41_checksums.json",
    ]:
        assert (out / name).exists(), name
PY

cat > qrds_phase41_verify.sh <<'VERIFY'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
echo "[QRDS][Phase41] Running focused tests..."
python -m pytest tests/unit/test_phase41_guided_research_portal_help_system.py -q
echo "[QRDS][Phase41] Running full suite..."
python -m pytest -q
echo "PHASE41_GUIDED_RESEARCH_PORTAL_HELP_SYSTEM_READY_RESEARCH_ONLY"
echo "Operational: BLOCKED_RESEARCH_ONLY"
echo "Edge: False"
echo "canonical_data_writes: 0"
echo "Focused tests: PASS"
echo "Full suite: PASS"
VERIFY
chmod +x qrds_phase41_verify.sh
cp -f qrds_phase41_verify.sh "$PROJECT_DIR/qrds_phase41_verify.sh"
chmod +x "$PROJECT_DIR/qrds_phase41_verify.sh"

cat > qrds_phase41_portal_serve.sh <<'SERVE'
#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="${QRDS_ROOT:-/workspaces/QRDS}"
PROJECT_DIR="$ROOT_DIR/crypto_decision_lab"
PORT="${PORT:-0}"
BIND="${BIND:-0.0.0.0}"
cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"
python -m crypto_decision_lab.scripts.phase41_guided_research_portal_help_system
OUT_DIR="$PROJECT_DIR/artifacts/phase41_guided_research_portal_help_system"
python - <<'PY'
import json, socket
from pathlib import Path
out = Path("artifacts/phase41_guided_research_portal_help_system")
s = socket.socket()
s.bind(("", 0))
port = s.getsockname()[1]
s.close()
plan = {"host": "0.0.0.0", "port": port, "output_dir": str(out), "index": "index.html"}
(out / "dashboard_serve_plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
print(port)
PY
PORT="$(python - <<'PY'
import json
from pathlib import Path
print(json.loads((Path("artifacts/phase41_guided_research_portal_help_system")/"dashboard_serve_plan.json").read_text())["port"])
PY
)"
echo "[QRDS][Phase41] Open Codespaces Ports tab and make port ${PORT} public/visible if needed."
echo "[QRDS][Phase41] Serving: $OUT_DIR"
cd "$OUT_DIR"
python -m http.server "$PORT" --bind "$BIND"
SERVE
chmod +x qrds_phase41_portal_serve.sh
cp -f qrds_phase41_portal_serve.sh "$PROJECT_DIR/qrds_phase41_portal_serve.sh"
chmod +x "$PROJECT_DIR/qrds_phase41_portal_serve.sh"

cp -f "$0" "$ARCHIVE_DIR/qrds_phase41_bootstrap_autonomy_pack.sh" 2>/dev/null || true

cat >> "$REPORT" <<MD

## Phase 41 — Guided Research Portal Help System

Gate: \`$GATE\`  
Operational: \`$OPERATIONAL_STATUS\`  
Edge validated: \`False\`  
canonical_data_writes: \`0\`  

Scope: guided help system for reading the QRDS Gate BTC research portal. This phase adds a help center, metric dictionary, reading paths, candidate status explanation, forbidden inference page, audit checklist and safety lock. It does not create trading signals, recommendations, allocations, shadow decisions, safe-apply, promotions, canonical writes, or operational decisions.
MD

git add \
  "$SCRIPTS_PKG/__init__.py" \
  "$SCRIPTS_PKG/phase41_guided_research_portal_help_system.py" \
  "$TEST_DIR/test_phase41_guided_research_portal_help_system.py" \
  qrds_phase41_verify.sh \
  qrds_phase41_portal_serve.sh \
  crypto_decision_lab/qrds_phase41_verify.sh \
  crypto_decision_lab/qrds_phase41_portal_serve.sh \
  "$REPORT"

if [[ -f "$ARCHIVE_DIR/qrds_phase41_bootstrap_autonomy_pack.sh" ]]; then
  git add "$ARCHIVE_DIR/qrds_phase41_bootstrap_autonomy_pack.sh" || true
fi

cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR/src:${PYTHONPATH:-}"

python -m crypto_decision_lab.scripts.phase41_guided_research_portal_help_system

echo "[QRDS][Phase41] Running focused tests..."
python -m pytest tests/unit/test_phase41_guided_research_portal_help_system.py -q

echo "[QRDS][Phase41] Running full suite..."
python -m pytest -q

cd "$ROOT_DIR"

if ! git diff --cached --quiet; then
  git commit -m "Phase 41: guided research portal help system"
  git push
else
  echo "[QRDS][Phase41] No staged changes to commit."
fi

echo
echo "QRDS Phase 41 • Guided Research Portal Help System"
echo "$GATE"
echo "Operational: $OPERATIONAL_STATUS"
echo "Edge: False"
echo "canonical_data_writes: 0"
echo "Focused tests: PASS"
echo "Full suite: PASS"
