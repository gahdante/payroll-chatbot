"""Casos do desafio técnico: valida os valores esperados na camada RAG."""
import pytest

from app.tools.payroll_rag import PayrollRAG
from app.utils.formatting import format_currency, format_date


@pytest.fixture
def rag(payroll_csv: str) -> PayrollRAG:
    return PayrollRAG(payroll_csv)


@pytest.mark.asyncio
async def test_case_1_ana_souza_maio_2025(rag: PayrollRAG):
    """"Quanto recebi (líquido) em maio/2025? (Ana Souza)" -> R$ 8.418,75 / E001, 2025-05."""
    r = await rag.query("Quanto recebi (líquido) em maio/2025? (Ana Souza)")

    assert r["success"] is True
    assert format_currency(8418.75) in r["data"]

    ev = r["evidence"]
    assert ev["employee_ids"] == ["E001"]
    assert ev["competencies"] == ["2025-05"]
    assert len(ev["sources"]) == 1
    assert ev["sources"][0]["employee_id"] == "E001"


@pytest.mark.asyncio
async def test_case_2_ana_souza_q1_total(rag: PayrollRAG):
    """"Total líquido de Ana Souza no 1º trimestre de 2025" -> R$ 23.221,25 / E001, 2025-01..03."""
    r = await rag.query("Qual o total líquido de Ana Souza no 1º trimestre de 2025?")

    assert r["success"] is True
    assert format_currency(23221.25) in r["data"]

    ev = r["evidence"]
    assert ev["employee_ids"] == ["E001"]
    assert set(ev["competencies"]) == {"2025-01", "2025-02", "2025-03"}
    assert ev["total_records"] == 3


@pytest.mark.asyncio
async def test_case_3_bruno_inss_junho(rag: PayrollRAG):
    """"Desconto de INSS do Bruno em jun/2025" -> R$ 660,00 / E002, 2025-06."""
    r = await rag.query("Qual foi o desconto de INSS do Bruno em jun/2025?")

    assert r["success"] is True
    assert "INSS" in r["data"]
    assert format_currency(660.0) in r["data"]
    assert r["evidence"]["employee_ids"] == ["E002"]
    assert r["evidence"]["competencies"] == ["2025-06"]


@pytest.mark.asyncio
async def test_case_4_bruno_abril_pagamento(rag: PayrollRAG):
    """"Quando foi pago abril/2025 do Bruno e qual o líquido" -> 28/04/2025 e R$ 5.756,25."""
    r = await rag.query("Quando foi pago o salário de abril/2025 do Bruno e qual o líquido?")

    assert r["success"] is True
    assert format_currency(5756.25) in r["data"]
    assert format_date("2025-04-28") in r["data"]
    assert r["evidence"]["competencies"] == ["2025-04"]


@pytest.mark.asyncio
async def test_case_5_bruno_maior_bonus(rag: PayrollRAG):
    """"Maior bônus do Bruno e em que mês" -> R$ 1.200,00 em 2025-05 / E002, 2025-05."""
    r = await rag.query("Qual foi o maior bônus do Bruno e em que mês?")

    assert r["success"] is True
    assert format_currency(1200.0) in r["data"]
    assert "2025-05" in r["data"] or "maio" in r["data"].lower()
    assert r["evidence"]["employee_ids"] == ["E002"]
    assert r["evidence"]["competencies"] == ["2025-05"]


@pytest.mark.asyncio
async def test_error_unknown_employee(rag: PayrollRAG):
    r = await rag.query("Qual é o salário do João Inexistente?")
    assert r["success"] is False
    assert "não encontrado" in r["data"].lower()


@pytest.mark.asyncio
async def test_error_unknown_competency(rag: PayrollRAG):
    r = await rag.query("Qual é o salário em dezembro/2025?")
    assert r["success"] is False
    assert "encontrado" in r["data"].lower()


@pytest.mark.asyncio
async def test_error_empty_query(rag: PayrollRAG):
    r = await rag.query("")
    assert r["success"] is False
