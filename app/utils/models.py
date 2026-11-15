"""Modelos Pydantic (v2) da API."""
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    """Requisição do endpoint de chat."""

    message: str = Field(..., min_length=1, max_length=1000, description="Mensagem do usuário")
    session_id: Optional[str] = Field(default=None, description="ID de sessão para manter o contexto")

    @field_validator("message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Mensagem não pode estar vazia")
        return value


class ChatResponse(BaseModel):
    """Resposta do endpoint de chat."""

    response: str = Field(..., description="Resposta do chatbot")
    tool_used: str = Field(..., description="Ferramenta usada: rag, web, general ou error")
    evidence: Optional[Dict[str, Any]] = Field(default=None, description="Fontes/evidências da resposta")
    session_id: Optional[str] = Field(default=None, description="ID da sessão desta conversa")


class HealthCheck(BaseModel):
    """Status do serviço."""

    status: str = Field(..., description="healthy ou degraded")
    version: str = Field(..., description="Versão do serviço")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    dependencies: Dict[str, str] = Field(default_factory=dict)
