from pathlib import Path

from tools.gate_btc_factory import grammar_007_physical_source_capture as p


def test_source_contract_is_exact_and_official_only():
    assert p.BCB_ANNUAL.startswith("https://olinda.bcb.gov.br/")
    assert p.CVM_INF_SAMPLE.startswith("https://dados.cvm.gov.br/")
    assert p.CVM_DELIVERY_SAMPLE.startswith("https://dados.cvm.gov.br/")
    assert p.CVM_CLASS_REGISTRY.startswith("https://dados.cvm.gov.br/")
    assert all(url.startswith("https://bvmf.bmfbovespa.com.br/") for url in p.B3_COTAHIST_CANDIDATES)


def test_b3_target_is_never_parsed_in_capture_stage():
    text = Path(p.__file__).read_text(encoding="utf-8")
    assert '"target_bytes_parsed": False' in text
    assert '"target_outcomes_read": False' in text
    assert '"outcomes_read": False' in text
    assert '"economics_read": False' in text
    assert '"features_materialized": False' in text
    assert '"candidate_ranked": False' in text


def test_pit_is_fail_closed_until_semantics_are_materialized():
    text = Path(p.__file__).read_text(encoding="utf-8")
    assert '"exact_historical_intraday_publication_timestamp_proven": False' in text
    assert '"availability_mapping_requires_delivery_join": True' in text
    assert text.count('"pit_admission_pass": False') >= 3


def test_scientific_credit_stays_zero():
    assert p.SAFETY["RESEARCH_ONLY"] is True
    assert p.SAFETY["SHADOW_ONLY"] is True
    assert p.SAFETY["NOT_APPROVED"] is True
    assert p.SAFETY["ENGINE_FEED"] is False
    assert p.SAFETY["ORDERS"] == 0
    assert p.SAFETY["REAL_CAPITAL"] == 0
    assert p.SAFETY["NO_BACKFILL"] is True
    assert p.SAFETY["NO_RETUNE"] is True
    assert p.SAFETY["FAIL_CLOSED"] is True


def test_feature_source_fields_match_frozen_materializer_contract():
    text = Path(p.__file__).read_text(encoding="utf-8")
    for field in ("DT_COMPTC", "CAPTC_DIA", "RESG_DIA", "VL_PATRIM_LIQ"):
        assert field in text
    for field in ("Indicador", "Data", "DataReferencia", "Mediana", "baseCalculo"):
        assert field in text
