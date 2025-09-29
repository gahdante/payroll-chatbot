"""
Testes para RAG (simples, agregado, formatação)
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
from tools.web_search import WebSearch
from core.agent import PayrollAgent
from utils.formatting import format_currency, parse_currency, format_date
from utils.models import ChatRequest, ChatResponse

class TestPayrollRAG:
    """Testes para o sistema RAG"""
    
    def test_rag_initialization(self, sample_payroll_data, create_test_csv):
        """Testa inicialização do RAG"""
        rag = PayrollRAG(create_test_csv)
        assert rag.df is not None
        assert len(rag.df) == 4
    
    def test_analyze_query_type(self, sample_payroll_data, create_test_csv):
        """Testa análise do tipo de consulta"""
        rag = PayrollRAG(create_test_csv)
        
        # Testa consulta por funcionário específico
        assert rag._analyze_query_type("Qual é o salário do João Silva?") == "specific_employee"
        
        # Testa consulta agregada
        assert rag._analyze_query_type("Qual é o salário médio?") == "aggregate"
        
        # Testa consulta com filtros
        assert rag._analyze_query_type("Quem trabalha no departamento de TI?") == "filter"
        
        # Testa consulta geral
        assert rag._analyze_query_type("Olá, como você está?") == "general"
    
    def test_extract_employee_name(self, sample_payroll_data, create_test_csv):
        """Testa extração de nome do funcionário"""
        rag = PayrollRAG(create_test_csv)
        
        # Testa extração de nome
        name = rag._extract_employee_name("Qual é o salário do funcionário João Silva?")
        assert name == "João"
        
        # Testa quando não há nome
        name = rag._extract_employee_name("Qual é o salário médio?")
        assert name is None
    
    def test_format_employee_data(self, sample_payroll_data, create_test_csv):
        """Testa formatação de dados do funcionário"""
        rag = PayrollRAG(create_test_csv)
        
        # Testa formatação
        formatted = rag._format_employee_data(sample_payroll_data.head(1))
        assert "João Silva" in formatted
        assert "Desenvolvedor" in formatted
        assert "R$ 7.500,00" in formatted
    
    def test_format_filtered_data(self, sample_payroll_data, create_test_csv):
        """Testa formatação de dados filtrados"""
        rag = PayrollRAG(create_test_csv)
        
        # Testa formatação
        formatted = rag._format_filtered_data(sample_payroll_data.head(2))
        assert "João Silva" in formatted
        assert "Maria Santos" in formatted
    
    @pytest.mark.asyncio
    async def test_query_specific_employee(self, sample_payroll_data, create_test_csv):
        """Testa consulta por funcionário específico"""
        rag = PayrollRAG(create_test_csv)
        
        # Mock da extração de nome
        with patch.object(rag, '_extract_employee_name', return_value="João"):
            result = await rag._query_specific_employee("Qual é o salário do João?")
            
            assert result["success"] is True
            assert "João Silva" in result["data"]
            assert "R$ 7.500,00" in result["data"]
    
    @pytest.mark.asyncio
    async def test_query_aggregate(self, sample_payroll_data, create_test_csv):
        """Testa consulta agregada"""
        rag = PayrollRAG(create_test_csv)
        
        result = await rag._query_aggregate("Qual é o salário médio?")
        
        assert result["success"] is True
        assert "Total de funcionários: 4" in result["data"]
        assert "R$ 7.375,00" in result["data"]  # Média dos salários
    
    @pytest.mark.asyncio
    async def test_query_filter(self, sample_payroll_data, create_test_csv):
        """Testa consulta com filtros"""
        rag = PayrollRAG(create_test_csv)
        
        # Mock da extração de departamento
        with patch.object(rag, '_extract_department', return_value="TI"):
            result = await rag._query_filter("Quem trabalha no departamento de TI?")
            
            assert result["success"] is True
            assert "João Silva" in result["data"]
            assert "Maria Santos" in result["data"]
    
    @pytest.mark.asyncio
    async def test_query_general(self, sample_payroll_data, create_test_csv):
        """Testa consulta geral"""
        rag = PayrollRAG(create_test_csv)
        
        result = await rag._query_general("Informações gerais")
        
        assert result["success"] is True
        assert "Total de funcionários: 4" in result["data"]
        assert "Colunas disponíveis" in result["data"]

class TestWebSearch:
    """Testes para o sistema de busca na web"""
    
    def test_web_search_initialization(self):
        """Testa inicialização do WebSearch"""
        search = WebSearch()
        assert search.base_url == "https://www.googleapis.com/customsearch/v1"
    
    def test_enhance_query_for_workplace(self):
        """Testa enriquecimento de consulta"""
        search = WebSearch()
        
        # Testa enriquecimento
        enhanced = search._enhance_query_for_workplace("Como calcular férias?")
        assert "legislação trabalhista" in enhanced
        
        # Testa quando já tem termos relevantes
        enhanced = search._enhance_query_for_workplace("CLT direitos trabalhistas")
        assert "legislação trabalhista" in enhanced
    
    def test_filter_workplace_results(self, sample_web_results):
        """Testa filtragem de resultados"""
        search = WebSearch()
        
        # Testa filtragem
        filtered = search._filter_workplace_results(sample_web_results["results"])
        assert len(filtered) > 0
        assert all("trabalho" in result["title"].lower() or "trabalhista" in result["title"].lower() 
                  for result in filtered)
    
    @pytest.mark.asyncio
    async def test_fallback_search(self):
        """Testa busca de fallback"""
        search = WebSearch()
        search.use_fallback = True
        
        result = await search.search("Como calcular férias?")
        
        assert result["success"] is True
        assert len(result["results"]) > 0
        assert "CLT" in result["results"][0]["title"]

class TestFormatting:
    """Testes para funções de formatação"""
    
    def test_format_currency(self):
        """Testa formatação de moeda"""
        # Testa valores numéricos
        assert format_currency(1500.50) == "R$ 1.500,50"
        assert format_currency(1000000) == "R$ 1.000.000,00"
        
        # Testa strings
        assert format_currency("1500.50") == "R$ 1.500,50"
        assert format_currency("R$ 1.500,50") == "R$ 1.500,50"
        
        # Testa valores inválidos
        assert format_currency("invalid") == "R$ 0,00"
    
    def test_parse_currency(self):
        """Testa parsing de moeda"""
        # Testa formatos válidos
        assert parse_currency("R$ 1.500,50") == 1500.50
        assert parse_currency("R$ 1.000.000,00") == 1000000.00
        assert parse_currency("1500.50") == 1500.50
        
        # Testa valores inválidos
        assert parse_currency("invalid") is None
        assert parse_currency("") is None
    
    def test_format_date(self):
        """Testa formatação de data"""
        # Testa string
        assert format_date("2024-01-01") == "01/01/2024"
        
        # Testa datetime
        from datetime import datetime
        date_obj = datetime(2024, 1, 1)
        assert format_date(date_obj) == "01/01/2024"
        
        # Testa formato inválido
        assert format_date("invalid") == "Data inválida"
    
    def test_parse_date(self):
        """Testa parsing de data"""
        # Testa formatos válidos
        assert parse_date("01/01/2024") == "2024-01-01"
        assert parse_date("01-01-2024") == "2024-01-01"
        assert parse_date("2024-01-01") == "2024-01-01"
        
        # Testa formato inválido
        assert parse_date("invalid") is None
    
    def test_validate_date_range(self):
        """Testa validação de intervalo de datas"""
        # Testa intervalo válido
        assert validate_date_range("2024-01-01", "2024-12-31") is True
        
        # Testa intervalo inválido
        assert validate_date_range("2024-12-31", "2024-01-01") is False
        
        # Testa datas inválidas
        assert validate_date_range("invalid", "2024-01-01") is False
    
    def test_format_percentage(self):
        """Testa formatação de porcentagem"""
        assert format_percentage(15.5) == "15.50%"
        assert format_percentage(100) == "100.00%"
        assert format_percentage("invalid") == "0,00%"
    
    def test_format_number(self):
        """Testa formatação de números"""
        assert format_number(1500.50) == "1.500,50"
        assert format_number(1000000) == "1.000.000,00"
        assert format_number("invalid") == "0,00"
    
    def test_clean_text(self):
        """Testa limpeza de texto"""
        assert clean_text("  João   Silva  ") == "João Silva"
        assert clean_text("João@Silva#123") == "João Silva 123"
        assert clean_text("") == ""
        assert clean_text(None) == ""
    
    def test_extract_numbers(self):
        """Testa extração de números"""
        assert extract_numbers("R$ 1.500,50") == [1.0, 500.0, 50.0]
        assert extract_numbers("Salário: 7500.00") == [7500.0]
        assert extract_numbers("Sem números") == []
    
    def test_format_employee_name(self):
        """Testa formatação de nome do funcionário"""
        assert format_employee_name("joão silva") == "João Silva"
        assert format_employee_name("MARIA SANTOS") == "Maria Santos"
        assert format_employee_name("") == ""
        assert format_employee_name(None) == ""
    
    def test_format_department_name(self):
        """Testa formatação de nome do departamento"""
        assert format_department_name("ti") == "TI"
        assert format_department_name("recursos humanos") == "RECURSOS HUMANOS"
        assert format_department_name("") == ""
        assert format_department_name(None) == ""
    
    def test_format_position_name(self):
        """Testa formatação de nome do cargo"""
        assert format_position_name("desenvolvedor") == "Desenvolvedor"
        assert format_position_name("ANALISTA DE SISTEMAS") == "Analista De Sistemas"
        assert format_position_name("") == ""
        assert format_position_name(None) == ""

class TestModels:
    """Testes para modelos Pydantic"""
    
    def test_chat_request(self):
        """Testa modelo ChatRequest"""
        request = ChatRequest(message="Qual é o salário médio?")
        assert request.message == "Qual é o salário médio?"
        
        # Testa validação
        with pytest.raises(ValueError):
            ChatRequest(message="")  # Mensagem vazia
    
    def test_chat_response(self):
        """Testa modelo ChatResponse"""
        response = ChatResponse(
            response="O salário médio é R$ 5.500,00",
            evidence="Baseado em 150 funcionários",
            tool_used="rag"
        )
        assert response.response == "O salário médio é R$ 5.500,00"
        assert response.evidence == "Baseado em 150 funcionários"
        assert response.tool_used == "rag"
    
    def test_employee_data(self):
        """Testa modelo EmployeeData"""
        employee = EmployeeData(
            nome="João Silva",
            cargo="Desenvolvedor",
            departamento="TI",
            salario=7500.00,
            data="2024-01-01"
        )
        assert employee.nome == "João Silva"
        assert employee.salario == 7500.00
    
    def test_payroll_stats(self):
        """Testa modelo PayrollStats"""
        stats = PayrollStats(
            total_funcionarios=150,
            soma_salarios=825000.00,
            salario_medio=5500.00,
            maior_salario=15000.00,
            menor_salario=2000.00
        )
        assert stats.total_funcionarios == 150
        assert stats.salario_medio == 5500.00

class TestIntegration:
    """Testes de integração"""
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Testa inicialização do agente"""
        with patch('core.llm.LLMConfig') as mock_llm:
            mock_llm.return_value = Mock()
            
            agent = PayrollAgent()
            assert agent.llm is not None
            assert agent.rag is not None
            assert agent.web_search is not None
    
    @pytest.mark.asyncio
    async def test_agent_tool_decision(self):
        """Testa decisão de ferramenta do agente"""
        with patch('core.llm.LLMConfig') as mock_llm:
            mock_llm.return_value = Mock()
            
            agent = PayrollAgent()
            
            # Testa decisão para RAG
            decision = await agent._decide_tool("Qual é o salário do João?")
            assert decision == "rag"
            
            # Testa decisão para web
            decision = await agent._decide_tool("Como calcular férias?")
            assert decision == "web"
            
            # Testa decisão geral
            decision = await agent._decide_tool("Olá, como você está?")
            assert decision == "general"
    
    @pytest.mark.asyncio
    async def test_agent_process_query(self):
        """Testa processamento de consulta pelo agente"""
        with patch('core.llm.LLMConfig') as mock_llm, \
             patch('tools.payroll_rag.PayrollRAG') as mock_rag, \
             patch('tools.web_search.WebSearch') as mock_web:
            
            # Mock das ferramentas
            mock_llm.return_value = Mock()
            mock_rag.return_value = Mock()
            mock_web.return_value = Mock()
            
            # Mock da resposta do RAG
            mock_rag.return_value.query = AsyncMock(return_value={
                "data": "João Silva - R$ 7.500,00",
                "evidence": "Baseado em dados de folha",
                "success": True
            })
            
            # Mock da resposta do LLM
            mock_llm.return_value.generate_response = AsyncMock(return_value="O salário do João é R$ 7.500,00")
            
            agent = PayrollAgent()
            result = await agent.process_query("Qual é o salário do João?")
            
            assert result["response"] == "O salário do João é R$ 7.500,00"
            assert result["tool_used"] == "rag"
