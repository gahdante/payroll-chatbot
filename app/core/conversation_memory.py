"""Memória de conversa: contexto entre turnos, por sessão, guardado em memória."""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from ..utils.text import contains_any

logger = logging.getLogger(__name__)

_TOPIC_TERMS = {
    "salário": ("salario", "liquido", "recebi", "recebeu"),
    "descontos": ("desconto", "descontos"),
    "INSS": ("inss",),
    "IRRF": ("irrf", "imposto de renda"),
    "bônus": ("bonus",),
    "trimestre": ("trimestre",),
    "semestre": ("semestre",),
}


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class Message:
    """Uma mensagem da conversa."""

    role: str  # "user" ou "assistant"
    content: str
    timestamp: datetime
    tool_used: str | None = None
    evidence: dict[str, Any] | None = None


@dataclass
class ConversationContext:
    """Estado de uma sessão de conversa."""

    session_id: str
    messages: list[Message] = field(default_factory=list)
    context_data: dict[str, Any] = field(default_factory=dict)
    last_activity: datetime = field(default_factory=_now)
    created_at: datetime = field(default_factory=_now)


class ConversationMemory:
    """Sessões de conversa com limite de quantidade, de tamanho e de inatividade."""

    def __init__(
        self,
        max_sessions: int = 100,
        max_messages_per_session: int = 50,
        session_timeout: timedelta = timedelta(hours=24),
    ):
        self.max_sessions = max_sessions
        self.max_messages_per_session = max_messages_per_session
        self.session_timeout = session_timeout
        self.sessions: dict[str, ConversationContext] = {}

    def create_session(self, session_id: str | None = None) -> str:
        """Cria uma sessão e devolve o ID.

        Antes, remove as sessões expiradas e, se o limite ``max_sessions`` já
        foi atingido, as de atividade mais antiga.
        """
        session_id = session_id or str(uuid.uuid4())
        self._cleanup_expired_sessions()
        self._evict_oldest_sessions(keep=self.max_sessions - 1)

        self.sessions[session_id] = ConversationContext(session_id=session_id)
        logger.info("Nova sessão criada: %s", session_id)
        return session_id

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_used: str | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> bool:
        """Adiciona uma mensagem à sessão. Retorna False se a sessão não existe."""
        session = self.sessions.get(session_id)
        if session is None:
            logger.warning("Sessão não encontrada: %s", session_id)
            return False

        session.messages.append(
            Message(
                role=role,
                content=content,
                timestamp=_now(),
                tool_used=tool_used,
                evidence=evidence,
            )
        )
        session.last_activity = _now()
        if len(session.messages) > self.max_messages_per_session:
            session.messages = session.messages[-self.max_messages_per_session :]
        return True

    def get_history_for_llm(self, session_id: str, max_messages: int = 8) -> list[dict[str, str]]:
        """
        Histórico recente no formato do chat da OpenAI, sem a última mensagem
        (que é a que está sendo processada agora).
        """
        if session_id not in self.sessions:
            return []

        previous = self.sessions[session_id].messages[:-1]
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in previous
            if msg.role in ("user", "assistant")
        ]
        return history[-max_messages:]

    def delete_session(self, session_id: str) -> bool:
        """Remove uma sessão. Retorna True se ela existia."""
        return self.sessions.pop(session_id, None) is not None

    def get_context_summary(self, session_id: str) -> dict[str, Any]:
        """Resumo da sessão: ferramentas usadas, temas, funcionários e competências."""
        session = self.sessions.get(session_id)
        if session is None:
            return {}

        # Funcionários e competências saem das evidências do RAG, não de texto livre.
        tools_used: set[str] = set()
        topics: set[str] = set()
        employees: set[str] = set()
        competencies: set[str] = set()
        for message in session.messages:
            if message.tool_used:
                tools_used.add(message.tool_used)
            sources: list[dict[str, Any]] = (message.evidence or {}).get("sources") or []
            for source in sources:
                if source.get("name"):
                    employees.add(source["name"])
                if source.get("competency"):
                    competencies.add(source["competency"])
            if message.role == "user":
                topics.update(
                    topic
                    for topic, terms in _TOPIC_TERMS.items()
                    if contains_any(message.content, terms)
                )

        return {
            "session_id": session_id,
            "total_messages": len(session.messages),
            "last_activity": session.last_activity.isoformat(),
            "created_at": session.created_at.isoformat(),
            "tools_used": sorted(tools_used),
            "topics_discussed": sorted(topics),
            "employee_mentions": sorted(employees),
            "competencies_mentioned": sorted(competencies),
        }

    def update_context_data(self, session_id: str, key: str, value: Any) -> bool:
        """Grava um dado de contexto na sessão. Retorna False se a sessão não existe."""
        session = self.sessions.get(session_id)
        if session is None:
            return False
        session.context_data[key] = value
        session.last_activity = _now()
        return True

    def get_context_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """Lê um dado de contexto da sessão (``default`` se não houver)."""
        session = self.sessions.get(session_id)
        if session is None:
            return default
        return session.context_data.get(key, default)

    def _cleanup_expired_sessions(self) -> None:
        """Remove as sessões sem atividade há mais de ``session_timeout``."""
        now = _now()
        expired = [
            session_id
            for session_id, session in self.sessions.items()
            if now - session.last_activity > self.session_timeout
        ]
        for session_id in expired:
            del self.sessions[session_id]
            logger.info("Sessão expirada removida: %s", session_id)

    def _evict_oldest_sessions(self, keep: int) -> None:
        """Mantém no máximo ``keep`` sessões, removendo as de atividade mais antiga."""
        excess = len(self.sessions) - max(keep, 0)
        if excess <= 0:
            return
        by_activity = sorted(self.sessions.values(), key=lambda s: s.last_activity)
        for session in by_activity[:excess]:
            del self.sessions[session.session_id]
            logger.info("Sessão antiga removida (limite de sessões): %s", session.session_id)

    def get_session_stats(self) -> dict[str, Any]:
        """Totais de sessões e mensagens; "ativas" = com atividade na última hora."""
        now = _now()
        return {
            "total_sessions": len(self.sessions),
            "total_messages": sum(len(s.messages) for s in self.sessions.values()),
            "active_sessions": sum(
                1 for s in self.sessions.values() if now - s.last_activity < timedelta(hours=1)
            ),
            "max_sessions": self.max_sessions,
            "max_messages_per_session": self.max_messages_per_session,
        }
