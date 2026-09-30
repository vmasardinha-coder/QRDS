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
        self._saved = {
            k: os.environ.get(k)
            for k in ("COINGECKO_API_KEY", "COINGECKO_DEMO_API_KEY", "COINGECKO_API_PLAN")
        }
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

    def test_the_alternate_secret_name_is_honoured(self) -> None:
        # O repositorio tem dois nomes em uso para o mesmo segredo. Ler so um
        # deixaria o outro configurado sem efeito, e o coletor voltaria ao
        # anonimo sem erro nenhum -- o modo silencioso que custou dois dias ao
        # V11. Os dois nomes valem.
        os.environ["COINGECKO_DEMO_API_KEY"] = "CG-alt-999"
        base, headers = self.module.coingecko_endpoint_and_headers()
        self.assertEqual(base, "https://api.coingecko.com/api/v3")
        self.assertEqual(headers, {"x-cg-demo-api-key": "CG-alt-999"})

    def test_the_primary_name_wins_when_both_are_set(self) -> None:
        os.environ["COINGECKO_API_KEY"] = "CG-primary"
        os.environ["COINGECKO_DEMO_API_KEY"] = "CG-alternate"
        _, headers = self.module.coingecko_endpoint_and_headers()
        self.assertEqual(headers, {"x-cg-demo-api-key": "CG-primary"})

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
        os.environ["COINGECKO_DEMO_API_KEY"] = "CG-secret-alt"
        session = self.module.session_or_raise()
        joined = " ".join(f"{k}:{v}" for k, v in session.headers.items())
        self.assertNotIn("CG-secret", joined)
        self.assertNotIn("CG-secret-alt", joined)
        # A mesma sessao chama cryptodatadownload.com e www.okx.com. Um header
        # global mandaria a chave da CoinGecko para os dois.
        self.assertNotIn("x-cg-demo-api-key", {k.lower() for k in session.headers})


class CoinGeckoCallSiteTests(unittest.TestCase):
    def test_backup_retries_the_whole_universe_without_mixing_pages(self) -> None:
        module = _load()
        from unittest.mock import patch
        requests_seen = []

        class FakeResponse:
            def __init__(self, status, page):
                self.status_code = status
                self.page = page

            def json(self):
                return [{"symbol": "btc" if self.page == 1 else "eth", "id": str(self.page)}]

        class FakeSession:
            def get(self, url, params=None, headers=None, timeout=None):
                requests_seen.append((params["page"], dict(headers)))
                if headers.get("x-cg-demo-api-key") == "first" and params["page"] == 2:
                    return FakeResponse(429, params["page"])
                return FakeResponse(200, params["page"])

        with patch.dict(os.environ, {
            "COINGECKO_API_KEY": "first",
            "COINGECKO_API_KEY_BACKUP": "second",
            "COINGECKO_API_PLAN": "demo",
        }), patch.object(module.time, "sleep"), patch.object(module, "save_df"):
            frame = module.fetch_coingecko_universe(FakeSession(), 500)
        self.assertEqual(
            requests_seen,
            [(1, {"x-cg-demo-api-key": "first"}),
             (2, {"x-cg-demo-api-key": "first"}),
             (1, {"x-cg-demo-api-key": "second"}),
             (2, {"x-cg-demo-api-key": "second"})],
        )
        self.assertEqual(frame["symbol"].tolist(), ["BTC", "ETH"])

    def test_backup_failure_stays_closed_without_exposing_keys(self) -> None:
        module = _load()
        from unittest.mock import patch

        class FakeSession:
            def get(self, url, params=None, headers=None, timeout=None):
                return type("Response", (), {"status_code": 403})()

        with patch.dict(os.environ, {
            "COINGECKO_API_KEY": "first-secret",
            "COINGECKO_API_KEY_BACKUP": "backup-secret",
            "COINGECKO_API_PLAN": "demo",
        }):
            with self.assertRaisesRegex(RuntimeError, "CoinGecko universe failed: HTTP 403") as error:
                module.fetch_coingecko_universe(FakeSession(), 1)
        self.assertNotIn("first-secret", str(error.exception))
        self.assertNotIn("backup-secret", str(error.exception))

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
