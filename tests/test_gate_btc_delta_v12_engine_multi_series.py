"""O motor roda mais de uma serie preregistrada sem perder a identidade de cada uma.

O V12 fechou por lacuna de dados e o V13 o sucede sob ancora propria. Os dois
usam o mesmo codigo, entao o codigo tem de saber de qual serie e cada linha que
grava -- e, mais importante, o contrato tem de poder NOMEAR seus livros sem
poder REPESA-LOS. Um contrato capaz de escolher o proprio split bruto retunaria
a estrategia sem uma linha de codigo mudar.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.gate_btc_delta_v12_engine import (
    BOOK_SHAPES,
    BOOKS,
    ENGINE_VERSION,
    SUPPORTED_ENGINE_VERSIONS,
    EngineError,
    assert_append_only,
    books_for,
    load_or_create_anchor,
    record_version_replay,
)

V13 = "DELTA_V13_ENGINE_1.0"


def _contract(names: list[str]) -> dict:
    return {"books": {"books": names}}


def _named(prefix: str) -> list[str]:
    return [f"{prefix}_{shape['suffix']}" for shape in BOOK_SHAPES]


class BooksFromTheContractTests(unittest.TestCase):
    def test_the_contract_names_its_own_books(self) -> None:
        books = books_for(_contract(_named("V13")))
        self.assertEqual([b["strategy"] for b in books],
                         ["V13_LS_70_30", "V13_LS_70_30_StopVol",
                          "V13_LS_50_50", "V13_LS_50_50_StopVol"])

    def test_the_shapes_are_frozen_whatever_the_names(self) -> None:
        # O ponto central: renomear nao repesa. O V13 carrega exatamente os
        # mesmos splits e as mesmas flags de StopVol do V12.
        v12 = {b["strategy"].split("_LS_", 1)[1]: b for b in BOOKS}
        for book in books_for(_contract(_named("V13"))):
            twin = v12[book["strategy"].split("_LS_", 1)[1]]
            self.assertEqual(book["gross_long"], twin["gross_long"])
            self.assertEqual(book["gross_short"], twin["gross_short"])
            self.assertEqual(book["stopvol"], twin["stopvol"])

    def test_a_contract_cannot_set_its_own_gross_split(self) -> None:
        # Mesmo declarando pesos, o contrato nao e lido para isso.
        contract = _contract(_named("V13"))
        contract["books"]["gross_long"] = 0.95
        contract["books"]["V13_LS_50_50"] = {"gross_long": 0.95, "gross_short": 0.05}
        for book in books_for(contract):
            self.assertIn(book["gross_long"], (0.70, 0.50))
            self.assertIn(book["gross_short"], (0.30, 0.50))

    def test_a_missing_book_is_refused(self) -> None:
        with self.assertRaises(EngineError) as ctx:
            books_for(_contract(_named("V13")[:3]))
        self.assertIn("always in parallel", str(ctx.exception))

    def test_a_fifth_book_is_refused(self) -> None:
        with self.assertRaises(EngineError):
            books_for(_contract(_named("V13") + ["V13_LS_90_10"]))

    def test_reordering_the_books_is_refused(self) -> None:
        names = _named("V13")
        names[0], names[2] = names[2], names[0]
        with self.assertRaises(EngineError) as ctx:
            books_for(_contract(names))
        self.assertIn("do not match the frozen shapes", str(ctx.exception))

    def test_two_prefixes_in_one_contract_are_refused(self) -> None:
        names = _named("V13")
        names[1] = "V12_LS_70_30_StopVol"
        with self.assertRaises(EngineError):
            books_for(_contract(names))

    def test_the_v12_books_still_resolve_unchanged(self) -> None:
        self.assertEqual(books_for(_contract(_named("V12"))), BOOKS)


class VersionIsPerSeriesTests(unittest.TestCase):
    def test_both_series_are_supported_and_nothing_else_is(self) -> None:
        self.assertIn(ENGINE_VERSION, SUPPORTED_ENGINE_VERSIONS)
        self.assertIn(V13, SUPPORTED_ENGINE_VERSIONS)
        self.assertNotIn("DELTA_V12_ENGINE_1.0", SUPPORTED_ENGINE_VERSIONS)

    def test_the_anchor_records_the_series_that_created_it(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "ANCHOR.json"
            load_or_create_anchor(path, "2026-09-22", "2026-09-22", "RUN1", V13)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["engine_version"], V13)
        self.assertIs(payload["backdating_prohibited"], True)

    def test_a_replay_authorisation_never_covers_the_running_series(self) -> None:
        # Sob o V13, uma linha V13 continua intocavel -- a regra e por serie, nao
        # uma constante global que o V13 herdaria do V12.
        old = [{"date": "2026-09-23", "strategy": "V13_LS_50_50",
                "chain_sha256": "aaa", "engine_version": V13}]
        new = [{"date": "2026-09-23", "strategy": "V13_LS_50_50",
                "chain_sha256": "bbb", "engine_version": V13}]
        with self.assertRaises(EngineError) as ctx:
            assert_append_only(old, new, "motivo", V13)
        self.assertIn("a version never restates itself", str(ctx.exception))

    def test_a_v12_row_is_not_replayable_by_a_v13_run(self) -> None:
        # Uma serie nunca reescreve o ledger de outra, autorizacao ou nao. O
        # ledger do V13 e proprio; se uma linha V12 aparecesse nele, seria
        # superada em silencio se este teste nao existisse.
        old = [{"date": "2026-09-19", "strategy": "V12_LS_50_50",
                "chain_sha256": "aaa", "engine_version": "DELTA_V12_ENGINE_1.0"}]
        new = [{"date": "2026-09-19", "strategy": "V13_LS_50_50",
                "chain_sha256": "bbb", "engine_version": V13}]
        superseded = assert_append_only(old, new, "motivo", V13)
        self.assertEqual([r["strategy"] for r in superseded], ["V12_LS_50_50"])
        with self.assertRaises(EngineError):
            assert_append_only(old, new, "", V13)

    def test_the_real_v13_contract_runs_end_to_end_under_its_own_identity(self) -> None:
        # Nao basta as pecas passarem isoladas: o contrato do V13 como esta em
        # disco tem de atravessar run() e produzir um ledger com a identidade
        # dele -- ancora, versao e nomes de livro.
        from tests.test_gate_btc_delta_v12_engine import price_panel, write_inputs
        from tools import gate_btc_delta_v12_engine as engine

        contract = Path("migration/reporting/delta_v13_engine_contract.json")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # 90 dias a partir de 2026-06-25 terminam em 2026-09-22, o not_before
            # congelado; um painel mais curto seria recusado como backdating.
            prices, universe = write_inputs(root, price_panel(days=90))
            status = engine.run(prices, universe, contract, root / "ledger", "RUN13")

            self.assertEqual(status["engine_version"], V13)
            self.assertEqual(status["anchor_date"], "2026-09-22")
            self.assertTrue(all(name.startswith("V13_") for name in status["books"]), status["books"])
            self.assertIs(status["promotion_allowed"], False)
            self.assertIs(status["research_only"], True)
            self.assertEqual(status["orders_generated"], 0)

            anchor = json.loads((root / "ledger" / "ANCHOR.json").read_text(encoding="utf-8"))
            self.assertEqual(anchor["engine_version"], V13)

    def test_the_replay_record_names_the_version_that_wrote_it(self) -> None:
        old = [{"date": "2026-09-19", "strategy": "V13_LS_50_50", "chain_sha256": "aaa",
                "engine_version": "DELTA_V12_ENGINE_1.0", "normalized_nav": "1.0"}]
        new = [{"date": "2026-09-19", "strategy": "V13_LS_50_50", "chain_sha256": "bbb",
                "engine_version": V13, "normalized_nav": "1.1"}]
        superseded = assert_append_only(old, new, "motivo", V13)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "RESTATEMENTS.json"
            record_version_replay(path, superseded, new, "motivo", "RUN1", V13)
            payload = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(payload["replays"][-1]["rows"][0]["to_engine_version"], V13)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
