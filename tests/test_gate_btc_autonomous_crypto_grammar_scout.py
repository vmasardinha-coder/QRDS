import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/gate_btc_factory"))
from autonomous_crypto_grammar_scout import scout

def test_crypto_scout_is_ideation_only_and_isolated():
    def fake(q):
        return [{"openalex_id":"x:"+q,"doi":None,"title":"evidence "+q,"publication_year":2024,"source":"test"}]
    d=scout(fetcher=fake)
    assert d["mode"]=="IDEATION_ONLY_NO_ECONOMICS"
    assert d["history_used_for_selection"] is False
    assert len(d["proposals"]) >= 5
    for p in d["proposals"]:
        assert p["economics_read"] is False
        assert p["may_allocate_family_id"] is False
        assert p["may_modify_incumbent"] is False
        assert p["requires_separate_preregistration"] is True
