from pathlib import Path


FROZEN = {
    "UPSTREAM_ENGINE_SHA256": "1e313614e4f8dd318488e3abdde1d56848c076f9e57bb47a4fd5ce4f9c06410c",
    "FULL_FROZEN_SCHEDULE_SHA256": "5fd7314f55fb1c6394628d94227fdc0ed375016a57453a07f05828ffd5a9282f",
    "H1_PREFIX_SHA256": "c9ff28b4d1b6c8e2aceb3281da51bc41858780493c99a0eeac148f2bdd0bc4f6",
    "BLIND_LOCK_SHA256": "ceb5ed9b48f2c4f616eee82a78942f39deceb41272369be02ad207b49425cbf1",
}


def test_late_publication_windows_only_retry_prior_session():
    workflow = Path(".github/workflows/gate-btc-b3-h1-daily.yml").read_text(encoding="utf-8")
    assert '- cron: "30 0,1,2 * * 2-6"' in workflow
    assert '- cron: "30 9,12 * * 2-6"' in workflow
    assert "TARGET_DATE=$(date -u -d 'yesterday' +%F)" in workflow
    assert 'SOURCE="SCHEDULE_PRIOR_UTC_DATE"' in workflow
    assert "backfill older dates" in workflow


def test_recovery_does_not_change_frozen_h1_contract():
    collector = Path("tools/gate_btc_b3_h1_daily.py").read_text(encoding="utf-8")
    for name, digest in FROZEN.items():
        assert f'{name} = "{digest}"' in collector
    assert "2026-08-25,WINV26,WDOV26,FROZEN_BEFORE_H1" in collector
    assert "EXPECTED_M5 = 102" in collector
    assert 'TICK = {"WIN": 5.0, "WDO": 0.5}' in collector
    assert '"economics_locked": True' in collector
    assert '"economic_functions_called": False' in collector
