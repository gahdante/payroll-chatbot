"""Agente que roteia entre RAG (folha), busca web e conversa geral."""

import logging
import re
from typing import Any

from openai import OpenAIError

from ..tools.payroll_rag import PayrollRAG, QueryParams
from ..tools.web_search import WebSearch
from ..utils.text import contains_any, normalize
from .conversation_memory import ConversationMemory
from .llm import LLMConfig

logger = logging.getLogger(__name__)

# Termos comparados como palavra inteira e sem acento (ver utils.text).
_WEB_TERMS = (
    "lei",
    "leis",
    "legislacao",
    "clt",
    "fgts",
    "selic",
    "ferias",
    "13o",
    "decimo terceiro",
    "rescisao",
    "aviso previo",
    "previdencia",
    "aliquota",
    "aliquotas",
    "teto",
    "salario minimo",
    "como calcular",
    "como funciona",
    "o que e",
    "taxa de juros",
)
_PAYROLL_TERMS = (
    "salario",
    "liquido",
    "bruto",
    "holerite",
    "contracheque",
    "folha",
    "bonus",
    "desconto",
    "descontos",
    "competencia",
    "trimestre",
    "semestre",
    "recebi",
    "recebeu",
    "pagamento",
    "inss",
    "irrf",
    "beneficio",
    "beneficios",
)
# "E em junho?", "Agora o INSS", "Também do Bruno?"
_FOLLOW_UP_START = re.compile(r"^\W*(?:e|agora|tambem|entao)\b")
_FOLLOW_UP_MAX_WORDS = 4

_CONTEXT_KEY = "payroll_params"


class PayrollAgent:
    """Decide qual ferramenta atende cada mensagem e monta a resposta."""

    def __init__(self) -> None:
        self.llm = LLMConfig()
        self.rag = PayrollRAG()
        self.web_search = WebSearch()
        self.memory = ConversationMemory()

    @staticmethod
    def _looks_like_follow_up(message: str) -> bool:
        return bool(_FOLLOW_UP_START.match(normalize(message))) or (
            len(message.split()) <= _FOLLOW_UP_MAX_WORDS
        )

    def _route(self, message: str, has_payroll_context: bool = False) -> tuple[str, bool]:
        """Ferramenta que atende a mensagem e se ela continua a consulta anterior."""
        params: QueryParams = self.rag.parse(message)
        web = contains_any(message, _WEB_TERMS)

        if (
            has_payroll_context
            and not web
            and params.has_signal()
            and self._looks_like_follow_up(message)
        ):
            return "rag", True
        if params.name or params.candidates:
            return "rag", False
        if web:
            return "web", False
        if params.competency or params.period or params.period_error:
            return "rag", False
        if contains_any(message, _PAYROLL_TERMS):
            return "rag", False
        return "general", False

    async def process_query(self, message: str, session_id: str | None = None) -> dict[str, Any]:
        if not session_id or session_id not in self.memory.sessions:
            session_id = self.memory.create_session(session_id)
        # Um "Obrigado!" no meio não quebra o fio da consulta; uma busca web, sim.
        last_tool = self.memory.get_context_data(session_id, "last_tool_used")
        has_payroll_context = self.memory.get_context_data(
            session_id, _CONTEXT_KEY
        ) is not None and last_tool in ("rag", "general")
        self.memory.add_message(session_id, "user", message)

        result: dict[str, Any]
        try:
            kind, follow_up = self._route(message, has_payroll_context)
            if kind == "rag":
                context = (
                    self.memory.get_context_data(session_id, _CONTEXT_KEY) if follow_up else None
                )
                result = await self._handle_rag(message, context)
                if result.get("params"):
                    self.memory.update_context_data(session_id, _CONTEXT_KEY, result["params"])
            elif kind == "web":
                result = await self._handle_web(message)
            else:
                result = await self._handle_general(message, session_id)
        except Exception:  # última barreira: o usuário sempre recebe uma resposta
            logger.exception("Erro ao processar consulta")
            result = {
                "response": "Desculpe, tive um problema para processar sua mensagem. "
                "Pode tentar de novo em instantes?",
                "evidence": None,
                "tool_used": "error",
            }

        self.memory.add_message(
            session_id,
            "assistant",
            result["response"],
            tool_used=result["tool_used"],
            evidence=result.get("evidence"),
        )
        self.memory.update_context_data(session_id, "last_tool_used", result["tool_used"])
        return {
            "response": result["response"],
            "evidence": result.get("evidence"),
            "tool_used": result["tool_used"],
            "session_id": session_id,
        }

    async def _handle_rag(
        self, message: str, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        rag = await self.rag.query(message, context=context)
        return {
            "response": rag["data"],
            "evidence": rag.get("evidence"),
            "tool_used": "rag",
            "params": rag.get("params"),
        }

    async def _handle_web(self, message: str) -> dict[str, Any]:
        web = await self.web_search.search_with_citation(message)
        text = web["data"]
        if web.get("note"):
            text = f"{text}\n\n({web['note']})"
        return {"response": text, "evidence": web.get("evidence"), "tool_used": "web"}

    async def _handle_general(self, message: str, session_id: str) -> dict[str, Any]:
        history = self.memory.get_history_for_llm(session_id)
        try:
            answer = await self.llm.generate_response(message, history=history)
        except OpenAIError as exc:
            logger.warning("Falha no LLM (conversa geral): %s", exc)
            answer = (
                "Posso ajudar com consultas de folha de pagamento (valores, descontos, "
                "competências) e dúvidas de legislação trabalhista. O que você precisa?"
            )
        return {"response": answer, "evidence": None, "tool_used": "general"}

    # helpers usados pela API -------------------------------------------------
    def get_session_stats(self) -> dict[str, Any]:
        return self.memory.get_session_stats()

    def get_context_summary(self, session_id: str) -> dict[str, Any]:
        return self.memory.get_context_summary(session_id)

    def delete_session(self, session_id: str) -> bool:
        return self.memory.delete_session(session_id)

    def cleanup_sessions(self) -> None:
        self.memory.cleanup_old_sessions()
