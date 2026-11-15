"""
Sistema de memória de conversa para o chatbot
Implementa contexto entre turnos da conversa
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

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

@dataclass
class Message:
    """Representa uma mensagem na conversa"""
    role: str  # "user" ou "assistant"
    content: str
    timestamp: datetime
    tool_used: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "tool_used": self.tool_used,
            "evidence": self.evidence
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Message':
        """Cria a partir de dicionário"""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            tool_used=data.get("tool_used"),
            evidence=data.get("evidence")
        )

@dataclass
class ConversationContext:
    """Representa o contexto de uma conversa"""
    session_id: str
    messages: List[Message]
    context_data: Dict[str, Any]
    last_activity: datetime
    created_at: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário"""
        return {
            "session_id": self.session_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "context_data": self.context_data,
            "last_activity": self.last_activity.isoformat(),
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Cria a partir de dicionário"""
        return cls(
            session_id=data["session_id"],
            messages=[Message.from_dict(msg) for msg in data["messages"]],
            context_data=data.get("context_data", {}),
            last_activity=datetime.fromisoformat(data["last_activity"]),
            created_at=datetime.fromisoformat(data["created_at"])
        )

class ConversationMemory:
    """Sistema de memória de conversa"""
    
    def __init__(self, max_sessions: int = 100, max_messages_per_session: int = 50):
        """
        Inicializa o sistema de memória
        
        Args:
            max_sessions: Número máximo de sessões ativas
            max_messages_per_session: Número máximo de mensagens por sessão
        """
        self.max_sessions = max_sessions
        self.max_messages_per_session = max_messages_per_session
        self.sessions: Dict[str, ConversationContext] = {}
        self.session_timeout = timedelta(hours=24)  # 24 horas de inatividade
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """
        Cria uma nova sessão de conversa
        
        Args:
            session_id: ID da sessão (opcional)
            
        Returns:
            ID da sessão criada
        """
        if session_id is None:
            session_id = str(uuid.uuid4())
        
        # Remove sessões expiradas
        self._cleanup_expired_sessions()
        
        # Cria nova sessão
        context = ConversationContext(
            session_id=session_id,
            messages=[],
            context_data={},
            last_activity=datetime.now(timezone.utc),
            created_at=datetime.now(timezone.utc)
        )
        
        self.sessions[session_id] = context
        logger.info(f"Nova sessão criada: {session_id}")
        
        return session_id
    
    def add_message(self, session_id: str, role: str, content: str, 
                   tool_used: Optional[str] = None, evidence: Optional[Dict[str, Any]] = None) -> bool:
        """
        Adiciona mensagem à sessão
        
        Args:
            session_id: ID da sessão
            role: Papel da mensagem ("user" ou "assistant")
            content: Conteúdo da mensagem
            tool_used: Ferramenta utilizada
            evidence: Evidências da resposta
            
        Returns:
            True se adicionada com sucesso
        """
        if session_id not in self.sessions:
            logger.warning(f"Sessão não encontrada: {session_id}")
            return False
        
        # Cria mensagem
        message = Message(
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc),
            tool_used=tool_used,
            evidence=evidence
        )
        
        # Adiciona à sessão
        session = self.sessions[session_id]
        session.messages.append(message)
        session.last_activity = datetime.now(timezone.utc)
        
        # Limita número de mensagens
        if len(session.messages) > self.max_messages_per_session:
            session.messages = session.messages[-self.max_messages_per_session:]
        
        logger.debug(f"Mensagem adicionada à sessão {session_id}")
        return True
    
    def get_conversation_history(self, session_id: str, max_messages: int = 10) -> List[Message]:
        """
        Obtém histórico da conversa
        
        Args:
            session_id: ID da sessão
            max_messages: Número máximo de mensagens a retornar
            
        Returns:
            Lista de mensagens
        """
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        messages = session.messages[-max_messages:] if max_messages > 0 else session.messages

        return messages

    def get_history_for_llm(self, session_id: str, max_messages: int = 8) -> List[Dict[str, str]]:
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

    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """
        Obtém resumo do contexto da conversa
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Resumo do contexto
        """
        if session_id not in self.sessions:
            return {}
        
        session = self.sessions[session_id]
        
        # Analisa mensagens para extrair contexto
        context_summary = {
            "session_id": session_id,
            "total_messages": len(session.messages),
            "last_activity": session.last_activity.isoformat(),
            "created_at": session.created_at.isoformat(),
            "tools_used": [],
            "topics_discussed": [],
            "employee_mentions": [],
            "competencies_mentioned": []
        }
        
        # Funcionários e competências saem das evidências do RAG, não de texto livre.
        tools_used, topics, employees, competencies = set(), set(), set(), set()
        for message in session.messages:
            if message.tool_used:
                tools_used.add(message.tool_used)
            for source in (message.evidence or {}).get("sources") or []:
                if source.get("name"):
                    employees.add(source["name"])
                if source.get("competency"):
                    competencies.add(source["competency"])
            if message.role == "user":
                topics.update(
                    topic for topic, terms in _TOPIC_TERMS.items()
                    if contains_any(message.content, terms)
                )

        context_summary["tools_used"] = sorted(tools_used)
        context_summary["topics_discussed"] = sorted(topics)
        context_summary["employee_mentions"] = sorted(employees)
        context_summary["competencies_mentioned"] = sorted(competencies)

        return context_summary
    
    def update_context_data(self, session_id: str, key: str, value: Any) -> bool:
        """
        Atualiza dados de contexto da sessão
        
        Args:
            session_id: ID da sessão
            key: Chave do contexto
            value: Valor do contexto
            
        Returns:
            True se atualizado com sucesso
        """
        if session_id not in self.sessions:
            return False
        
        session = self.sessions[session_id]
        session.context_data[key] = value
        session.last_activity = datetime.now(timezone.utc)
        
        return True
    
    def get_context_data(self, session_id: str, key: str, default: Any = None) -> Any:
        """
        Obtém dados de contexto da sessão
        
        Args:
            session_id: ID da sessão
            key: Chave do contexto
            default: Valor padrão
            
        Returns:
            Valor do contexto ou padrão
        """
        if session_id not in self.sessions:
            return default
        
        session = self.sessions[session_id]
        return session.context_data.get(key, default)
    
    def _cleanup_expired_sessions(self):
        """Remove sessões expiradas"""
        now = datetime.now(timezone.utc)
        expired_sessions = []
        
        for session_id, session in self.sessions.items():
            if now - session.last_activity > self.session_timeout:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.sessions[session_id]
            logger.info(f"Sessão expirada removida: {session_id}")
    
    def cleanup_old_sessions(self):
        """Remove sessões mais antigas se exceder o limite"""
        if len(self.sessions) <= self.max_sessions:
            return
        
        # Ordena por última atividade
        sorted_sessions = sorted(
            self.sessions.items(),
            key=lambda x: x[1].last_activity
        )
        
        # Remove as mais antigas
        sessions_to_remove = len(self.sessions) - self.max_sessions
        for i in range(sessions_to_remove):
            session_id = sorted_sessions[i][0]
            del self.sessions[session_id]
            logger.info(f"Sessão antiga removida: {session_id}")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas das sessões"""
        total_sessions = len(self.sessions)
        total_messages = sum(len(session.messages) for session in self.sessions.values())
        
        # Sessões ativas (últimas 1 hora)
        now = datetime.now(timezone.utc)
        active_sessions = sum(
            1 for session in self.sessions.values()
            if now - session.last_activity < timedelta(hours=1)
        )
        
        return {
            "total_sessions": total_sessions,
            "total_messages": total_messages,
            "active_sessions": active_sessions,
            "max_sessions": self.max_sessions,
            "max_messages_per_session": self.max_messages_per_session
        }
    
    def export_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Exporta dados da sessão
        
        Args:
            session_id: ID da sessão
            
        Returns:
            Dados da sessão ou None se não encontrada
        """
        if session_id not in self.sessions:
            return None
        
        session = self.sessions[session_id]
        return session.to_dict()
    
    def import_session(self, session_data: Dict[str, Any]) -> bool:
        """
        Importa dados da sessão
        
        Args:
            session_data: Dados da sessão
            
        Returns:
            True se importado com sucesso
        """
        try:
            session = ConversationContext.from_dict(session_data)
            self.sessions[session.session_id] = session
            logger.info(f"Sessão importada: {session.session_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao importar sessão: {e}")
            return False
