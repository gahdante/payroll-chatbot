"""Regressões: perguntas que recebiam resposta errada antes da revisão."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pandas as pd
import pytest
import uvicorn

import run
from app.core.agent import PayrollAgent
from app.core.conversation_memory import ConversationMemory
from app.tools.payroll_rag import PayrollRAG
from app.tools.web_search import WebSearch
from app.utils.formatting import format_currency, parse_currency


@pytest.fixture
def rag(payroll_csv: str) -> PayrollRAG:
    return PayrollRAG(payroll_csv)


@pytest.fixture
def agent(monkeypatch: pytest.MonkeyPatch) -> PayrollAgent:
    agent = PayrollAgent()
    agent.web_search.use_fallback = True
    monkeypatch.setattr(agent.llm, "generate_response", AsyncMock(return_value="resposta do LLM"))
    return agent


async def _chat(agent: PayrollAgent, *messages: str) -> dict[str, Any]:
    """Envia as mensagens na mesma sessão e devolve a última resposta."""
    session_id: str | None = None
    result: dict[str, Any] = {}
    for message in messages:
        result = await agent.process_query(message, session_id)
        session_id = result["session_id"]
    return result


class TestRouting:
    def test_name_inside_other_word_is_not_an_employee(self, agent: PayrollAgent):
        # "semana" contém "ana"
        assert agent._route("Quantas horas extras por semana posso fazer?")[0] != "rag"

    def test_legislation_about_inss_goes_to_web(self, agent: PayrollAgent):
        assert agent._route("Qual a alíquota do INSS?")[0] == "web"

    def test_year_in_legislation_question_stays_web(self, agent: PayrollAgent):
        assert agent._route("Como funciona o 13º salário em 2025?")[0] == "web"

    def test_competency_without_name_goes_to_rag(self, agent: PayrollAgent):
        assert agent._route("Qual a folha de maio/2025?")[0] == "rag"


class TestAggregates:
    async def test_total_respects_requested_metric(self, rag: PayrollRAG):
        r = await rag.query("Qual o total de INSS da Ana no 1º trimestre de 2025?")
        assert r["success"] is True
        assert f"Total de INSS: {format_currency(2640)}" in r["data"]
        assert "Total líquido" not in r["data"]

    async def test_year_is_a_period_filter(self, rag: PayrollRAG):
        r = await rag.query("Qual o total de bônus do Bruno em 2025?")
        assert f"Total de bônus: {format_currency(2800)}" in r["data"]
        assert r["data"].startswith("Bruno Lima — 2025:")
        assert "ano de" not in r["data"]

    async def test_last_quarter_is_the_latest_with_data(self, rag: PayrollRAG):
        r = await rag.query("Quanto a Ana recebeu no último trimestre?")
        assert "2º trimestre de 2025" in r["data"]
        assert format_currency(23591.25) in r["data"]
        assert r["evidence"]["competencies"] == ["2025-04", "2025-05", "2025-06"]

    async def test_quarter_without_number_asks_which(self, rag: PayrollRAG):
        r = await rag.query("Quanto a Ana recebeu no trimestre?")
        assert r["success"] is False
        assert "Qual trimestre" in r["data"]

    async def test_invalid_semester(self, rag: PayrollRAG):
        r = await rag.query("Total da Ana no 3º semestre de 2025")
        assert r["success"] is False


class TestRecords:
    async def test_deductions_breakdown(self, rag: PayrollRAG):
        r = await rag.query("Qual foi o desconto do Bruno em abril/2025?")
        assert f"Desconto de INSS: {format_currency(660)}" in r["data"]
        assert f"Desconto de IRRF: {format_currency(333.75)}" in r["data"]
        assert f"Outros descontos: {format_currency(200)}" in r["data"]
        assert f"Total de descontos: {format_currency(1193.75)}" in r["data"]

    async def test_payslip_shows_every_field(self, rag: PayrollRAG):
        r = await rag.query("Holerite do Bruno em abril/2025")
        for label in ("Salário base", "Benefícios (VT/VR)", "Outros proventos", "Outros descontos"):
            assert label in r["data"]

    async def test_extreme_for_net_pay(self, rag: PayrollRAG):
        r = await rag.query("Qual o maior salário líquido da Ana?")
        assert format_currency(8418.75) in r["data"]
        assert r["evidence"]["competencies"] == ["2025-05"]

    async def test_extreme_reports_ties(self, rag: PayrollRAG):
        r = await rag.query("Qual o menor bônus do Bruno?")
        assert r["evidence"]["competencies"] == ["2025-02", "2025-04"]
        assert "2025-02" in r["data"] and "2025-04" in r["data"]

    async def test_extreme_across_employees(self, rag: PayrollRAG):
        r = await rag.query("Qual o maior bônus?")
        assert format_currency(1200) in r["data"]
        assert r["evidence"]["employee_ids"] == ["E001", "E002"]

    async def test_month_without_year_uses_latest_year(self, rag: PayrollRAG):
        r = await rag.query("Quanto recebi em maio? (Ana Souza)")
        assert format_currency(8418.75) in r["data"]
        assert r["evidence"]["competencies"] == ["2025-05"]

    async def test_competency_listing_has_total(self, rag: PayrollRAG):
        r = await rag.query("Qual a folha de maio/2025?")
        assert f"Total (líquido): {format_currency(8418.75 + 6788.75)}" in r["data"]


class TestNames:
    @pytest.fixture
    def rag_two_anas(self, tmp_path: Path, payroll_csv: str) -> PayrollRAG:
        df = pd.read_csv(payroll_csv)
        other = df[df["name"] == "Ana Souza"].copy()
        other["employee_id"] = "E003"
        other["name"] = "Ana Araújo"
        path = tmp_path / "payroll.csv"
        pd.concat([df, other]).to_csv(path, index=False)
        return PayrollRAG(path)

    async def test_ambiguous_first_name_asks_which(self, rag_two_anas: PayrollRAG):
        r = await rag_two_anas.query("Quanto a Ana recebeu em maio/2025?")
        assert r["success"] is False
        assert "Ana Araújo" in r["data"] and "Ana Souza" in r["data"]

    async def test_name_without_accents(self, rag_two_anas: PayrollRAG):
        r = await rag_two_anas.query("Quanto a ana araujo recebeu em maio/2025?")
        assert r["success"] is True
        assert r["evidence"]["employee_ids"] == ["E003"]


class TestFollowUps:
    async def test_follow_up_chain(self, agent: PayrollAgent):
        r = await _chat(agent, "Quanto a Ana recebeu em maio/2025?", "E em junho?")
        assert r["tool_used"] == "rag"
        assert format_currency(7586.25) in r["response"]
        assert r["evidence"]["competencies"] == ["2025-06"]

        session = r["session_id"]
        r = await agent.process_query("E o Bruno?", session)
        assert r["evidence"]["employee_ids"] == ["E002"]
        assert r["evidence"]["competencies"] == ["2025-06"]

        r = await agent.process_query("E o INSS?", session)
        assert f"Desconto de INSS: {format_currency(660)}" in r["response"]

        r = await agent.process_query("E no 1º trimestre?", session)
        assert f"Total de INSS: {format_currency(1980)}" in r["response"]

    async def test_small_talk_keeps_the_thread(self, agent: PayrollAgent):
        r = await _chat(agent, "Qual o bônus da Ana em maio/2025?", "Obrigado!", "E em março?")
        assert r["tool_used"] == "rag"
        assert f"Bônus: {format_currency(800)}" in r["response"]
        assert r["evidence"]["employee_ids"] == ["E001"]

    async def test_web_question_breaks_the_thread(self, agent: PayrollAgent):
        r = await _chat(
            agent, "Quanto a Ana recebeu em maio/2025?", "Qual é o valor do FGTS?", "E em março?"
        )
        assert r["evidence"]["total_records"] == 2  # folha do mês, sem filtrar a Ana

    async def test_full_question_does_not_inherit(self, agent: PayrollAgent):
        r = await _chat(agent, "Quanto a Ana recebeu em maio/2025?", "Qual a folha de junho/2025?")
        assert r["evidence"]["total_records"] == 2


class TestFormatting:
    def test_brazilian_string_input(self):
        assert format_currency("1.500,50") == "R$ 1.500,50"
        assert format_currency("R$ 2.000") == "R$ 2.000,00"

    def test_parse_thousands_separator(self):
        assert parse_currency("1.500") == 1500.0
        assert parse_currency("1.500.000,00") == 1500000.0
        assert parse_currency("1500.50") == 1500.5

    def test_negative(self):
        assert format_currency(-10) == "-R$ 10,00"
        assert parse_currency("-R$ 10,50") == -10.5

    def test_half_cent_rounds_up(self):
        assert format_currency(2.675) == "R$ 2,68"  # f"{2.675:.2f}" dá "2.67"

    def test_nan(self):
        assert format_currency(float("nan")) == "R$ 0,00"


class TestContextSummary:
    def test_maior_is_not_may(self):
        memory = ConversationMemory()
        sid = memory.create_session()
        memory.add_message(sid, "user", "Qual o maior bônus do Bruno?")
        assert memory.get_context_summary(sid)["competencies_mentioned"] == []

    async def test_mentions_come_from_evidence(self, agent: PayrollAgent):
        r = await agent.process_query("Qual foi o maior bônus do Bruno e em que mês?")
        summary = agent.get_context_summary(r["session_id"])
        assert summary["employee_mentions"] == ["Bruno Lima"]
        assert summary["competencies_mentioned"] == ["2025-05"]
        assert "bônus" in summary["topics_discussed"]


class TestSelic:
    async def test_live_rate_from_central_bank(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["params"] = dict(request.url.params)
            return httpx.Response(
                200,
                json=[
                    {"data": "14/11/2026", "valor": "13.75"},
                    {"data": "15/11/2026", "valor": "13.75"},
                ],
            )

        ws = WebSearch(transport=httpx.MockTransport(handler))
        r = await ws.search_with_citation("Traga a taxa Selic atual e cite a fonte")

        assert "13,75% ao ano" in r["data"]
        assert "15/11/2026" in r["data"]
        assert "bcb.gov.br" in r["data"]
        assert "note" not in r  # dado ao vivo, sem aviso de desatualização
        assert seen["params"]["dataFinal"] == date.today().strftime("%d/%m/%Y")

    async def test_central_bank_failure_falls_back(self):
        ws = WebSearch(transport=httpx.MockTransport(lambda request: httpx.Response(503)))
        ws.use_fallback = True
        r = await ws.search_with_citation("Qual a Selic hoje?")
        assert r["success"] is True
        assert "note" in r


class TestSessionLimit:
    def test_limit_applies_while_running(self):
        # Antes, max_sessions só era aplicado no desligamento do servidor.
        memory = ConversationMemory(max_sessions=3)
        for _ in range(10):
            memory.create_session()
        assert len(memory.sessions) == 3

    def test_least_recently_active_goes_first(self):
        memory = ConversationMemory(max_sessions=3)
        for session_id in ("a", "b", "c"):
            memory.create_session(session_id)
        now = datetime.now(UTC)
        memory.sessions["a"].last_activity = now - timedelta(seconds=1)  # usada agora há pouco
        memory.sessions["b"].last_activity = now - timedelta(minutes=3)
        memory.sessions["c"].last_activity = now - timedelta(minutes=2)

        memory.create_session("d")
        assert set(memory.sessions) == {"a", "c", "d"}

    def test_expired_sessions_are_removed(self):
        memory = ConversationMemory()
        memory.create_session("antiga")
        memory.sessions["antiga"].last_activity = datetime.now(UTC) - timedelta(hours=25)
        memory.create_session("nova")
        assert set(memory.sessions) == {"nova"}


class TestRunScript:
    @pytest.fixture
    def project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[dict[str, Any]]:
        """Projeto falso em tmp_path; devolve os argumentos passados ao uvicorn.run."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "main.py").write_text("")
        (tmp_path / ".env").write_text("HOST=127.0.0.2\nPORT=9999\nLOG_LEVEL=DEBUG\n")
        for var in ("HOST", "PORT", "LOG_LEVEL"):
            # setenv antes do delenv: assim o monkeypatch apaga, no fim do teste,
            # o que o load_dotenv gravar em os.environ.
            monkeypatch.setenv(var, "x")
            monkeypatch.delenv(var)
        monkeypatch.chdir(tmp_path)
        calls: list[dict[str, Any]] = []

        def fake_uvicorn_run(*_args: object, **kwargs: Any) -> None:
            calls.append(kwargs)

        monkeypatch.setattr(uvicorn, "run", fake_uvicorn_run)
        return calls

    def test_reads_env_file(self, project: list[dict[str, Any]]):
        run.main()
        assert project[0]["host"] == "127.0.0.2"
        assert project[0]["port"] == 9999
        assert project[0]["log_level"] == "debug"

    def test_shell_variable_wins_over_env_file(
        self, project: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setenv("PORT", "7000")
        run.main()
        assert project[0]["port"] == 7000


class TestLLMOptional:
    async def test_agent_works_without_api_key(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        agent = PayrollAgent()
        assert not agent.llm.available

        general = await agent.process_query("Olá!")
        assert general["tool_used"] == "general"
        assert "folha de pagamento" in general["response"]

        payroll = await agent.process_query("Quanto a Ana recebeu em maio/2025?")
        assert payroll["tool_used"] == "rag"
        assert format_currency(8418.75) in payroll["response"]


class TestReferenceBase:
    @pytest.mark.parametrize(
        ("question", "expected"),
        [
            ("Como funciona o aviso prévio?", "Lei nº 12.506/2011"),
            ("Qual o prazo para pagar a rescisão?", "CLT, art. 477"),
            ("rescisao sem acento", "CLT, art. 477"),
            ("Qual o salário mínimo?", "art. 7º, IV"),
            ("Qual a alíquota do IRRF?", "Lei nº 7.713/1988"),
            ("Como calcular férias proporcionais na rescisão?", "CLT, arts. 130 e 146"),
            ("Como funciona o 13º salário?", "Lei nº 4.090/1962"),
        ],
    )
    async def test_topic_has_its_own_entry(self, question: str, expected: str):
        ws = WebSearch()
        ws.use_fallback = True
        r = await ws.search_with_citation(question)
        assert expected in r["data"]
        assert "Decreto-Lei nº 5.452/1943" not in r["data"]  # não caiu no texto genérico da CLT
