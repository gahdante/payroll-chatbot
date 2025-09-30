"""
Agente principal do chatbot de folha de pagamento
Implementa lógica de decisão entre RAG, Web Search e conversa geral
"""
import logging
from typing import Dict, Any, Optional

from .llm import LLMConfig
from ..tools.payroll_rag import PayrollRAG
from ..tools.web_search import WebSearch
from .conversation_memory import ConversationMemory

logger = logging.getLogger(__name__)

class PayrollAgent:
    """Agente principal que decide qual ferramenta usar"""
    
    def __init__(self):
        """Inicializa o agente"""
        self.llm = LLMConfig()
        self.rag = PayrollRAG()
        self.web_search = WebSearch()
        self.memory = ConversationMemory()
        
        # Palavras-chave para classificação de consultas
        self.rag_keywords = [
            "funcionário", "funcionários", "salário", "salários", "folha", "pagamento",
            "nome", "cargo", "departamento", "data", "valor", "total", "média", "soma",
            "quem", "quanto", "quando", "onde", "qual", "recebi", "recebeu", "ganhou",
            "líquido", "líquida", "bruto", "bruta", "desconto", "descontos", "inss",
            "irrf", "bônus", "bonus", "trimestre", "semestre", "competência"
        ]
        
        self.web_keywords = [
            "lei", "legislação", "direito", "direitos", "trabalhista", "trabalhistas",
            "clt", "fgts", "inss", "imposto", "tributo", "encargo", "encargos",
            "como calcular", "como funciona", "o que é", "quando", "prazo", "prazo",
            "selic", "taxa", "juros", "férias", "ferias", "13º", "13", "salário"
        ]
        
        self.general_keywords = [
            "olá", "oi", "bom dia", "boa tarde", "boa noite", "obrigado", "obrigada",
            "tchau", "até logo", "como você está", "como está", "ajuda", "help"
        ]
    
    async def process_query(self, message: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Processa consulta do usuário
        
        Args:
            message: Mensagem do usuário
            session_id: ID da sessão (opcional)
            
        Returns:
            Resposta processada
        """
        try:
            # Cria sessão se não existir
            if session_id is None:
                session_id = self.memory.create_session()
            
            # Adiciona mensagem do usuário à memória
            self.memory.add_message(session_id, "user", message)
            
            # Analisa o tipo de consulta
            query_type = await self._analyze_query_type(message)
            
            # Obtém contexto da conversa
            context = self.memory.get_context_summary(session_id)
            
            # Processa consulta baseada no tipo
            if query_type == "rag":
                result = await self._process_rag_query(message, context)
            elif query_type == "web":
                result = await self._process_web_query(message, context)
            else:
                result = await self._process_general_query(message, context)
            
            # Adiciona resposta à memória
            self.memory.add_message(
                session_id, 
                "assistant", 
                result["response"],
                tool_used=result["tool_used"],
                evidence=result.get("evidence")
            )
            
            # Atualiza contexto
            self.memory.update_context_data(session_id, "last_query_type", query_type)
            self.memory.update_context_data(session_id, "last_tool_used", result["tool_used"])
            
            return result
            
        except Exception as e:
            logger.error(f"Erro ao processar consulta: {e}")
            return {
                "response": f"Desculpe, ocorreu um erro ao processar sua consulta: {str(e)}",
                "evidence": None,
                "tool_used": "error"
            }
    
    async def _analyze_query_type(self, message: str) -> str:
        """
        Analisa o tipo de consulta
        
        Args:
            message: Mensagem do usuário
            
        Returns:
            Tipo de consulta (rag, web, general)
        """
        message_lower = message.lower()
        
        # Verifica palavras-chave RAG
        rag_score = sum(1 for keyword in self.rag_keywords if keyword in message_lower)
        
        # Verifica palavras-chave Web
        web_score = sum(1 for keyword in self.web_keywords if keyword in message_lower)
        
        # Verifica palavras-chave gerais
        general_score = sum(1 for keyword in self.general_keywords if keyword in message_lower)
        
        # Decisão baseada em scores
        if rag_score > web_score and rag_score > general_score:
            return "rag"
        elif web_score > rag_score and web_score > general_score:
            return "web"
        elif general_score > 0:
            return "general"
        else:
            # Fallback: se não há palavras-chave claras, usa RAG
            return "rag"
    
    async def _process_rag_query(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa consulta RAG
        
        Args:
            message: Mensagem do usuário
            context: Contexto da conversa
            
        Returns:
            Resposta processada
        """
        try:
            # Executa consulta RAG
            rag_result = await self.rag.query(message)
            
            if not rag_result["success"]:
                return {
                    "response": rag_result["data"],
                    "evidence": None,
                    "tool_used": "rag"
                }
            
            # Enriquece resposta com contexto
            enhanced_response = await self._enhance_response_with_context(
                rag_result["data"], 
                context, 
                rag_result.get("evidence")
            )
            
            return {
                "response": enhanced_response,
                "evidence": rag_result.get("evidence"),
                "tool_used": "rag"
            }
            
        except Exception as e:
            logger.error(f"Erro no RAG: {e}")
            return {
                "response": f"Erro ao consultar dados de folha: {str(e)}",
                "evidence": None,
                "tool_used": "rag"
            }
    
    async def _process_web_query(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa consulta de busca na web
        
        Args:
            message: Mensagem do usuário
            context: Contexto da conversa
            
        Returns:
            Resposta processada
        """
        try:
            # Executa busca na web
            web_result = await self.web_search.search_with_citation(message)
            
            if not web_result["success"]:
                return {
                    "response": "Não foi possível realizar a busca na web. Tente novamente.",
                    "evidence": None,
                    "tool_used": "web"
                }
            
            # Enriquece resposta com contexto
            enhanced_response = await self._enhance_response_with_context(
                web_result["data"], 
                context, 
                web_result.get("evidence")
            )
            
            return {
                "response": enhanced_response,
                "evidence": web_result.get("evidence"),
                "tool_used": "web"
            }
            
        except Exception as e:
            logger.error(f"Erro na busca web: {e}")
            return {
                "response": f"Erro ao buscar informações na web: {str(e)}",
                "evidence": None,
                "tool_used": "web"
            }
    
    async def _process_general_query(self, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa consulta geral
        
        Args:
            message: Mensagem do usuário
            context: Contexto da conversa
            
        Returns:
            Resposta processada
        """
        try:
            # Gera resposta geral usando LLM
            response = await self.llm.generate_response(message, context)
            
            return {
                "response": response,
                "evidence": None,
                "tool_used": "general"
            }
            
        except Exception as e:
            logger.error(f"Erro na resposta geral: {e}")
            return {
                "response": "Desculpe, não consegui processar sua mensagem. Tente novamente.",
                "evidence": None,
                "tool_used": "general"
            }
    
    async def _enhance_response_with_context(self, response: str, context: Dict[str, Any], 
                                           evidence: Optional[Dict[str, Any]]) -> str:
        """
        Enriquece resposta com contexto da conversa
        
        Args:
            response: Resposta original
            context: Contexto da conversa
            evidence: Evidências da resposta
            
        Returns:
            Resposta enriquecida
        """
        try:
            # Adiciona informações de contexto se relevante
            context_info = []
            
            # Menciona funcionários discutidos anteriormente
            if context.get("employee_mentions"):
                employees = ", ".join(context["employee_mentions"])
                context_info.append(f"Vejo que você já consultou informações sobre {employees}.")
            
            # Menciona tópicos discutidos
            if context.get("topics_discussed"):
                topics = ", ".join(context["topics_discussed"])
                context_info.append(f"Anteriormente discutimos sobre {topics}.")
            
            # Menciona competências mencionadas
            if context.get("competencies_mentioned"):
                competencies = ", ".join(context["competencies_mentioned"])
                context_info.append(f"Você já consultou dados das competências {competencies}.")
            
            # Adiciona contexto se houver
            if context_info:
                context_text = " ".join(context_info)
                response = f"{context_text}\n\n{response}"
            
            return response
            
        except Exception as e:
            logger.error(f"Erro ao enriquecer resposta: {e}")
            return response
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas das sessões"""
        return self.memory.get_session_stats()
    
    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """Obtém resumo do contexto da sessão"""
        return self.memory.get_context_summary(session_id)
    
    def cleanup_sessions(self):
        """Limpa sessões expiradas"""
        self.memory.cleanup_old_sessions()
    