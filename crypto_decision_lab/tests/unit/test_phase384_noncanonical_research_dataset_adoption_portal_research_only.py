from pathlib import Path
from crypto_decision_lab.scripts.phase384_noncanonical_research_dataset_adoption_portal_research_only import build
from tests.unit._phase376_385_fixtures import base, write_json

def items(tmp_path):
    values={376:base(376),377:base(377),378:base(378),379:base(379,candidate_dataset_adopted_noncanonical=True),380:base(380),381:base(381,integrity_pass=True,candidate_row_count=2),382:base(382,coexistence_pass=True),383:base(383,release_harness_pass=True)}; return {p:write_json(tmp_path/f"{p}.json",v) for p,v in values.items()}

def test_phase384_builds_required_portal(tmp_path:Path):
    r=build(items(tmp_path),tmp_path/"out",portal_registry_path=tmp_path/"catalog.md",root_start_path=tmp_path/"start.md"); text=(tmp_path/"out/index.html").read_text(encoding="utf-8"); assert r["capital_authorized_brl"]==0 and "VOCE ESTA AQUI" in text and "EXEMPLO COM R$10.000" in text

def test_phase384_updates_marked_blocks_idempotently(tmp_path:Path):
    paths=items(tmp_path); build(paths,tmp_path/"out",portal_registry_path=tmp_path/"catalog.md",root_start_path=tmp_path/"start.md"); build(paths,tmp_path/"out",portal_registry_path=tmp_path/"catalog.md",root_start_path=tmp_path/"start.md"); assert (tmp_path/"catalog.md").read_text(encoding="utf-8").count("BEGIN QRDS CURRENT PORTAL")==1
