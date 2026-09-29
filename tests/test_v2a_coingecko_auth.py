from __future__ import annotations

import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import requests


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "migration/canonical/v2a/scripts/00_run_all_v2a.py"
)


def load_v2a():
    spec = importlib.util.spec_from_file_location("v2a_coingecko_auth_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CoinGeckoDemoAuthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v2a = load_v2a()

    def test_demo_key_is_header_only_on_frozen_endpoint(self):
        with patch.dict(os.environ, {"COINGECKO_DEMO_API_KEY": "test-secret"}, clear=False):
            session = self.v2a.session_or_raise()
        prepared = session.prepare_request(
            requests.Request("GET", "https://api.coingecko.com/api/v3/coins/markets",
                             params={"vs_currency": "usd", "page": 1})
        )
        self.assertEqual(prepared.headers["x-cg-demo-api-key"], "test-secret")
        self.assertNotIn("test-secret", prepared.url)
        self.assertIn("/api/v3/coins/markets", prepared.url)
        session.close()

    def test_missing_key_keeps_public_transport(self):
        with patch.dict(os.environ, {"COINGECKO_DEMO_API_KEY": ""}, clear=False):
            session = self.v2a.session_or_raise()
        self.assertNotIn("x-cg-demo-api-key", session.headers)
        session.close()


if __name__ == "__main__":
    unittest.main()
