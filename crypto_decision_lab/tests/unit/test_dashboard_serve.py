import socket
from pathlib import Path

from crypto_decision_lab.cli.dashboard_serve import (
    DASHBOARD_SERVE_PLAN_SCHEMA_VERSION,
    build_dashboard_serve_plan,
    find_available_port,
    is_port_available,
    validate_dashboard_serve_plan,
    write_dashboard_serve_plan,
)


def test_is_port_available_with_bound_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.listen(1)
    try:
        assert is_port_available(port) is False
    finally:
        sock.close()


def test_find_available_port_skips_busy_port():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.listen(1)
    try:
        found = find_available_port(preferred_port=port, max_tries=5)
        assert found != port
        assert found > port
    finally:
        sock.close()


def test_build_dashboard_serve_plan(tmp_path):
    html_path = tmp_path / "index.html"
    html_path.write_text("<html></html>", encoding="utf-8")

    plan = build_dashboard_serve_plan(html_path=html_path, preferred_port=8020)

    assert plan["schema"] == DASHBOARD_SERVE_PLAN_SCHEMA_VERSION
    assert plan["html_path"] == str(html_path.resolve())
    assert plan["selected_port"] >= 8020
    assert "python -m http.server" in plan["serve_command"]
    assert plan["allocation_generated"] is False
    assert validate_dashboard_serve_plan(plan) == []


def test_write_dashboard_serve_plan(tmp_path):
    html_path = tmp_path / "index.html"
    html_path.write_text("<html></html>", encoding="utf-8")

    plan = write_dashboard_serve_plan(
        html_path=html_path,
        output_dir=tmp_path / "plan",
        preferred_port=8021,
    )

    assert Path(plan["serve_plan_path"]).exists()
    assert plan["selected_port"] >= 8021
