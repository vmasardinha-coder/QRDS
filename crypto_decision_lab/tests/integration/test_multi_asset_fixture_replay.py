from crypto_decision_lab.cli.full_research import run_full_research_chain
from crypto_decision_lab.contracts.research import build_integration_health_report, validate_integration_health_report
from crypto_decision_lab.fixtures.okx_public_catalog import (
    build_okx_public_fixture_catalog,
    validate_okx_public_fixture_catalog,
)


def test_multi_asset_fixture_replay_eth_sol(tmp_path):
    catalog = build_okx_public_fixture_catalog(symbols=("ETH-USDT", "SOL-USDT"))

    assert validate_okx_public_fixture_catalog(catalog) == []

    summaries = []
    for entry in catalog["entries"]:
        symbol_id = entry["instId"].lower().replace("-", "_")
        summaries.append(
            run_full_research_chain(
                fixture_path=entry["path"],
                output_dir=tmp_path / symbol_id,
                run_id=f"multi-asset-{symbol_id}",
                report_id=f"edge-{symbol_id}",
                horizons=(1, 3),
                train_size=4,
                test_size=2,
                step_size=1,
            )
        )

    health = build_integration_health_report(
        {
            f"summary_{i}_{summary['symbol']}": summary
            for i, summary in enumerate(summaries)
        },
        report_name="multi-asset-fixture-replay",
    )

    assert len(summaries) == 2
    assert {summary["symbol"] for summary in summaries} == {"ETH-USDT", "SOL-USDT"}
    assert all(summary["full_research_cli_passed"] is True for summary in summaries)
    assert health["integration_health_passed"] is True
    assert validate_integration_health_report(health) == []
