from pathlib import Path
import importlib.util

MOD = Path(__file__).parents[1] / "tools/gate_btc_factory/h1_canonical_control.py"
spec = importlib.util.spec_from_file_location("h1_control", MOD)
h1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h1)


def write(p: Path, q: int, day: str, appended: bool = True):
    p.write_text(
        f"STATUS=H1_{q}_OF_20_CANONICAL\n"
        f"QUALIFIED={q}/20\n"
        f"REMAINING={20-q}\n"
        f"LAST_CANDIDATE_DATE={day}\n"
        "LAST_CANDIDATE_STATUS=STRUCTURAL_PASS\n"
        f"APPENDED_NOW={str(appended)}\n"
        "ECONOMICS_LOCKED=True\n",
        encoding="utf-8",
    )


def test_newer_canonical_8_beats_old_6(tmp_path):
    a = tmp_path / "GATE_BTC_B3_H1_STATUS_LATEST(20260827-230000).txt"
    b = tmp_path / "GATE_BTC_B3_H1_STATUS_LATEST(20260829-032536).txt"
    write(a, 6, "2026-08-26")
    write(b, 8, "2026-08-28")
    chosen, warnings = h1.choose_canonical(h1.discover(tmp_path))
    assert chosen.qualified == 8
    assert chosen.remaining == 12
    assert chosen.last_candidate_date == "2026-08-28"
    assert warnings == []


def test_later_bad_reporting_cannot_regress_counter(tmp_path):
    a = tmp_path / "GATE_BTC_B3_H1_STATUS_LATEST(20260829-032536).txt"
    b = tmp_path / "GATE_BTC_B3_H1_STATUS_LATEST(20260830-090000).txt"
    write(a, 8, "2026-08-28")
    write(b, 6, "2026-08-29")
    chosen, warnings = h1.choose_canonical(h1.discover(tmp_path))
    assert chosen.qualified == 8
    assert warnings and warnings[0].startswith("CANONICAL_COUNTER_REGRESSION_BLOCKED")


def test_reason_taxonomy():
    assert h1.normalize_reason("PENDING_SOURCE_NOT_PUBLISHED", False) == "SOURCE_NOT_PUBLISHED"
    assert h1.normalize_reason("SOURCE_RETRY_EXHAUSTED", False) == "SOURCE_FAILURE"
    assert h1.normalize_reason("STRUCTURAL_FAIL_CLOSED", False) == "STRUCTURAL_FAIL"
    assert h1.normalize_reason("STRUCTURAL_PASS", True) == "STRUCTURAL_PASS"
    assert h1.normalize_reason("STRUCTURAL_PASS", False, duplicate=True) == "DUPLICATE"


def test_checkpoint_and_mt5_stay_locked_before_20():
    cp = h1.checkpoint_contract(8)
    mt5 = h1.mt5_paper_contract(8)
    assert cp["trigger_reached"] is False
    assert cp["economics_locked_now"] is True
    assert mt5["handoff_exists"] is True
    assert mt5["handoff_ready"] is False
    assert mt5["paper_enabled"] is False
    assert mt5["orders"] == 0
    assert mt5["real_capital"] == 0


def test_20_only_readies_handoff_not_paper_activation():
    cp = h1.checkpoint_contract(20)
    mt5 = h1.mt5_paper_contract(20, reviewed=False)
    assert cp["trigger_reached"] is True
    assert cp["handoff_sequence"][0] == "FREEZE_FINAL_H1_LEDGER"
    assert mt5["handoff_ready"] is True
    assert mt5["paper_enabled"] is False
    assert mt5["activation_gate_satisfied"] is False
