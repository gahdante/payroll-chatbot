"""
Modelos Pydantic para Request/Response (incluindo a 'evidência')
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class ChatRequest(BaseModel):
    """Modelo para requisições de chat"""
    message: str = Field(..., description="Mensagem do usuário", min_length=1, max_length=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Qual é o salário médio dos funcionários?"
            }
        }

class ChatResponse(BaseModel):
    """Modelo para respostas de chat"""
    response: str = Field(..., description="Resposta do chatbot")
    evidence: str = Field(default="", description="Evidência da resposta (dados ou fontes)")
    tool_used: str = Field(default="unknown", description="Ferramenta utilizada (rag, web, general)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "O salário médio dos funcionários é R$ 5.500,00",
                "evidence": "Baseado em 150 funcionários",
                "tool_used": "rag"
            }
        }

class EmployeeData(BaseModel):
    """Modelo para dados de funcionário"""
    nome: str = Field(..., description="Nome do funcionário")
    cargo: str = Field(..., description="Cargo do funcionário")
    departamento: str = Field(..., description="Departamento")
    salario: float = Field(..., description="Salário em reais")
    data: str = Field(..., description="Data de referência")
    
    class Config:
        json_schema_extra = {
            "example": {
                "nome": "João Silva",
                "cargo": "Desenvolvedor",
                "departamento": "TI",
                "salario": 7500.00,
                "data": "2024-01-01"
            }
        }

class PayrollStats(BaseModel):
    """Modelo para estatísticas de folha de pagamento"""
    total_funcionarios: int = Field(..., description="Total de funcionários")
    soma_salarios: float = Field(..., description="Soma total dos salários")
    salario_medio: float = Field(..., description="Salário médio")
    maior_salario: float = Field(..., description="Maior salário")
    menor_salario: float = Field(..., description="Menor salário")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_funcionarios": 150,
                "soma_salarios": 825000.00,
                "salario_medio": 5500.00,
                "maior_salario": 15000.00,
                "menor_salario": 2000.00
            }
        }

class WebSearchResult(BaseModel):
    """Modelo para resultados de busca na web"""
    title: str = Field(..., description="Título do resultado")
    link: str = Field(..., description="URL do resultado")
    snippet: str = Field(..., description="Snippet do resultado")
    display_link: str = Field(..., description="Link de exibição")
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Consolidação das Leis do Trabalho (CLT)",
                "link": "https://www.gov.br/trabalho-e-emprego/pt-br",
                "snippet": "A CLT é a principal legislação trabalhista brasileira...",
                "display_link": "gov.br"
            }
        }

class RAGResult(BaseModel):
    """Modelo para resultados do RAG"""
    data: str = Field(..., description="Dados encontrados")
    evidence: str = Field(..., description="Evidência dos dados")
    success: bool = Field(..., description="Indica se a consulta foi bem-sucedida")
    
    class Config:
        json_schema_extra = {
            "example": {
                "data": "João Silva - Desenvolvedor - R$ 7.500,00",
                "evidence": "Baseado em dados de folha de pagamento",
                "success": True
            }
        }

class WebSearchResponse(BaseModel):
    """Modelo para resposta de busca na web"""
    results: List[WebSearchResult] = Field(..., description="Lista de resultados")
    evidence: str = Field(..., description="Evidência da busca")
    success: bool = Field(..., description="Indica se a busca foi bem-sucedida")
    
    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "title": "CLT - Consolidação das Leis do Trabalho",
                        "link": "https://www.gov.br/trabalho-e-emprego/pt-br",
                        "snippet": "A CLT é a principal legislação trabalhista...",
                        "display_link": "gov.br"
                    }
                ],
                "evidence": "Baseado em 3 resultados da web",
                "success": True
            }
        }

class ErrorResponse(BaseModel):
    """Modelo para respostas de erro"""
    error: str = Field(..., description="Mensagem de erro")
    detail: Optional[str] = Field(None, description="Detalhes adicionais do erro")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "Erro interno do servidor",
                "detail": "Falha ao processar consulta"
            }
        }
