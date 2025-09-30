"""
Modelos Pydantic para o sistema de folha de pagamento
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime

class ChatRequest(BaseModel):
    """Modelo para requisição de chat"""
    message: str = Field(..., min_length=1, max_length=1000, description="Mensagem do usuário")
    
    @validator('message')
    def validate_message(cls, v):
        if not v or not v.strip():
            raise ValueError('Mensagem não pode estar vazia')
        return v.strip()

class ChatResponse(BaseModel):
    """Modelo para resposta do chat"""
    response: str = Field(..., description="Resposta do chatbot")
    evidence: Optional[List[Dict[str, Any]]] = Field(None, description="Evidências da resposta")
    tool_used: str = Field(..., description="Ferramenta utilizada (rag, web, general)")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class EvidenceSource(BaseModel):
    """Modelo para fonte de evidência"""
    employee_id: str = Field(..., description="ID do funcionário")
    name: str = Field(..., description="Nome do funcionário")
    competency: str = Field(..., description="Competência")
    payment_date: str = Field(..., description="Data de pagamento")
    net_pay: Optional[float] = Field(None, description="Salário líquido")
    base_salary: Optional[float] = Field(None, description="Salário base")
    bonus: Optional[float] = Field(None, description="Bônus")
    deductions_inss: Optional[float] = Field(None, description="Desconto INSS")
    deductions_irrf: Optional[float] = Field(None, description="Desconto IRRF")

class Evidence(BaseModel):
    """Modelo para evidências da resposta"""
    sources: List[EvidenceSource] = Field(..., description="Fontes de evidência")
    total_records: int = Field(..., ge=0, description="Total de registros")
    employee_ids: List[str] = Field(..., description="IDs dos funcionários")
    competencies: List[str] = Field(..., description="Competências")
    query_type: str = Field(..., description="Tipo de consulta")
    confidence: float = Field(..., ge=0, le=1, description="Confiança na resposta")

class HealthCheck(BaseModel):
    """Modelo para health check"""
    status: str = Field(..., description="Status do serviço")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp")
    version: str = Field(..., description="Versão do serviço")
    uptime: Optional[float] = Field(None, description="Tempo de atividade em segundos")
    dependencies: Optional[Dict[str, str]] = Field(None, description="Status das dependências")