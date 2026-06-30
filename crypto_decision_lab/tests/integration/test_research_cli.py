import json
from pathlib import Path

from crypto_decision_lab.cli.research import main


def _candles():
    closes = [100, 102, 105, 103, 108, 111, 115]
    rows = []
    for i, close in enumerate(closes):
        rows.append(
            {
                "ts": 1_700_000_000_000 + i * 3_600_000,
                "symbol": "BTC-USDT",
                "interval": "1h",
                "source": "cli_test",
                "open": close - 1,
                "high": close + 2,
                "low": close - 2,
                "close": close,
                "volume": 1000 + i,
            }
        )
    return rows


def test_research_cli_runs_pipeline(tmp_path, capsys):
    input_path = tmp_path / "candles.json"
    output_dir = tmp_path / "runs"

    input_path.write_text(
        json.dumps(
            {
                "symbol": "BTC-USDT",
                "interval": "1h",
                "source": "cli_test",
                "candles": _candles(),
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--input-candles",
            str(input_path),
            "--output-dir",
            str(output_dir),
            "--run-id",
            "cli-run",
            "--pipeline-commit",
            "cli-test",
            "--horizons",
            "1,3",
            "--tag",
            "cli",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["run_id"] == "cli-run"
    assert payload["dataset_row_count"] > 0
    assert payload["pipeline_quality_passed"] is True
    assert payload["operational_decision_allowed"] is False
    assert payload["api_key_required"] is False
    assert payload["orders_generated"] is False
    assert payload["real_capital_used"] is False

    assert Path(payload["paths"]["jsonl_path"]).exists()
    assert Path(payload["paths"]["csv_path"]).exists()
    assert Path(payload["paths"]["manifest_path"]).exists()
    assert Path(payload["paths"]["registry_path"]).exists()
    assert (output_dir / "cli-run" / "cli_summary.json").exists()
