import json

from tools.gate_btc_factory.autonomous_grammar_scout import scout


def _write_result(path):
    path.write_text(json.dumps({
        "status": "CLOSED_NO_SURVIVOR",
        "families": [
            {"contract": {"feature": "OPEN_RETURN", "direction": "CONTINUATION", "causal_standardization": "ROLLING_20_PRIOR_SESSIONS_MEDIAN_MAD"}},
            {"contract": {"feature": "GAP_FROM_PRIOR_CLOSE", "direction": "REVERSION", "causal_standardization": "ROLLING_120_PRIOR_SESSIONS_MEDIAN_MAD"}},
        ],
    }), encoding="utf-8")


def test_scout_is_ideation_only_and_includes_b3_adr(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    _write_result(results / "gate_btc_b3_h170_h179_result.json")

    def fake_fetcher(query):
        return [{
            "openalex_id": "https://openalex.org/W1",
            "doi": "https://doi.org/10.0000/example",
            "title": f"Evidence for {query}",
            "publication_year": 2024,
            "source": "Journal",
        }]

    out = scout(results, fetcher=fake_fetcher)
    assert out["mode"] == "IDEATION_ONLY_NO_ECONOMICS"
    assert out["history_used_for_selection"] is False
    assert out["b3_adr_scope_required"] is True
    assert out["evaluation_data_policy"].startswith("FORWARD_OR_INDEPENDENT_UNSEEN_ONLY")
    assert out["safety"]["no_backfill"] is True
    assert out["safety"]["h1_economics_read"] is False
    adr = next(x for x in out["proposals"] if x["channel_id"] == "B3_ADR_CROSS_LISTING_PRICE_DISCOVERY")
    assert adr["status"] == "SCOUTED_NOT_PREREGISTERED"
    assert adr["economics_read"] is False
    assert adr["may_allocate_family_id"] is False
    assert adr["may_test_threshold_grid"] is False
    assert "B3" in adr["official_free_source_candidates"]
    assert "SEC EDGAR" in adr["official_free_source_candidates"]


def test_existing_channel_is_suppressed(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    _write_result(results / "gate_btc_b3_h170_h179_result.json")
    existing = tmp_path / "existing"
    existing.mkdir()
    (existing / "old.json").write_text(json.dumps({
        "proposals": [{"channel_id": "B3_ADR_CROSS_LISTING_PRICE_DISCOVERY"}]
    }), encoding="utf-8")

    def fake_fetcher(query):
        return [{"openalex_id": "W1", "doi": None, "title": query, "publication_year": 2020, "source": None}]

    out = scout(results, existing, fake_fetcher)
    adr = next(x for x in out["proposals"] if x["channel_id"] == "B3_ADR_CROSS_LISTING_PRICE_DISCOVERY")
    assert adr["status"] == "DUPLICATE_CHANNEL_SUPPRESSED"
