"""Fixtures compartilhadas dos testes."""
import os
from pathlib import Path

import httpx
import pytest

# O agente instancia LLMConfig na criação; os testes não fazem chamadas reais.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from app.tools.web_search import WebSearch

DATA_CSV = Path(__file__).resolve().parents[1] / "data" / "payroll.csv"


@pytest.fixture
def payroll_csv() -> str:
    """Caminho para o CSV real da folha usado no desafio."""
    return str(DATA_CSV)


@pytest.fixture(autouse=True)
def _offline_web_search(monkeypatch: pytest.MonkeyPatch):
    """Nenhum teste chama serviços externos.

    Um ``WebSearch`` sem transporte injetado recebe um que sempre falha, e o
    código segue para a base de referência local, como faria sem rede.
    """
    def offline(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("rede desabilitada nos testes", request=request)

    original = WebSearch._client

    def client(self: WebSearch) -> httpx.AsyncClient:
        if self._transport is None:
            return httpx.AsyncClient(transport=httpx.MockTransport(offline))
        return original(self)

    monkeypatch.setattr(WebSearch, "_client", client)
