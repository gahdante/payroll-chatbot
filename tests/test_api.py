"""Testes da API HTTP (app/main.py)."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.utils.formatting import format_currency
from app.utils.models import MAX_MESSAGE_LENGTH, MAX_SESSION_ID_LENGTH


@pytest.fixture
def client() -> Iterator[TestClient]:
    # O "with" roda o lifespan, que cria um agente novo para cada teste.
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_without_llm(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with TestClient(app) as c:
        yield c


def _chat(client: TestClient, message: str, session_id: str | None = None) -> dict[str, Any]:
    response = client.post("/chat", json={"message": message, "session_id": session_id})
    assert response.status_code == 200, response.text
    return response.json()


def _assert_error_format(body: dict[str, Any], status_code: int) -> None:
    """Todos os erros saem como {"error", "status_code", "timestamp"}."""
    assert body["status_code"] == status_code
    assert isinstance(body["error"], str) and body["error"]
    assert "timestamp" in body
    assert "detail" not in body


class TestStatus:
    def test_root(self, client: TestClient):
        assert client.get("/").json()["status"] == "running"

    def test_health(self, client: TestClient):
        body = client.get("/health").json()
        assert body["status"] == "healthy"
        assert body["dependencies"]["rag"] == "ok"
        assert body["dependencies"]["llm"] == "ok"

    def test_health_without_llm_is_degraded(self, client_without_llm: TestClient):
        body = client_without_llm.get("/health").json()
        assert body["status"] == "degraded"
        assert body["dependencies"]["llm"] == "sem OPENAI_API_KEY"

    def test_examples(self, client: TestClient):
        assert client.get("/examples").json()["rag"]


class TestChat:
    def test_rag_question(self, client: TestClient):
        body = _chat(client, "Quanto recebi (líquido) em maio/2025? (Ana Souza)")
        assert body["tool_used"] == "rag"
        assert format_currency(8418.75) in body["response"]
        assert body["evidence"]["employee_ids"] == ["E001"]
        assert body["session_id"]

    def test_follow_up_with_session_id(self, client: TestClient):
        first = _chat(client, "Quanto a Ana recebeu em maio/2025?")
        second = _chat(client, "E em junho?", first["session_id"])
        assert second["session_id"] == first["session_id"]
        assert second["evidence"]["employee_ids"] == ["E001"]
        assert second["evidence"]["competencies"] == ["2025-06"]

    def test_session_id_in_url(self, client: TestClient):
        response = client.post("/chat/minha-sessao", json={"message": "Qual a folha de maio/2025?"})
        assert response.json()["session_id"] == "minha-sessao"

    def test_web_question(self, client: TestClient):
        body = _chat(client, "Como funciona o aviso prévio?")
        assert body["tool_used"] == "web"
        assert "12.506" in body["response"]

    def test_general_chat_without_llm(self, client_without_llm: TestClient):
        body = _chat(client_without_llm, "Olá, tudo bem?")
        assert body["tool_used"] == "general"
        assert "folha de pagamento" in body["response"]


class TestSessions:
    def test_context_stats_and_delete(self, client: TestClient):
        session_id = _chat(client, "Quanto a Ana recebeu em maio/2025?")["session_id"]

        context = client.get(f"/sessions/{session_id}/context").json()
        assert context["employee_mentions"] == ["Ana Souza"]
        assert context["total_messages"] == 2
        assert client.get("/sessions/stats").json()["total_sessions"] == 1

        assert client.delete(f"/sessions/{session_id}").status_code == 200
        again = client.delete(f"/sessions/{session_id}")
        assert again.status_code == 404
        _assert_error_format(again.json(), 404)
        assert again.json()["error"] == "Sessão não encontrada"


class TestErrors:
    def test_message_too_long(self, client: TestClient):
        response = client.post("/chat", json={"message": "a" * (MAX_MESSAGE_LENGTH + 1)})
        assert response.status_code == 422
        body = response.json()
        _assert_error_format(body, 422)
        assert body["error"] == f"A mensagem precisa ter entre 1 e {MAX_MESSAGE_LENGTH} caracteres."
        assert body["details"][0]["campo"] == "body.message"

    def test_blank_message(self, client: TestClient):
        response = client.post("/chat", json={"message": "   "})
        assert response.status_code == 422
        assert "mensagem" in response.json()["error"]

    def test_session_id_too_long(self, client: TestClient):
        long_id = "x" * (MAX_SESSION_ID_LENGTH + 1)
        for response in (
            client.post("/chat", json={"message": "oi", "session_id": long_id}),
            client.post(f"/chat/{long_id}", json={"message": "oi"}),
        ):
            assert response.status_code == 422
            assert "session_id" in response.json()["error"]

    def test_unknown_route(self, client: TestClient):
        response = client.get("/nao-existe")
        assert response.status_code == 404
        _assert_error_format(response.json(), 404)

    def test_wrong_method_keeps_allow_header(self, client: TestClient):
        response = client.put("/chat", json={"message": "oi"})
        assert response.status_code == 405
        _assert_error_format(response.json(), 405)
        assert "POST" in response.headers["allow"]
