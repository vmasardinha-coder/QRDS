#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -d "$ROOT/crypto_decision_lab" ] && [ -d "/workspaces/QRDS/crypto_decision_lab" ]; then
  ROOT="/workspaces/QRDS"
fi

PROJECT="$ROOT/crypto_decision_lab"
SRC="$PROJECT/src"
OUT="$PROJECT/artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack"

export PYTHONPATH="$SRC:${PYTHONPATH:-}"

echo "[QRDS 30F HOTFIX] Patching 30E regression to wait for HTTP readiness..."

cat > "$PROJECT/tests/regression/test_portal_serve_plan_30e_hotfix.py" <<'PY'
import json
from pathlib import Path
import socket
import subprocess
import time
import urllib.request


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def test_portal_serve_writes_dashboard_serve_plan_json(tmp_path: Path) -> None:
    project = Path(__file__).resolve().parents[2]
    port = _free_port()
    out = tmp_path / "portal"
    proc = subprocess.Popen(
        ["bash", "qrds_portal_serve.sh", "--output-dir", str(out), "--port", str(port), "--host", "127.0.0.1", "--no-build"],
        cwd=project,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.time() + 10
        plan_path = out / "dashboard_serve_plan.json"
        plan = None

        while time.time() < deadline:
            if proc.poll() is not None:
                stdout, stderr = proc.communicate(timeout=1)
                raise AssertionError(f"server exited early rc={proc.returncode}\nstdout={stdout}\nstderr={stderr}")
            if plan_path.exists() and (out / "index.html").exists():
                try:
                    plan = json.loads(plan_path.read_text(encoding="utf-8"))
                    break
                except Exception:
                    pass
            time.sleep(0.2)

        assert proc.poll() is None
        assert (out / "index.html").exists()
        assert plan_path.exists()
        assert plan is not None
        assert plan["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
        assert plan["policy_lock"] == "ACTIVE"
        assert plan["port"] == port
        assert plan["safe_apply_allowed"] is False
        assert plan["promotion_allowed"] is False
        assert plan["canonical_data_writes"] == 0

        # Wait separately for the HTTP server socket. The plan JSON is written
        # before `python -m http.server` has necessarily completed binding.
        served = None
        deadline = time.time() + 10
        while time.time() < deadline:
            if proc.poll() is not None:
                stdout, stderr = proc.communicate(timeout=1)
                raise AssertionError(f"server exited before serving plan rc={proc.returncode}\nstdout={stdout}\nstderr={stderr}")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/dashboard_serve_plan.json", timeout=1) as resp:
                    served = json.loads(resp.read().decode("utf-8"))
                    break
            except Exception:
                time.sleep(0.2)

        assert served is not None
        assert served["port"] == port
        assert served["research_only"] is True
        assert served["operational_decision_allowed"] is False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
PY

echo "[QRDS 30F HOTFIX] Running portal serve targeted tests..."
cd "$PROJECT"
pytest -q \
  tests/integration/test_dashboard_portal_serve_cli.py::test_qrds_portal_serve_wrapper_starts_server \
  tests/regression/test_portal_serve_wrapper_30c_hotfix.py \
  tests/regression/test_portal_serve_wrapper_30d_dual_location.py \
  tests/regression/test_portal_serve_plan_30e_hotfix.py

echo "[QRDS 30F HOTFIX] Running Phase 30 targeted tests..."
pytest -q \
  tests/unit/test_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.py \
  tests/integration/test_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_cli.py \
  tests/regression/test_phase30_missing_inputs_needs_review.py \
  tests/regression/test_phase30_readiness_alias_override_hotfix.py

echo "[QRDS 30F HOTFIX] Running full test suite..."
pytest -q tests/safety tests/unit tests/integration tests/regression tests/docs

echo "[QRDS 30F HOTFIX] Regenerating Phase 30 report..."
cd "$ROOT"
bash "$ROOT/qrds_phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack.sh" "$OUT"

python - <<'PY'
import json
from pathlib import Path

p = Path("crypto_decision_lab/artifacts/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack/phase30_no_edge_checkpoint_risk_regime_dashboard_readiness_pack_index.json")
d = json.loads(p.read_text(encoding="utf-8"))

for k in [
    "gate_answer",
    "station",
    "no_edge_checkpoint_ready",
    "phase29_retest_ready",
    "data_nature",
    "stable_compressed_candidate_count",
    "edge_validated",
    "edge_operationally_validated",
    "risk_regime_dashboard_research_ready",
    "shadow_decision_allowed",
    "decision_layer_allowed",
    "next_research_path",
    "operational_status",
    "modeling_status",
    "safe_apply_allowed",
    "promotion_allowed",
    "canonical_data_writes",
    "git_status_line_count",
    "criteria_ready_count",
    "criteria_total_count",
    "mean_checkpoint_score",
    "policy_lock",
    "app_mode",
]:
    print(f"{k}: {d.get(k)}")

print("[QRDS 30F HOTFIX] Component readiness:")
for r in d.get("payload", {}).get("component_readiness", []):
    print(f"{r['component_id']}: present={r['index_present']} ready={r['ready']} ready_key={r['ready_key']} gate={r['gate_answer']}")
PY

echo "[QRDS 30F HOTFIX] Committing changes..."
git add -A
git commit -m "Hotfix portal serve plan readiness wait and regenerate Phase 30" || true
git push || true

echo "[QRDS 30F HOTFIX] Final status:"
git status --short
