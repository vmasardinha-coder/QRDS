from pathlib import Path

from crypto_decision_lab.reports.dataset_evidence_scanner import build_dataset_evidence_scan, discover_dataset_files


def test_dataset_evidence_scanner_profiles_csv(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    csv_path = data_dir / "BTC-USDT_fixture.csv"
    csv_path.write_text("timestamp,open,close\n2026-01-01T00:00:00Z,1,2\n2026-01-01T00:01:00Z,2,3\n", encoding="utf-8")

    result = build_dataset_evidence_scan(
        tmp_path / "out",
        "BTC-USDT,ETH-USDT",
        scan_roots=[data_dir],
        min_rows_per_symbol=2,
    )
    payload = result["payload"]
    assert payload["dataset_file_count"] == 1
    assert payload["symbols_with_files"] == 1
    btc = [p for p in payload["symbol_profiles"] if p["symbol"] == "BTC-USDT"][0]
    assert btc["row_count"] == 2
    assert btc["time_column_present"] is True
    assert result["html_path"].endswith("index.html")


def test_dataset_evidence_scanner_without_files_blocks(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    result = build_dataset_evidence_scan(tmp_path / "out", "BTC-USDT", scan_roots=[root])
    assert result["gate_answer"] == "NO_LOCAL_DATASET_EVIDENCE_FOUND_RESEARCH_ONLY"
    assert result["payload"]["orders_generated"] is False
    assert result["payload"]["recommendation_generated"] is False


def test_discover_dataset_files_matches_symbol(tmp_path: Path) -> None:
    root = tmp_path / "fixtures"
    root.mkdir()
    (root / "eth_usdt_sample.jsonl").write_text('{"timestamp":"2026-01-01T00:00:00Z","x":1}\n', encoding="utf-8")
    found = discover_dataset_files(["ETH-USDT"], [root])
    assert len(found["ETH-USDT"]) == 1
