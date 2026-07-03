from pathlib import Path

from crypto_decision_lab.reports.canonical_data_collection_dry_run import build_canonical_data_collection_dry_run


def test_canonical_data_collection_dry_run_builds_artifacts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    fixture = root / "crypto_decision_lab" / "data" / "fixtures" / "research" / "btc_usdt_1h_sample.json"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    fixture.write_text('{"symbol":"BTC-USDT","candles":[{"t":1},{"t":2}]}', encoding="utf-8")

    result = build_canonical_data_collection_dry_run(
        output_dir=tmp_path / "out",
        repo_root=root,
        symbols="BTC-USDT,ETH-USDT",
        target_rows_per_symbol=10,
    )
    payload = result["payload"]

    assert payload["policy_lock"] == "ACTIVE"
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["collection_mode"] == "DRY_RUN_ONLY"
    assert payload["jobs_created"] == 2
    assert payload["total_gap_rows"] > 0
    assert Path(result["html_path"]).exists()
    assert Path(result["markdown_path"]).exists()


def test_canonical_data_collection_dry_run_has_no_operational_flags(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    result = build_canonical_data_collection_dry_run(output_dir=tmp_path / "out", repo_root=root)
    payload = result["payload"]

    for key in [
        "api_key_present",
        "authenticated_connection_used",
        "orders_generated",
        "real_orders_generated",
        "real_capital_used",
        "trading_signal_generated",
        "executable_signal_generated",
        "recommendation_generated",
        "allocation_generated",
        "portfolio_decision_generated",
        "operational_decision_allowed",
    ]:
        assert payload[key] is False
