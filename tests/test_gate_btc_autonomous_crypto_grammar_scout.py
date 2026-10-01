import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/gate_btc_factory"))
from autonomous_crypto_grammar_scout import scout

NEW_CHANNELS={
    "CRYPTO_ONCHAIN_EXCHANGE_FLOW",
    "CRYPTO_STABLECOIN_LIQUIDITY_IMPULSE",
    "CRYPTO_MACRO_LIQUIDITY_RATES",
    "CRYPTO_MINER_HASHRATE_STRESS",
    "CRYPTO_SPOT_PARTICIPATION_FLOW",
}

def test_crypto_scout_is_ideation_only_and_isolated():
    def fake(q):
        return [{"openalex_id":"x:"+q,"doi":None,"title":"evidence "+q,"publication_year":2024,"source":"test"}]
    d=scout(fetcher=fake)
    assert d["mode"]=="IDEATION_ONLY_NO_ECONOMICS"
    assert d["history_used_for_selection"] is False
    assert len(d["proposals"]) >= 10
    ids={p["channel_id"] for p in d["proposals"]}
    assert NEW_CHANNELS <= ids
    for p in d["proposals"]:
        assert p["economics_read"] is False
        assert p["may_allocate_family_id"] is False
        assert p["may_modify_incumbent"] is False
        assert p["requires_separate_preregistration"] is True
        assert p["requires_forward_or_independent_unseen_data"] is True


def test_generation2_channels_do_not_define_economic_parameters():
    def fake(q):
        return [{"openalex_id":"x:"+q,"doi":None,"title":"evidence "+q,"publication_year":2024,"source":"test"}]
    d=scout(fetcher=fake)
    rows={p["channel_id"]:p for p in d["proposals"] if p["channel_id"] in NEW_CHANNELS}
    assert set(rows)==NEW_CHANNELS
    for row in rows.values():
        assert row["status"]=="SCOUTED_NOT_PREREGISTERED"
        assert "threshold" not in row
        assert "direction" not in row
        assert row["economics_read"] is False


def test_prior_scout_history_does_not_self_suppress(tmp_path):
    def fake(q):
        return [{"openalex_id":"x:"+q,"doi":None,"title":"evidence "+q,"publication_year":2024,"source":"test"}]
    prior={"proposals":[{"channel_id":"CRYPTO_MINER_HASHRATE_STRESS","status":"SCOUTED_NOT_PREREGISTERED"}]}
    (tmp_path/"prior.json").write_text(__import__("json").dumps(prior))
    d=scout(existing_dir=tmp_path,fetcher=fake)
    row=next(p for p in d["proposals"] if p["channel_id"]=="CRYPTO_MINER_HASHRATE_STRESS")
    assert row["status"]=="SCOUTED_NOT_PREREGISTERED"
    assert row["previously_scouted"] is True
    assert row["duplicate_authority"] is None
