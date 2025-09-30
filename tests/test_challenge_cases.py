"""
Testes específicos para os casos do desafio técnico
Implementa validação das respostas esperadas conforme especificação
"""
import pytest
import pandas as pd
import os
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any

# Importa módulos do projeto
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from tools.payroll_rag import PayrollRAG
from utils.formatting import format_currency, format_date
from utils.models import ChatRequest, ChatResponse, Evidence

class TestChallengeCases:
    """Testes para casos específicos do desafio"""
    
    @pytest.fixture
    def payroll_rag(self):
        """Fixture para PayrollRAG com dados do desafio"""
        csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'payroll.csv')
        return PayrollRAG(csv_path)
    
    @pytest.fixture
    def challenge_data(self):
        """Dados específicos do desafio"""
        return {
            "ana_souza": {
                "employee_id": "E001",
                "name": "Ana Souza",
                "may_2025": {
                    "net_pay": 8418.75,
                    "competency": "2025-05",
                    "payment_date": "2025-05-28"
                },
                "q1_2025": {
                    "jan": 7725.0,
                    "feb": 7447.5,
                    "mar": 8048.75,
                    "total": 23221.25
                }
            },
            "bruno_lima": {
                "employee_id": "E002",
                "name": "Bruno Lima",
                "june_2025": {
                    "inss": 660.0,
                    "competency": "2025-06"
                },
                "april_2025": {
                    "net_pay": 5756.25,
                    "payment_date": "2025-04-28",
                    "competency": "2025-04"
                },
                "may_2025": {
                    "bonus": 1200.0,
                    "competency": "2025-05"
                }
            }
        }
    
    @pytest.mark.asyncio
    async def test_case_1_ana_souza_may_2025(self, payroll_rag, challenge_data):
        """
        Caso 1: "Quanto recebi (líquido) em maio/2025? (Ana Souza)"
        Esperado: R$ 8.418,75. Fonte: E001, 2025-05
        """
        query = "Quanto recebi (líquido) em maio/2025? (Ana Souza)"
        
        result = await payroll_rag.query(query)
        
        # Verifica sucesso
        assert result["success"] is True
        
        # Verifica resposta
        expected_amount = challenge_data["ana_souza"]["may_2025"]["net_pay"]
        expected_formatted = format_currency(expected_amount)
        assert expected_formatted in result["data"]
        
        # Verifica evidências
        assert result["evidence"] is not None
        assert result["evidence"]["employee_ids"] == ["E001"]
        assert result["evidence"]["competencies"] == ["2025-05"]
        
        # Verifica fonte específica
        sources = result["evidence"]["sources"]
        assert len(sources) == 1
        assert sources[0]["employee_id"] == "E001"
        assert sources[0]["competency"] == "2025-05"
    
    @pytest.mark.asyncio
    async def test_case_2_ana_souza_q1_2025(self, payroll_rag, challenge_data):
        """
        Caso 2: "Qual o total líquido de Ana Souza no 1º trimestre de 2025?"
        Esperado: R$ 23.221,25 (jan+fev+mar). Fontes: E001, 2025-01..03
        """
        query = "Qual o total líquido de Ana Souza no 1º trimestre de 2025?"
        
        result = await payroll_rag.query(query)
        
        # Verifica sucesso
        assert result["success"] is True
        
        # Verifica resposta
        expected_total = challenge_data["ana_souza"]["q1_2025"]["total"]
        expected_formatted = format_currency(expected_total)
        assert expected_formatted in result["data"]
        
        # Verifica evidências
        assert result["evidence"] is not None
        assert result["evidence"]["employee_ids"] == ["E001"]
        assert set(result["evidence"]["competencies"]) == {"2025-01", "2025-02", "2025-03"}
        
        # Verifica total de registros
        assert result["evidence"]["total_records"] == 3
    
    @pytest.mark.asyncio
    async def test_case_3_bruno_lima_june_2025_inss(self, payroll_rag, challenge_data):
        """
        Caso 3: "Qual foi o desconto de INSS do Bruno em jun/2025?"
        Esperado: R$ 660,00. Fonte: E002, 2025-06
        """
        query = "Qual foi o desconto de INSS do Bruno em jun/2025?"
        
        result = await payroll_rag.query(query)
        
        # Verifica sucesso
        assert result["success"] is True
        
        # Verifica resposta
        expected_inss = challenge_data["bruno_lima"]["june_2025"]["inss"]
        expected_formatted = format_currency(expected_inss)
        assert expected_formatted in result["data"]
        assert "INSS" in result["data"]
        
        # Verifica evidências
        assert result["evidence"] is not None
        assert result["evidence"]["employee_ids"] == ["E002"]
        assert result["evidence"]["competencies"] == ["2025-06"]
    
    @pytest.mark.asyncio
    async def test_case_4_bruno_lima_april_2025_payment(self, payroll_rag, challenge_data):
        """
        Caso 4: "Quando foi pago o salário de abril/2025 do Bruno e qual o líquido?"
        Esperado: 28/04/2025 e R$ 5.756,25. Fonte: E002, 2025-04
        """
        query = "Quando foi pago o salário de abril/2025 do Bruno e qual o líquido?"
        
        result = await payroll_rag.query(query)
        
        # Verifica sucesso
        assert result["success"] is True
        
        # Verifica resposta
        expected_net = challenge_data["bruno_lima"]["april_2025"]["net_pay"]
        expected_formatted = format_currency(expected_net)
        assert expected_formatted in result["data"]
        
        expected_date = challenge_data["bruno_lima"]["april_2025"]["payment_date"]
        expected_date_formatted = format_date(expected_date)
        assert expected_date_formatted in result["data"]
        
        # Verifica evidências
        assert result["evidence"] is not None
        assert result["evidence"]["employee_ids"] == ["E002"]
        assert result["evidence"]["competencies"] == ["2025-04"]
    
    @pytest.mark.asyncio
    async def test_case_5_bruno_lima_highest_bonus(self, payroll_rag, challenge_data):
        """
        Caso 5: "Qual foi o maior bônus do Bruno e em que mês?"
        Esperado: R$ 1.200,00 em 2025-05. Fonte: E002, 2025-05
        """
        query = "Qual foi o maior bônus do Bruno e em que mês?"
        
        result = await payroll_rag.query(query)
        
        # Verifica sucesso
        assert result["success"] is True
        
        # Verifica resposta
        expected_bonus = challenge_data["bruno_lima"]["may_2025"]["bonus"]
        expected_formatted = format_currency(expected_bonus)
        assert expected_formatted in result["data"]
        assert "2025-05" in result["data"] or "maio" in result["data"].lower()
        
        # Verifica evidências
        assert result["evidence"] is not None
        assert result["evidence"]["employee_ids"] == ["E002"]
        assert result["evidence"]["competencies"] == ["2025-05"]
    
    @pytest.mark.asyncio
    async def test_date_parsing_variations(self, payroll_rag):
        """Testa parsing de datas em diferentes formatos"""
        test_cases = [
            ("maio/2025", "2025-05"),
            ("mai/2025", "2025-05"),
            ("2025-05", "2025-05"),
            ("maio 2025", "2025-05"),
            ("em maio/2025", "2025-05"),
            ("no maio/2025", "2025-05"),
        ]
        
        for input_date, expected in test_cases:
            parsed = payroll_rag._parse_date_variations(input_date)
            assert parsed == expected, f"Falha ao parsear '{input_date}': esperado {expected}, obtido {parsed}"
    
    @pytest.mark.asyncio
    async def test_employee_name_extraction(self, payroll_rag):
        """Testa extração de nomes de funcionários"""
        test_cases = [
            ("Qual é o salário do Ana Souza?", "Ana Souza"),
            ("Quanto recebi em maio/2025? (Ana Souza)", "Ana Souza"),
            ("Bruno Lima recebeu quanto?", "Bruno Lima"),
            ("Qual o salário médio?", None),
        ]
        
        for query, expected in test_cases:
            extracted = payroll_rag._extract_employee_name(query)
            assert extracted == expected, f"Falha ao extrair nome de '{query}': esperado {expected}, obtido {extracted}"
    
    @pytest.mark.asyncio
    async def test_competency_extraction(self, payroll_rag):
        """Testa extração de competência"""
        test_cases = [
            ("Quanto recebi em maio/2025?", "2025-05"),
            ("Qual o salário em 2025-05?", "2025-05"),
            ("Bruno em jun/2025", "2025-06"),
            ("Qual o salário médio?", None),
        ]
        
        for query, expected in test_cases:
            extracted = payroll_rag._extract_competency(query)
            assert extracted == expected, f"Falha ao extrair competência de '{query}': esperado {expected}, obtido {extracted}"
    
    def test_currency_formatting(self):
        """Testa formatação de moeda brasileira"""
        test_cases = [
            (8418.75, "R$ 8.418,75"),
            (23221.25, "R$ 23.221,25"),
            (660.0, "R$ 660,00"),
            (5756.25, "R$ 5.756,25"),
            (1200.0, "R$ 1.200,00"),
        ]
        
        for value, expected in test_cases:
            formatted = format_currency(value)
            assert formatted == expected, f"Falha na formatação de {value}: esperado {expected}, obtido {formatted}"
    
    def test_date_formatting(self):
        """Testa formatação de datas brasileiras"""
        test_cases = [
            ("2025-05-28", "28/05/2025"),
            ("2025-04-28", "28/04/2025"),
            ("2025-01-28", "28/01/2025"),
        ]
        
        for input_date, expected in test_cases:
            formatted = format_date(input_date)
            assert formatted == expected, f"Falha na formatação de {input_date}: esperado {expected}, obtido {formatted}"
    
    @pytest.mark.asyncio
    async def test_evidence_structure(self, payroll_rag):
        """Testa estrutura das evidências"""
        query = "Qual é o salário do Ana Souza em maio/2025?"
        
        result = await payroll_rag.query(query)
        
        # Verifica estrutura da evidência
        assert result["evidence"] is not None
        evidence = result["evidence"]
        
        # Verifica campos obrigatórios
        assert "sources" in evidence
        assert "total_records" in evidence
        assert "employee_ids" in evidence
        assert "competencies" in evidence
        
        # Verifica tipos
        assert isinstance(evidence["sources"], list)
        assert isinstance(evidence["total_records"], int)
        assert isinstance(evidence["employee_ids"], list)
        assert isinstance(evidence["competencies"], list)
        
        # Verifica conteúdo das fontes
        sources = evidence["sources"]
        assert len(sources) > 0
        
        for source in sources:
            assert "employee_id" in source
            assert "name" in source
            assert "competency" in source
            assert "payment_date" in source
    
    @pytest.mark.asyncio
    async def test_error_handling(self, payroll_rag):
        """Testa tratamento de erros"""
        # Funcionário inexistente
        result = await payroll_rag.query("Qual é o salário do João Inexistente?")
        assert result["success"] is False
        assert "não encontrado" in result["data"].lower()
        
        # Competência inexistente
        result = await payroll_rag.query("Qual é o salário em dezembro/2025?")
        assert result["success"] is False
        assert "não encontrado" in result["data"].lower()
        
        # Consulta malformada
        result = await payroll_rag.query("")
        assert result["success"] is False
    
    @pytest.mark.asyncio
    async def test_aggregate_queries(self, payroll_rag):
        """Testa consultas agregadas"""
        # Total líquido
        result = await payroll_rag.query("Qual é o total líquido de Ana Souza no 1º trimestre?")
        assert result["success"] is True
        assert "R$ 23.221,25" in result["data"]
        
        # Média
        result = await payroll_rag.query("Qual é o salário médio?")
        assert result["success"] is True
        assert "média" in result["data"].lower()
        
        # Trimestre específico
        result = await payroll_rag.query("Qual é o total do 1º trimestre de 2025?")
        assert result["success"] is True
        assert "trimestre" in result["data"].lower()
    
    @pytest.mark.asyncio
    async def test_deduction_queries(self, payroll_rag):
        """Testa consultas de descontos"""
        # INSS
        result = await payroll_rag.query("Qual foi o desconto de INSS do Bruno em junho/2025?")
        assert result["success"] is True
        assert "R$ 660,00" in result["data"]
        assert "INSS" in result["data"]
        
        # IRRF
        result = await payroll_rag.query("Qual foi o desconto de IRRF do Ana em maio/2025?")
        assert result["success"] is True
        assert "IRRF" in result["data"]
    
    @pytest.mark.asyncio
    async def test_query_type_detection(self, payroll_rag):
        """Testa detecção de tipo de consulta"""
        test_cases = [
            ("Qual é o salário do Ana?", "specific_employee"),
            ("Qual é o salário médio?", "aggregate"),
            ("Qual foi o desconto de INSS?", "deduction"),
            ("Quanto recebi em maio/2025?", "competency"),
            ("Informações gerais", "general"),
        ]
        
        for query, expected in test_cases:
            detected = payroll_rag._analyze_query_type(query)
            assert detected == expected, f"Falha na detecção de '{query}': esperado {expected}, obtido {detected}"

