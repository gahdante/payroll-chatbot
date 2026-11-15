"""Testes de RAG (extração, roteamento), busca web, formatação, modelos e agente."""

from unittest.mock import AsyncMock

import pytest

from app.tools.payroll_rag import PayrollRAG
from app.tools.web_search import WebSearch
from app.utils.formatting import format_currency, format_date, parse_currency, parse_date
from app.utils.models import ChatRequest, ChatResponse


@pytest.fixture
def rag(payroll_csv: str) -> PayrollRAG:
    return PayrollRAG(payroll_csv)


class TestExtraction:
    def test_employee_name(self, rag: PayrollRAG):
        assert rag._extract_employee_name("Qual é o salário do Ana Souza?") == "Ana Souza"
        assert rag._extract_employee_name("Quanto recebi? (Ana Souza)") == "Ana Souza"
        assert rag._extract_employee_name("Bruno Lima recebeu quanto?") == "Bruno Lima"
        assert rag._extract_employee_name("Bruno em jun/2025") == "Bruno Lima"
        assert rag._extract_employee_name("Qual o salário médio?") is None

    def test_competency(self, rag: PayrollRAG):
        assert rag._extract_competency("Quanto recebi em maio/2025?") == "2025-05"
        assert rag._extract_competency("Qual o salário em 2025-05?") == "2025-05"
        assert rag._extract_competency("Bruno em jun/2025") == "2025-06"
        assert rag._extract_competency("05/2025") == "2025-05"
        assert rag._extract_competency("Qual o salário médio?") is None

    def test_period(self, rag: PayrollRAG):
        assert rag._extract_period("1º trimestre de 2025") == ["2025-01", "2025-02", "2025-03"]
        assert rag._extract_period("primeiro trimestre de 2025") == [
            "2025-01",
            "2025-02",
            "2025-03",
        ]
        assert rag._extract_period("2º trimestre de 2025") == ["2025-04", "2025-05", "2025-06"]
        assert rag._extract_period("1º semestre de 2025") == [f"2025-{m:02d}" for m in range(1, 7)]
        assert rag._extract_period("salário de maio") is None

    def test_metric(self, rag: PayrollRAG):
        assert rag._detect_metric("desconto de INSS") == "inss"
        assert rag._detect_metric("desconto de IRRF") == "irrf"
        assert rag._detect_metric("maior bônus") == "bonus"
        assert rag._detect_metric("quando foi pago") == "payment_date"
        assert rag._detect_metric("quanto recebi líquido") == "net_pay"


class TestRagQueries:
    @pytest.mark.asyncio
    async def test_competency_listing(self, rag: PayrollRAG):
        r = await rag.query("Qual a folha de maio/2025?")
        assert r["success"] is True
        assert "Ana Souza" in r["data"] and "Bruno Lima" in r["data"]
        assert r["evidence"]["total_records"] == 2

    @pytest.mark.asyncio
    async def test_global_average(self, rag: PayrollRAG):
        r = await rag.query("Qual é o salário médio?")
        assert r["success"] is True
        assert "média" in r["data"].lower()

    @pytest.mark.asyncio
    async def test_employee_quarter_total(self, rag: PayrollRAG):
        r = await rag.query("Qual é o total líquido de Ana Souza no 1º trimestre?")
        assert r["success"] is True
        assert format_currency(23221.25) in r["data"]

    @pytest.mark.asyncio
    async def test_irrf_single_record(self, rag: PayrollRAG):
        r = await rag.query("Qual foi o desconto de IRRF da Ana em maio/2025?")
        assert r["success"] is True
        assert "IRRF" in r["data"]
        assert format_currency(551.25) in r["data"]


class TestWebSearch:
    @pytest.mark.asyncio
    async def test_reference_fallback_selic(self):
        ws = WebSearch()
        ws.use_fallback = True
        r = await ws.search_with_citation("Traga a taxa Selic atual e cite a fonte")
        assert r["success"] is True
        assert "bcb.gov.br" in r["data"]
        assert r["evidence"]["sources"][0]["url"]
        assert "note" in r  # aviso de possível desatualização

    @pytest.mark.asyncio
    async def test_reference_fallback_ferias(self):
        ws = WebSearch()
        ws.use_fallback = True
        r = await ws.search_with_citation("Como calcular férias proporcionais?")
        assert r["success"] is True
        assert "1/12" in r["data"]


class TestFormatting:
    def test_currency(self):
        assert format_currency(1500.5) == "R$ 1.500,50"
        assert format_currency(1000000) == "R$ 1.000.000,00"
        assert format_currency(660.0) == "R$ 660,00"
        assert format_currency("invalido") == "R$ 0,00"

    def test_parse_currency(self):
        assert parse_currency("R$ 1.500,50") == 1500.5
        assert parse_currency("1500.50") == 1500.5
        assert parse_currency("") is None

    def test_dates(self):
        assert format_date("2025-05-28") == "28/05/2025"
        assert parse_date("28/05/2025") == "2025-05-28"


class TestModels:
    def test_chat_request_ok(self):
        req = ChatRequest(message="  oi  ")
        assert req.message == "oi"
        assert req.session_id is None

    def test_chat_request_blank(self):
        with pytest.raises(ValueError):
            ChatRequest(message="   ")

    def test_chat_response(self):
        resp = ChatResponse(response="ok", tool_used="rag", session_id="s1")
        assert resp.evidence is None


class TestAgent:
    @pytest.mark.asyncio
    async def test_rag_routing(self):
        from app.core.agent import PayrollAgent

        agent = PayrollAgent()
        result = await agent.process_query("Quanto recebi líquido em maio/2025? (Ana Souza)")
        assert result["tool_used"] == "rag"
        assert format_currency(8418.75) in result["response"]
        assert result["evidence"]["employee_ids"] == ["E001"]
        assert result["session_id"]

    @pytest.mark.asyncio
    async def test_web_routing(self):
        from app.core.agent import PayrollAgent

        agent = PayrollAgent()
        agent.web_search.use_fallback = True
        result = await agent.process_query("Qual é o valor do FGTS?")
        assert result["tool_used"] == "web"
        assert "fgts" in result["response"].lower()

    @pytest.mark.asyncio
    async def test_session_persists_across_turns(self, monkeypatch: pytest.MonkeyPatch):
        from app.core.agent import PayrollAgent

        agent = PayrollAgent()
        monkeypatch.setattr(
            type(agent.llm), "generate_response", AsyncMock(return_value="resposta simulada")
        )

        first = await agent.process_query("Qual foi o maior bônus do Bruno e em que mês?")
        session_id = first["session_id"]
        second = await agent.process_query("E antes disso?", session_id)

        assert second["session_id"] == session_id
        assert len(agent.memory.sessions[session_id].messages) == 4
