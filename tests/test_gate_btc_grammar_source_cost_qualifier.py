import json
from tools.gate_btc_factory.grammar_source_cost_qualifier import qualify

def protocol():
 return {"frozen_before_outcomes":True,"schema":"qrds.factory.grammar_source_cost_qualification_protocol.v1","safety":{"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"FAIL_CLOSED":True,"H1_H31_UNTOUCHED":True}}

def intake():
 return {"families":[{"family_id":"X","grammar_signature":"s","official_free_source_candidates":["B3"],"economics_read":False,"historical_testing_started":False}]}

def test_waits_without_evidence(tmp_path):
 o=qualify(intake(),protocol(),tmp_path); assert o["waiting_count"]==1 and o["qualified_count"]==0

def test_qualifies_only_complete_preregistered_evidence(tmp_path):
 e={"family_id":"X","grammar_signature":"s","qualified_sources":["B3"],"outcomes_read":False,"economics_read":False,"source_checks":{"official_public_free":True,"required_data_covered":True,"pit_timestamps":True,"granularity_sufficient":True,"calendar_causal":True,"reproducible_auditable":True},"cost_checks":{"data_acquisition_zero":True,"frozen_execution_cost_contract_preserved":True,"no_new_economic_assumption":True}}
 (tmp_path/"X.json").write_text(json.dumps(e))
 o=qualify(intake(),protocol(),tmp_path); assert o["qualified_count"]==1 and o["families"][0]["next_stage"]=="EXISTING_FACTORY_INTAKE"

def test_rejects_non_preregistered_source(tmp_path):
 e={"family_id":"X","grammar_signature":"s","qualified_sources":["OTHER"],"outcomes_read":False,"economics_read":False}
 (tmp_path/"X.json").write_text(json.dumps(e))
 try: qualify(intake(),protocol(),tmp_path)
 except ValueError as x: assert "non-preregistered" in str(x); return
 raise AssertionError("expected fail closed")
