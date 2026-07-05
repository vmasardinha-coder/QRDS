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
