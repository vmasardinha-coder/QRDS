import json

import pytest

from crypto_decision_lab.validation.walk_forward import (
    WALK_FORWARD_REPORT_SCHEMA_VERSION,
    WALK_FORWARD_SPLIT_SCHEMA_VERSION,
    WalkForwardSplitError,
    build_walk_forward_report,
    build_walk_forward_splits,
    load_research_dataset_jsonl,
    materialize_walk_forward_split,
    validate_walk_forward_splits,
)


def _rows(n=10):
    return [
        {
            "ts": 1_700_000_000_000 + i * 3_600_000,
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "candle_close": 100 + i,
            "future_return_h1": 0.01,
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        }
        for i in range(n)
    ]


def test_build_walk_forward_splits():
    splits = build_walk_forward_splits(_rows(10), train_size=4, test_size=2, step_size=2, gap_size=1)

    assert len(splits) == 2
    assert splits[0]["schema"] == WALK_FORWARD_SPLIT_SCHEMA_VERSION
    assert splits[0]["train_row_count"] == 4
    assert splits[0]["gap_row_count"] == 1
    assert splits[0]["test_row_count"] == 2
    assert splits[0]["operational_decision_allowed"] is False


def test_build_walk_forward_splits_blocks_too_few_rows():
    with pytest.raises(WalkForwardSplitError):
        build_walk_forward_splits(_rows(4), train_size=4, test_size=2, step_size=1)


def test_build_walk_forward_splits_blocks_operational_row():
    rows = _rows(10)
    rows[0]["operational_decision_allowed"] = True

    with pytest.raises(WalkForwardSplitError):
        build_walk_forward_splits(rows, train_size=4, test_size=2, step_size=1)


def test_materialize_walk_forward_split():
    rows = _rows(10)
    splits = build_walk_forward_splits(rows, train_size=4, test_size=2, step_size=1)
    materialized = materialize_walk_forward_split(rows, splits[0])

    assert len(materialized["train"]) == 4
    assert len(materialized["test"]) == 2


def test_validate_walk_forward_splits_flags_bad_bounds():
    splits = build_walk_forward_splits(_rows(10), train_size=4, test_size=2, step_size=1)
    splits[0]["test_end_index_exclusive"] = 999
    issues = validate_walk_forward_splits(splits, dataset_row_count=10)

    assert any(issue["code"] == "INVALID_WALK_FORWARD_BOUNDS" for issue in issues)


def test_build_walk_forward_report():
    rows = _rows(10)
    splits = build_walk_forward_splits(rows, train_size=4, test_size=2, step_size=1)
    report = build_walk_forward_report(rows, splits, split_name="unit")

    assert report["schema"] == WALK_FORWARD_REPORT_SCHEMA_VERSION
    assert report["walk_forward_quality_passed"] is True
    assert report["split_count"] == len(splits)
    assert report["operational_decision_allowed"] is False
    assert report["api_key_required"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False


def test_load_research_dataset_jsonl(tmp_path):
    path = tmp_path / "dataset.jsonl"
    with path.open("w", encoding="utf-8") as handle:
        for row in _rows(3):
            handle.write(json.dumps(row) + "\n")

    loaded = load_research_dataset_jsonl(path)

    assert len(loaded) == 3
