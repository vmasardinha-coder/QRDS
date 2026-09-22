"""O corte transversal de um dia so enxerga ativos ja fixados naquele dia.

Um ativo fixado depois traz historico retroativo. Sem o recorte, ele entra na
media e no desvio de um dia passado, desloca o z-score de todos os elegiveis, e
uma linha ja gravada deixa de ser reproduzivel -- que foi o que travou a serie
DELTA_V12_ENGINE_1.0 em 2026-09-21 com "A restatement is not new evidence".
"""
from __future__ import annotations

import unittest
from datetime import date, timedelta

from tools.gate_btc_delta_v12_engine import build_panels

DAYS = 40
CFG = {"minimum_signal_history": 20}


def _dates() -> list[str]:
    start = date(2026, 8, 1)
    return [(start + timedelta(days=i)).isoformat() for i in range(DAYS)]


def _panel(dates: list[str], bases: list[str]) -> dict:
    # Trajetorias distintas e deterministas, para que o corte transversal tenha
    # dispersao e os z-scores fiquem definidos.
    slopes = {b: 1.0 + 0.003 * (i + 1) for i, b in enumerate(bases)}
    out: dict[str, dict[str, dict[str, float]]] = {}
    for i, day in enumerate(dates):
        row = {}
        for b in bases:
            close = 100.0 * (slopes[b] ** i) + (i % 5) * (bases.index(b) + 1) * 0.1
            row[b] = {"close": close, "volume": 1000.0 + 10 * i + bases.index(b)}
        out[day] = row
    return out


class CrossSectionPanelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dates = _dates()
        self.bases = ["AAA", "BBB", "CCC", "DDD", "LATE"]
        self.panel = _panel(self.dates, self.bases)
        self.day = self.dates[-1]
        # LATE so foi fixado depois do ultimo dia da amostra, mas o painel ja
        # carrega o historico retroativo dele.
        self.admitted = {b: self.dates[0] for b in self.bases}
        self.admitted["LATE"] = "2026-12-31"

    def test_a_late_pin_has_no_score_on_a_day_it_was_not_admitted(self) -> None:
        cut = build_panels(self.dates, self.bases, self.panel, CFG, self.admitted)
        self.assertIsNone(cut["score"][self.day]["LATE"])

    def test_a_late_pin_would_otherwise_score_and_shift_the_others(self) -> None:
        full = build_panels(self.dates, self.bases, self.panel, CFG)
        cut = build_panels(self.dates, self.bases, self.panel, CFG, self.admitted)

        self.assertIsNotNone(
            full["score"][self.day]["LATE"],
            "sem o recorte o ativo fixado depois entra no corte transversal")

        moved = [b for b in self.bases if b != "LATE"
                 and full["score"][self.day][b] != cut["score"][self.day][b]]
        self.assertTrue(
            moved,
            "um ativo a mais no corte transversal tem de deslocar a media e o "
            "desvio, e portanto o z-score dos demais; se nada se move o recorte "
            "nao esta protegendo nada")

    def test_without_provenance_the_behaviour_is_unchanged(self) -> None:
        # Sem PRICE_PROVENANCE.json o motor mantem o comportamento anterior, em
        # vez de silenciosamente recortar sobre um mapa vazio e zerar a serie.
        a = build_panels(self.dates, self.bases, self.panel, CFG)
        b = build_panels(self.dates, self.bases, self.panel, CFG, None)
        self.assertEqual(a["score"], b["score"])

    def test_the_cut_is_monotonic_as_pins_accumulate(self) -> None:
        # Admitir mais ativos nunca pode reduzir o conjunto pontuado do dia.
        early = dict(self.admitted)
        early["DDD"] = "2026-12-31"
        fewer = build_panels(self.dates, self.bases, self.panel, CFG, early)
        more = build_panels(self.dates, self.bases, self.panel, CFG, self.admitted)
        scored_fewer = {b for b in self.bases if fewer["score"][self.day][b] is not None}
        scored_more = {b for b in self.bases if more["score"][self.day][b] is not None}
        self.assertTrue(scored_fewer.issubset(scored_more))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
