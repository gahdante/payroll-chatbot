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
            "tchau", "até logo", "como você está", "como está", "ajuda", "help",
            "tudo bem", "beleza", "ok", "certo", "entendi", "perfeito", "legal",
            "bacana", "show", "massa", "top", "massa", "bacana", "show", "massa",
            "como vai", "e aí", "eae", "e aí", "beleza", "tranquilo", "suave",
            "valeu", "brigado", "brigada", "obrigad", "obrigad", "valeu", "brigado",
            "até mais", "até", "tchau", "falou", "flw", "abraço", "abraços",
            "conversa", "falar", "falei", "disse", "comentou", "mencionou",
            "lembra", "lembro", "lembrar", "esqueci", "esqueceu", "esquecer",
            "sabia", "sabia", "sabe", "saber", "conhece", "conhecer", "conhecia",
            "pode", "poder", "consegue", "conseguir", "quero", "quer", "querer",
            "preciso", "precisa", "precisar", "gostaria", "gostaria", "gostar",
            "dúvida", "duvida", "duvido", "duvidar", "pergunta", "perguntar",
            "questão", "questao", "questão", "questao", "problema", "problema",
            "solução", "solucao", "solução", "solucao", "resolver", "resolver",
            "explicar", "explicar", "explicação", "explicacao", "explicação", "explicacao"
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
        
        # Verifica palavras-chave RAG (dados específicos)
        rag_score = sum(1 for keyword in self.rag_keywords if keyword in message_lower)
        
        # Verifica palavras-chave Web (legislação)
        web_score = sum(1 for keyword in self.web_keywords if keyword in message_lower)
        
        # Verifica palavras-chave gerais (conversa)
        general_score = sum(1 for keyword in self.general_keywords if keyword in message_lower)
        
        # Verifica se é uma pergunta direta sobre dados específicos
        if any(name in message_lower for name in ['ana', 'bruno', 'souza', 'lima']):
            return "rag"
        
        # Verifica se é uma pergunta sobre legislação
        if any(word in message_lower for word in ['lei', 'direito', 'trabalhista', 'clt', 'fgts', 'inss', 'como calcular', 'como funciona', 'selic', 'taxa selic', 'juros', 'férias', 'ferias', 'previdência', 'previdencia']):
            return "web"
        
        # Verifica se é uma conversa geral
        if general_score > 0 or len(message.split()) <= 3:
            return "general"
        
        # Se tem palavras-chave RAG, prioriza RAG
        if rag_score > 0:
            return "rag"
        
        # Se tem palavras-chave Web, prioriza Web
        if web_score > 0:
            return "web"
        
        # Fallback: se não consegue classificar, tenta RAG primeiro
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
                # Usa LLM para gerar resposta mais fluida mesmo quando não encontra dados
                rag_data = rag_result["data"]
                llm_response = await self.llm.generate_response(
                    f"O usuário perguntou: '{message}'. "
                    f"Baseado nos dados disponíveis, a resposta é: '{rag_data}'. "
                    f"Transforme isso em uma resposta conversacional e amigável.",
                    context
                )
                return {
                    "response": llm_response,
                    "evidence": None,
                    "tool_used": "rag"
                }
            
            # Usa LLM para tornar a resposta mais fluida e conversacional
            rag_data = rag_result["data"]
            evidence = rag_result.get("evidence", [])
            
            try:
                # Monta contexto para o LLM
                evidence_context = ""
                if evidence:
                    evidence_context = f"Evidências encontradas: {evidence}"
                
                llm_response = await self.llm.generate_response(
                    f"O usuário perguntou: '{message}'. "
                    f"Baseado nos dados da folha de pagamento, encontrei: '{rag_data}'. "
                    f"{evidence_context} "
                    f"Transforme isso em uma resposta conversacional, natural e amigável, "
                    f"como se você fosse um assistente pessoal. Use os dados encontrados mas "
                    f"seja fluido e natural na resposta.",
                    context
                )
                
                return {
                    "response": llm_response,
                    "evidence": evidence,
                    "tool_used": "rag"
                }
            except Exception as llm_error:
                logger.error(f"Erro no LLM: {llm_error}")
                # Resposta fluida sem LLM
                response = f"Perfeito! Encontrei os dados que você pediu: {rag_data} 😊"
                if evidence:
                    response += f" Os dados estão bem detalhados e confiáveis!"
                response += " Precisa de mais alguma informação sobre folha de pagamento?"
                
                return {
                    "response": response,
                    "evidence": evidence,
                    "tool_used": "rag"
                }
            
        except Exception as e:
            logger.error(f"Erro no RAG: {e}")
            return {
                "response": f"Desculpe, não consegui consultar os dados de folha no momento. Tente novamente em alguns instantes.",
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
                # Resposta fluida mesmo sem LLM
                response = f"Ops! Não consegui acessar as informações na web no momento. 😊 Mas não se preocupe! Tente novamente em alguns instantes que vou buscar para você. Ou posso ajudar com outras questões sobre folha de pagamento!"
                return {
                    "response": response,
                    "evidence": None,
                    "tool_used": "web"
                }
            
            # Usa LLM para tornar a resposta mais fluida e conversacional
            web_data = web_result["data"]
            evidence = web_result.get("evidence", [])
            
            try:
                # Monta contexto para o LLM
                evidence_context = ""
                if evidence:
                    evidence_context = f"Fontes encontradas: {evidence}"
                
                llm_response = await self.llm.generate_response(
                    f"O usuário perguntou: '{message}'. "
                    f"Baseado na busca na web, encontrei: '{web_data}'. "
                    f"{evidence_context} "
                    f"Transforme isso em uma resposta conversacional, natural e amigável, "
                    f"como se você fosse um assistente pessoal. Use as informações encontradas "
                    f"mas seja fluido e natural na resposta.",
                    context
                )
                
                return {
                    "response": llm_response,
                    "evidence": evidence,
                    "tool_used": "web"
                }
            except Exception as llm_error:
                logger.error(f"Erro no LLM: {llm_error}")
                # Resposta fluida sem LLM
                response = f"Perfeito! Encontrei informações sobre '{message}':\n\n{web_data} 😊"
                if evidence:
                    response += f"\n\nAs fontes estão bem detalhadas e confiáveis!"
                response += "\n\nPrecisa de mais alguma informação sobre legislação trabalhista?"
                
                return {
                    "response": response,
                    "evidence": evidence,
                    "tool_used": "web"
                }
            
        except Exception as e:
            logger.error(f"Erro na busca web: {e}")
            return {
                "response": f"Desculpe, não consegui buscar informações na web no momento. Tente novamente em alguns instantes.",
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
            # Resposta fluida mesmo sem LLM
            message_lower = message.lower()
            
            # Saudações
            if any(greeting in message_lower for greeting in ['olá', 'oi', 'bom dia', 'boa tarde', 'boa noite', 'e aí', 'eae', 'como vai']):
                response = "Olá! 😊 Estou aqui para ajudar com questões de folha de pagamento. Como posso te auxiliar hoje?"
            
            # Agradecimentos
            elif any(thanks in message_lower for thanks in ['obrigado', 'obrigada', 'valeu', 'obrigad', 'brigado', 'brigada', 'valeu']):
                response = "De nada! 😊 Fico feliz em poder ajudar. Precisa de mais alguma coisa sobre folha de pagamento?"
            
            # Como está
            elif any(how in message_lower for how in ['como você está', 'como está', 'tudo bem', 'beleza', 'tranquilo', 'suave']):
                response = "Estou ótimo, obrigado por perguntar! 😊 Pronto para ajudar com qualquer questão de folha de pagamento. O que você gostaria de saber?"
            
            # Confirmações
            elif any(confirm in message_lower for confirm in ['ok', 'certo', 'entendi', 'perfeito', 'legal', 'bacana', 'show', 'massa', 'top']):
                response = "Perfeito! 😊 Estou aqui para ajudar com qualquer questão de folha de pagamento. O que você gostaria de saber?"
            
            # Despedidas
            elif any(bye in message_lower for bye in ['tchau', 'até logo', 'até mais', 'até', 'falou', 'flw', 'abraço', 'abraços']):
                response = "Até logo! 😊 Foi um prazer ajudar. Volte sempre que precisar de informações sobre folha de pagamento!"
            
            # Perguntas sobre o que pode fazer
            elif any(what in message_lower for what in ['o que você faz', 'o que você pode', 'como você pode', 'o que consegue', 'o que sabe']):
                response = "Posso ajudar com várias coisas! 😊 Consultar dados de folha de pagamento, buscar informações sobre legislação trabalhista, e conversar sobre qualquer assunto relacionado. O que você gostaria de saber?"
            
            # Perguntas sobre ajuda
            elif any(help in message_lower for help in ['ajuda', 'help', 'pode ajudar', 'consegue ajudar', 'preciso de ajuda']):
                response = "Claro que posso ajudar! 😊 Posso consultar dados de folha de pagamento, buscar informações sobre legislação trabalhista, e responder qualquer pergunta relacionada. O que você gostaria de saber?"
            
            # Perguntas sobre dúvidas
            elif any(doubt in message_lower for doubt in ['dúvida', 'duvida', 'duvido', 'pergunta', 'questão', 'questao', 'problema']):
                response = "Estou aqui para esclarecer suas dúvidas! 😊 Posso ajudar com questões de folha de pagamento, legislação trabalhista, ou qualquer outra pergunta. O que você gostaria de saber?"
            
            # Conversas sobre lembrar
            elif any(remember in message_lower for remember in ['lembra', 'lembro', 'lembrar', 'esqueci', 'esqueceu', 'esquecer']):
                response = "Sim, lembro! 😊 Estou aqui para ajudar com qualquer questão de folha de pagamento. O que você gostaria de saber?"
            
            # Conversas sobre saber/conhecer
            elif any(know in message_lower for know in ['sabia', 'sabe', 'saber', 'conhece', 'conhecer', 'conhecia']):
                response = "Sim, sei várias coisas! 😊 Posso ajudar com dados de folha de pagamento, legislação trabalhista, e muito mais. O que você gostaria de saber?"
            
            # Conversas sobre poder/conseguir
            elif any(can in message_lower for can in ['pode', 'poder', 'consegue', 'conseguir', 'quero', 'quer', 'querer', 'preciso', 'precisa', 'precisar', 'gostaria']):
                response = "Claro que posso! 😊 Estou aqui para ajudar com qualquer questão de folha de pagamento. O que você gostaria de saber?"
            
            # Conversas sobre falar/conversar
            elif any(talk in message_lower for talk in ['conversa', 'falar', 'falei', 'disse', 'comentou', 'mencionou']):
                response = "Adoro conversar! 😊 Estou aqui para ajudar com qualquer questão de folha de pagamento. O que você gostaria de saber?"
            
            # Resposta padrão para qualquer outra coisa
            else:
                response = "Entendi! 😊 Posso ajudar com consultas sobre dados de folha de pagamento, informações sobre funcionários, ou questões gerais sobre legislação trabalhista. O que você gostaria de saber?"
            
            return {
                "response": response,
                "evidence": None,
                "tool_used": "general"
            }
    
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Obtém estatísticas das sessões"""
        return self.memory.get_session_stats()
    
    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """Obtém resumo do contexto da sessão"""
        return self.memory.get_context_summary(session_id)
    
    def cleanup_sessions(self):
        """Limpa sessões expiradas"""
        self.memory.cleanup_old_sessions()
    