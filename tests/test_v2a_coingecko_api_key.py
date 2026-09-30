"""A chave da CoinGecko vai so na chamada da CoinGecko, e so quando existe.

A coleta de 2026-09-28 caiu com `CoinGecko universe failed: HTTP 403` e levou
junto o V11, que nao le um unico numero desta fonte. A API nao estava fora do
ar: ela recusa chamada anonima vinda de IP de datacenter. A chave resolve isso,
e estes testes fixam as duas propriedades que importam nela -- sem chave o
comportamento e byte a byte o de sempre, e com chave o header nao escapa para
nenhum outro host.
"""
from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "migration/canonical/v2a/scripts/00_run_all_v2a.py"


def _load():
    spec = importlib.util.spec_from_file_location("v2a_run_all", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoinGeckoEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load()
        self._saved = {k: os.environ.get(k) for k in ("COINGECKO_API_KEY", "COINGECKO_API_PLAN")}
        for key in self._saved:
            os.environ.pop(key, None)

    def tearDown(self) -> None:
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_without_a_key_nothing_changes(self) -> None:
        # O caminho sem chave tem de continuar identico ao que sempre foi: host
        # publico e nenhum header. Se este teste quebrar, a mudanca deixou de
        # ser aditiva e passou a alterar a coleta de quem nao configurou nada.
        base, headers = self.module.coingecko_endpoint_and_headers()
        self.assertEqual(base, "https://api.coingecko.com/api/v3")
        self.assertEqual(headers, {})

    def test_an_empty_or_blank_key_counts_as_no_key(self) -> None:
        for blank in ("", "   ", "\n"):
            os.environ["COINGECKO_API_KEY"] = blank
            base, headers = self.module.coingecko_endpoint_and_headers()
            self.assertEqual(headers, {}, blank)
            self.assertEqual(base, "https://api.coingecko.com/api/v3")

    def test_a_demo_key_uses_the_demo_header_on_the_public_host(self) -> None:
        os.environ["COINGECKO_API_KEY"] = "CG-demo-123"
        base, headers = self.module.coingecko_endpoint_and_headers()
        self.assertEqual(base, "https://api.coingecko.com/api/v3")
        self.assertEqual(headers, {"x-cg-demo-api-key": "CG-demo-123"})

    def test_a_pro_key_moves_host_and_header_together(self) -> None:
        # Os dois andam juntos: chave pro no host publico e header demo no host
        # pro respondem 400. Separar os dois seria um jeito silencioso de voltar
        # a falhar.
        os.environ["COINGECKO_API_KEY"] = "CG-pro-456"
        os.environ["COINGECKO_API_PLAN"] = "pro"
        base, headers = self.module.coingecko_endpoint_and_headers()
        self.assertEqual(base, "https://pro-api.coingecko.com/api/v3")
        self.assertEqual(headers, {"x-cg-pro-api-key": "CG-pro-456"})

    def test_an_unknown_plan_fails_closed(self) -> None:
        os.environ["COINGECKO_API_KEY"] = "CG-x"
        os.environ["COINGECKO_API_PLAN"] = "enterprise"
        with self.assertRaises(RuntimeError) as ctx:
            self.module.coingecko_endpoint_and_headers()
        self.assertIn("demo", str(ctx.exception))

    def test_the_key_never_reaches_the_shared_session(self) -> None:
        # O ponto central. A sessao desta coleta tambem fala com Binance, OKX e
        # outras; um header global mandaria a chave da CoinGecko para todas
        # elas. Por isso o header e passado por chamada, e a sessao tem de
        # continuar limpa mesmo com a chave configurada.
        os.environ["COINGECKO_API_KEY"] = "CG-secret"
        session = self.module.session_or_raise()
        joined = " ".join(f"{k}:{v}" for k, v in session.headers.items())
        self.assertNotIn("CG-secret", joined)
        self.assertNotIn("x-cg-demo-api-key", {k.lower() for k in session.headers})


class CoinGeckoCallSiteTests(unittest.TestCase):
    def test_the_universe_call_sends_the_header_and_keeps_the_frozen_params(self) -> None:
        # A chave nao pode virar desculpa para mexer no que e pedido. Os
        # parametros da chamada sao os mesmos de sempre; muda so a autenticacao.
        module = _load()
        saved = os.environ.get("COINGECKO_API_KEY")
        os.environ["COINGECKO_API_KEY"] = "CG-demo-789"
        seen: list[dict] = []

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return [{"symbol": "btc", "id": "bitcoin"}]

        class FakeSession:
            headers: dict[str, str] = {}

            def get(self, url, params=None, headers=None, timeout=None):
                seen.append({"url": url, "params": params, "headers": headers})
                return FakeResponse()

        try:
            module.time.sleep = lambda *_: None
            module.save_df = lambda *_args, **_kwargs: None
            module.fetch_coingecko_universe(FakeSession(), 1)
        finally:
            if saved is None:
                os.environ.pop("COINGECKO_API_KEY", None)
            else:
                os.environ["COINGECKO_API_KEY"] = saved

        self.assertEqual(len(seen), 1)
        self.assertEqual(seen[0]["url"], "https://api.coingecko.com/api/v3/coins/markets")
        self.assertEqual(seen[0]["headers"], {"x-cg-demo-api-key": "CG-demo-789"})
        self.assertEqual(seen[0]["params"]["vs_currency"], "usd")
        self.assertEqual(seen[0]["params"]["order"], "market_cap_desc")
        self.assertEqual(seen[0]["params"]["per_page"], 250)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
