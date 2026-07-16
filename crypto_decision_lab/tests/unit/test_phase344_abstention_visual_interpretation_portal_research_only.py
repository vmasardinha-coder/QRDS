from __future__ import annotations

import json

from tests.unit._phase336_345_fixtures import create_previous_state, patch_roots, run_chain

def test_phase344_portal_contains_required_plain_language_blocks(tmp_path, monkeypatch):
    patch_roots(monkeypatch, tmp_path)
    paths=run_chain(tmp_path, create_previous_state(tmp_path), through=344)
    item=json.loads(paths[344].read_text())
    portal=tmp_path/item["portal_path"]
    text=portal.read_text(encoding="utf-8")
    for heading in ("O QUE FOI COLETADO","O QUE FOI TESTADO","QUAL ERA A PERGUNTA","O QUE O RESULTADO SIGNIFICA","EXEMPLO COM R$10.000","POR QUE FOI REPROVADO OU APROVADO","O QUE O TESTE NAO PROVA","CONCLUSAO PRATICA","VOCE ESTA AQUI"):
        assert heading in text
    assert item["capital_authorized_brl"] == 0
