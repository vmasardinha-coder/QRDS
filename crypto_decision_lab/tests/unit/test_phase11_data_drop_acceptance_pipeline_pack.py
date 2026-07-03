import json
from pathlib import Path
from crypto_decision_lab.reports.phase11_data_drop_acceptance_pipeline_pack import build_phase11_data_drop_acceptance_pipeline_pack

def test_phase11_data_drop_acceptance_pipeline_pack_builds(tmp_path: Path):
    root=tmp_path/"repo"
    items=[
      ("phase11_offline_source_normalizer_pack","phase11_offline_source_normalizer_pack_index.json",{"rows_normalized":5,"ready_files":1,"files_normalized":1,"inbox_file_count":1,"fallback_samples_used":False}),
      ("phase10_offline_sample_intake_promotion_pack","phase10_offline_sample_intake_promotion_pack_index.json",{"valid_rows":5,"staging_rows":5}),
      ("phase10_sample_quality_promotion_gate_pack","phase10_sample_quality_promotion_gate_pack_index.json",{"sample_quality_ready":True,"full_depth_ready":False,"promotion_allowed":False,"canonical_data_writes":0}),
      ("phase10_depth_expansion_readiness_pack","phase10_depth_expansion_readiness_pack_index.json",{"total_gap_rows":4995,"promotion_allowed":False,"canonical_data_writes":0}),
      ("phase11_canonical_promotion_dry_run_lock_pack","phase11_canonical_promotion_dry_run_lock_pack_index.json",{"promotion_candidates_count":1,"safe_apply_allowed":False,"promotion_allowed":False,"canonical_data_writes":0}),
    ]
    for folder,file,payload in items:
        p=root/"crypto_decision_lab/artifacts"/folder/file; p.parent.mkdir(parents=True,exist_ok=True)
        payload.update({"gate_answer":"READY_RESEARCH_ONLY","policy_lock":"ACTIVE","app_mode":"INTERACTIVE_RESEARCH_ONLY"})
        p.write_text(json.dumps(payload),encoding="utf-8")
    r=build_phase11_data_drop_acceptance_pipeline_pack(tmp_path/"out",root); p=r["payload"]
    assert p["policy_lock"]=="ACTIVE"; assert p["app_mode"]=="INTERACTIVE_RESEARCH_ONLY"
    assert p["data_drop_mode"]=="INBOX_DATA"; assert p["packs_present"]==5
    assert p["promotion_allowed"] is False; assert p["canonical_data_writes"]==0
    assert Path(r["html_path"]).exists()

def test_phase11_data_drop_acceptance_pipeline_pack_has_no_operational_flags(tmp_path: Path):
    r=build_phase11_data_drop_acceptance_pipeline_pack(tmp_path/"out",tmp_path/"repo"); p=r["payload"]
    for key in ["api_key_present","authenticated_connection_used","orders_generated","real_orders_generated","real_capital_used","trading_signal_generated","executable_signal_generated","recommendation_generated","allocation_generated","portfolio_decision_generated","operational_decision_allowed"]:
        assert p[key] is False
