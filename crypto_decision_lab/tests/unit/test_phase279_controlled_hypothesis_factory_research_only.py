from crypto_decision_lab.scripts.phase276_285_strategy_search_common import p276,p279
def test_phase279_factory():
 p=p279(p276());assert p["passed"] and p["hypothesis_count"]==108 and len({x["hypothesis_id"] for x in p["hypotheses"]})==108
