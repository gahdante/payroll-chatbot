"""
Fixtures para testes
"""
import pytest
import pandas as pd
import os
from typing import Dict, Any

@pytest.fixture
def sample_payroll_data():
    """Dados de exemplo para testes"""
    return pd.DataFrame({
        'nome': ['João Silva', 'Maria Santos', 'Pedro Costa', 'Ana Oliveira'],
        'cargo': ['Desenvolvedor', 'Analista', 'Gerente', 'Designer'],
        'departamento': ['TI', 'TI', 'TI', 'Design'],
        'salario': [7500.00, 5500.00, 12000.00, 4500.00],
        'data': ['2024-01-01', '2024-01-01', '2024-01-01', '2024-01-01']
    })

@pytest.fixture
def sample_web_results():
    """Resultados de exemplo para testes de web search"""
    return {
        'results': [
            {
                'title': 'CLT - Consolidação das Leis do Trabalho',
                'link': 'https://www.gov.br/trabalho-e-emprego/pt-br',
                'snippet': 'A CLT é a principal legislação trabalhista brasileira...',
                'display_link': 'gov.br'
            },
            {
                'title': 'Direitos Trabalhistas',
                'link': 'https://www.trabalhador.gov.br/direitos',
                'snippet': 'Informações sobre direitos trabalhistas...',
                'display_link': 'trabalhador.gov.br'
            }
        ],
        'evidence': 'Baseado em 2 resultados da web',
        'success': True
    }

@pytest.fixture
def sample_rag_results():
    """Resultados de exemplo para testes de RAG"""
    return {
        'data': 'João Silva - Desenvolvedor - R$ 7.500,00',
        'evidence': 'Baseado em dados de folha de pagamento',
        'success': True
    }

@pytest.fixture
def mock_llm_config():
    """Configuração mock do LLM"""
    return {
        'api_key': 'test_key',
        'model': 'gpt-4o-mini',
        'temperature': 0.1
    }

@pytest.fixture
def sample_queries():
    """Consultas de exemplo para testes"""
    return {
        'rag_queries': [
            'Qual é o salário do João Silva?',
            'Quantos funcionários temos?',
            'Qual é o salário médio?',
            'Quem trabalha no departamento de TI?'
        ],
        'web_queries': [
            'Como calcular férias proporcionais?',
            'Qual é o valor do FGTS?',
            'Como funciona o 13º salário?',
            'Quais são os direitos trabalhistas?'
        ],
        'general_queries': [
            'Olá, como você está?',
            'Obrigado pela ajuda',
            'Preciso de mais informações'
        ]
    }

@pytest.fixture
def expected_responses():
    """Respostas esperadas para testes"""
    return {
        'rag_response': {
            'response': 'O salário do João Silva é R$ 7.500,00',
            'evidence': 'Baseado em dados de folha de pagamento',
            'tool_used': 'rag'
        },
        'web_response': {
            'response': 'As férias proporcionais são calculadas...',
            'evidence': 'Baseado em 3 resultados da web',
            'tool_used': 'web'
        },
        'general_response': {
            'response': 'Olá! Como posso ajudá-lo?',
            'evidence': '',
            'tool_used': 'general'
        }
    }

@pytest.fixture
def test_csv_path():
    """Caminho para arquivo CSV de teste"""
    return "data/test_payroll.csv"

@pytest.fixture
def create_test_csv(test_csv_path, sample_payroll_data):
    """Cria arquivo CSV de teste"""
    # Cria diretório se não existir
    os.makedirs(os.path.dirname(test_csv_path), exist_ok=True)
    
    # Salva dados de exemplo
    sample_payroll_data.to_csv(test_csv_path, index=False)
    
    yield test_csv_path
    
    # Limpa arquivo após teste
    if os.path.exists(test_csv_path):
        os.remove(test_csv_path)

@pytest.fixture
def mock_environment():
    """Variáveis de ambiente mock"""
    return {
        'OPENAI_API_KEY': 'test_openai_key',
        'OPENAI_MODEL': 'gpt-4o-mini',
        'GOOGLE_API_KEY': 'test_google_key',
        'GOOGLE_SEARCH_ENGINE_ID': 'test_search_engine_id',
        'DEBUG': 'True',
        'LOG_LEVEL': 'INFO'
    }
