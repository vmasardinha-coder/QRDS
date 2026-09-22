"""Uma retificacao so atravessa fronteira de versao, e nunca em silencio.

O append-only do V12 e absoluto dentro de uma versao. Um defeito descoberto se
corrige publicando uma versao nova e reexecutando sob ela, com autorizacao
escrita, nunca recomputando sob o mesmo nome. Estes testes prendem as duas
metades: o que a autorizacao permite e o que ela continua proibindo.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_delta_v12_engine import (
    ENGINE_VERSION,
    EngineError,
    assert_append_only,
    record_version_replay,
)

REASON = "Retificacao autorizada: corte transversal congelado por dia"


def _row(date: str, chain: str, version: str, nav: str = "1.0") -> dict[str, str]:
    return {"date": date, "strategy": "V12_LS_50_50", "chain_sha256": chain,
            "engine_version": version, "normalized_nav": nav}


class VersionReplayTests(unittest.TestCase):
    def test_an_unchanged_row_is_not_a_replay(self) -> None:
        old = [_row("2026-09-08", "aaa", "DELTA_V12_ENGINE_1.0")]
        new = [_row("2026-09-08", "aaa", ENGINE_VERSION)]
        self.assertEqual(assert_append_only(old, new, REASON), [])

    def test_without_authorisation_an_older_version_still_fails_closed(self) -> None:
        old = [_row("2026-09-08", "aaa", "DELTA_V12_ENGINE_1.0")]
        new = [_row("2026-09-08", "bbb", ENGINE_VERSION)]
        with self.assertRaises(EngineError) as ctx:
            assert_append_only(old, new, "")
        self.assertIn("A restatement is not new evidence", str(ctx.exception))

    def test_authorisation_covers_a_row_from_an_earlier_version(self) -> None:
        old = [_row("2026-09-08", "aaa", "DELTA_V12_ENGINE_1.0")]
        new = [_row("2026-09-08", "bbb", ENGINE_VERSION)]
        superseded = assert_append_only(old, new, REASON)
        self.assertEqual([r["chain_sha256"] for r in superseded], ["aaa"])

    def test_authorisation_never_covers_the_current_version(self) -> None:
        # O ponto central: autorizar uma retificacao de versao nao abre a porta
        # para restatement dentro da versao corrente.
        old = [_row("2026-09-08", "aaa", ENGINE_VERSION)]
        new = [_row("2026-09-08", "bbb", ENGINE_VERSION)]
        with self.assertRaises(EngineError) as ctx:
            assert_append_only(old, new, REASON)
        self.assertIn("a version never restates itself", str(ctx.exception))

    def test_a_row_with_no_recorded_version_is_never_replayed(self) -> None:
        old = [_row("2026-09-08", "aaa", "")]
        new = [_row("2026-09-08", "bbb", ENGINE_VERSION)]
        with self.assertRaises(EngineError):
            assert_append_only(old, new, REASON)

    def test_shortening_the_ledger_is_refused_even_with_authorisation(self) -> None:
        old = [_row("2026-09-08", "aaa", "DELTA_V12_ENGINE_1.0"),
               _row("2026-09-09", "bbb", "DELTA_V12_ENGINE_1.0")]
        with self.assertRaises(EngineError) as ctx:
            assert_append_only(old, old[:1], REASON)
        self.assertIn("refusing to shorten", str(ctx.exception))

    def test_the_replay_record_keeps_both_sides_auditable(self) -> None:
        old = [_row("2026-09-08", "aaa", "DELTA_V12_ENGINE_1.0", nav="1.019")]
        new = [_row("2026-09-08", "bbb", ENGINE_VERSION, nav="1.015")]
        superseded = assert_append_only(old, new, REASON)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "RESTATEMENTS.json"
            record_version_replay(path, superseded, new, REASON, "RUN123")
            payload = json.loads(path.read_text(encoding="utf-8"))

        self.assertTrue(payload["within_a_version_restatement_is_closed"])
        self.assertIs(payload["research_only"], True)
        self.assertIs(payload["not_approved"], True)
        self.assertEqual(payload["orders_generated"], 0)
        self.assertEqual(payload["real_capital_used"], 0)
        self.assertIs(payload["promotion_allowed"], False)

        entry = payload["replays"][-1]
        self.assertEqual(entry["authorised_reason"], REASON)
        self.assertEqual(entry["replayed_by_run_id"], "RUN123")
        self.assertEqual(entry["rows_superseded"], 1)

        row = entry["rows"][0]
        self.assertEqual(row["superseded_chain_sha256"], "aaa")
        self.assertEqual(row["replacement_chain_sha256"], "bbb")
        self.assertEqual(row["superseded_normalized_nav"], "1.019")
        self.assertEqual(row["replacement_normalized_nav"], "1.015")

    def test_a_second_replay_appends_instead_of_erasing_the_first(self) -> None:
        old = [_row("2026-09-08", "aaa", "DELTA_V12_ENGINE_1.0")]
        new = [_row("2026-09-08", "bbb", ENGINE_VERSION)]
        superseded = assert_append_only(old, new, REASON)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "RESTATEMENTS.json"
            record_version_replay(path, superseded, new, REASON, "RUN1")
            record_version_replay(path, superseded, new, "outro motivo", "RUN2")
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(payload["replays"]), 2)
        self.assertEqual(payload["replays"][0]["replayed_by_run_id"], "RUN1")

    def test_nothing_superseded_writes_no_record(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "RESTATEMENTS.json"
            record_version_replay(path, [], [], REASON, "RUN1")
            self.assertFalse(path.exists())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
