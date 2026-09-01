"""Agente que roteia entre RAG (folha), busca web e conversa geral."""
import logging
from typing import Any, Dict, Optional, Set

from .conversation_memory import ConversationMemory
from .llm import LLMConfig
from ..tools.payroll_rag import PayrollRAG
from ..tools.web_search import WebSearch

logger = logging.getLogger(__name__)

_WEB_TERMS = (
    "lei", "legislação", "legislacao", "clt", "fgts", "selic", "férias", "ferias",
    "13º", "13o", "décimo terceiro", "decimo terceiro", "rescisão", "rescisao",
    "aviso prévio", "aviso previo", "previdência", "previdencia", "imposto de renda",
    "como calcular", "como funciona", "o que é", "o que e", "taxa de juros",
)
_PAYROLL_TERMS = (
    "salário", "salario", "líquido", "liquido", "bruto", "holerite", "contracheque",
    "folha", "bônus", "bonus", "desconto", "competência", "competencia", "trimestre",
    "semestre", "recebi", "pagamento", "inss", "irrf",
)
_SMALLTALK = (
    "olá", "ola", "oi", "bom dia", "boa tarde", "boa noite", "obrigado", "obrigada",
    "valeu", "tchau", "até logo", "ate logo", "tudo bem", "como vai", "e aí", "e ai",
)


class PayrollAgent:
    """Decide qual ferramenta atende cada mensagem e monta a resposta."""

    def __init__(self) -> None:
        self.llm = LLMConfig()
        self.rag = PayrollRAG()
        self.web_search = WebSearch()
        self.memory = ConversationMemory()
        self._employee_tokens = self._build_employee_tokens()

    def _build_employee_tokens(self) -> Set[str]:
        tokens: Set[str] = set()
        for full in self.rag.known_names():
            tokens.add(full.lower())
            tokens.update(full.lower().split())
        return tokens

    def _classify(self, message: str) -> str:
        m = message.lower()
        if any(token in m for token in self._employee_tokens):
            return "rag"
        if any(term in m for term in _WEB_TERMS):
            return "web"
        if any(term in m for term in _PAYROLL_TERMS):
            return "rag"
        if len(message.split()) <= 3 or any(term in m for term in _SMALLTALK):
            return "general"
        return "general"

    async def process_query(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        if not session_id or session_id not in self.memory.sessions:
            session_id = self.memory.create_session(session_id)
        self.memory.add_message(session_id, "user", message)

        try:
            kind = self._classify(message)
            if kind == "rag":
                result = await self._handle_rag(message)
            elif kind == "web":
                result = await self._handle_web(message)
            else:
                result = await self._handle_general(message, session_id)
        except Exception as exc:
            logger.error("Erro ao processar consulta: %s", exc)
            result = {
                "response": "Desculpe, tive um problema para processar sua mensagem. "
                            "Pode tentar de novo em instantes?",
                "evidence": None,
                "tool_used": "error",
            }

        self.memory.add_message(
            session_id, "assistant", result["response"],
            tool_used=result["tool_used"], evidence=result.get("evidence"),
        )
        self.memory.update_context_data(session_id, "last_tool_used", result["tool_used"])
        result["session_id"] = session_id
        return result

    async def _handle_rag(self, message: str) -> Dict[str, Any]:
        rag = await self.rag.query(message)
        return {"response": rag["data"], "evidence": rag.get("evidence"), "tool_used": "rag"}

    async def _handle_web(self, message: str) -> Dict[str, Any]:
        web = await self.web_search.search_with_citation(message)
        text = web["data"]
        if web.get("note"):
            text = f"{text}\n\n({web['note']})"
        return {"response": text, "evidence": web.get("evidence"), "tool_used": "web"}

    async def _handle_general(self, message: str, session_id: str) -> Dict[str, Any]:
        history = self.memory.get_history_for_llm(session_id)
        try:
            answer = await self.llm.generate_response(message, history=history)
        except Exception as exc:
            logger.error("Falha no LLM (conversa geral): %s", exc)
            answer = (
                "Posso ajudar com consultas de folha de pagamento (valores, descontos, "
                "competências) e dúvidas de legislação trabalhista. O que você precisa?"
            )
        return {"response": answer, "evidence": None, "tool_used": "general"}

    # helpers usados pela API -------------------------------------------------
    def get_session_stats(self) -> Dict[str, Any]:
        return self.memory.get_session_stats()

    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        return self.memory.get_context_summary(session_id)

    def delete_session(self, session_id: str) -> bool:
        return self.memory.delete_session(session_id)

    def cleanup_sessions(self) -> None:
        self.memory.cleanup_old_sessions()
