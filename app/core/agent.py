"""
Lógica central: decide qual ferramenta usar (RAG ou Web Search)
"""
import logging
from typing import Dict, Any, Optional
import re

from .llm import LLMConfig
from ..tools.payroll_rag import PayrollRAG
from ..tools.web_search import WebSearch
from ..utils.models import ChatRequest

logger = logging.getLogger(__name__)

class PayrollAgent:
    """Agente principal que decide qual ferramenta usar"""
    
    def __init__(self):
        self.llm = LLMConfig()
        self.rag = PayrollRAG()
        self.web_search = WebSearch()
        
        # Palavras-chave que indicam necessidade de RAG
        self.rag_keywords = [
            "funcionário", "funcionários", "salário", "salários", "folha", "pagamento",
            "nome", "cargo", "departamento", "data", "valor", "total", "média", "soma",
            "quem", "quanto", "quando", "onde", "qual"
        ]
        
        # Palavras-chave que indicam necessidade de web search
        self.web_keywords = [
            "lei", "legislação", "direito", "direitos", "trabalhista", "trabalhistas",
            "clt", "fgts", "inss", "imposto", "tributo", "encargo", "encargos",
            "como calcular", "como funciona", "o que é", "quando", "prazo", "prazo"
        ]
    
    async def process_query(self, message: str) -> Dict[str, Any]:
        """
        Processa a consulta e decide qual ferramenta usar
        
        Args:
            message: Mensagem do usuário
        
        Returns:
            Dicionário com resposta, evidência e ferramenta usada
        """
        try:
            # Analisa a mensagem para decidir a ferramenta
            tool_decision = await self._decide_tool(message)
            
            if tool_decision == "rag":
                return await self._handle_rag_query(message)
            elif tool_decision == "web":
                return await self._handle_web_query(message)
            else:
                return await self._handle_general_query(message)
                
        except Exception as e:
            logger.error(f"Erro ao processar consulta: {e}")
            return {
                "response": "Desculpe, ocorreu um erro ao processar sua consulta. Tente novamente.",
                "evidence": "",
                "tool_used": "error"
            }
    
    async def _decide_tool(self, message: str) -> str:
        """
        Decide qual ferramenta usar baseado na mensagem
        
        Args:
            message: Mensagem do usuário
        
        Returns:
            "rag", "web" ou "general"
        """
        message_lower = message.lower()
        
        # Verifica se há palavras-chave para RAG
        rag_score = sum(1 for keyword in self.rag_keywords if keyword in message_lower)
        
        # Verifica se há palavras-chave para web search
        web_score = sum(1 for keyword in self.web_keywords if keyword in message_lower)
        
        # Verifica padrões específicos
        if re.search(r'\b(funcionário|funcionários)\b', message_lower):
            rag_score += 2
        
        if re.search(r'\b(lei|legislação|direito)\b', message_lower):
            web_score += 2
        
        # Decisão baseada nos scores
        if rag_score > web_score and rag_score > 0:
            return "rag"
        elif web_score > rag_score and web_score > 0:
            return "web"
        else:
            return "general"
    
    async def _handle_rag_query(self, message: str) -> Dict[str, Any]:
        """
        Processa consulta usando RAG
        
        Args:
            message: Mensagem do usuário
        
        Returns:
            Resposta com dados do RAG
        """
        try:
            # Busca dados usando RAG
            rag_results = await self.rag.query(message)
            
            if not rag_results or not rag_results.get("data"):
                return {
                    "response": "Não encontrei dados específicos para sua consulta nos registros de folha de pagamento.",
                    "evidence": "",
                    "tool_used": "rag"
                }
            
            # Formata a resposta usando LLM
            formatted_response = await self._format_rag_response(message, rag_results)
            
            return {
                "response": formatted_response,
                "evidence": rag_results.get("evidence", ""),
                "tool_used": "rag"
            }
            
        except Exception as e:
            logger.error(f"Erro no RAG: {e}")
            return {
                "response": "Erro ao consultar dados de folha de pagamento.",
                "evidence": "",
                "tool_used": "rag"
            }
    
    async def _handle_web_query(self, message: str) -> Dict[str, Any]:
        """
        Processa consulta usando web search
        
        Args:
            message: Mensagem do usuário
        
        Returns:
            Resposta com dados da web
        """
        try:
            # Busca na web
            web_results = await self.web_search.search(message)
            
            if not web_results or not web_results.get("results"):
                return {
                    "response": "Não consegui encontrar informações relevantes na web para sua consulta.",
                    "evidence": "",
                    "tool_used": "web"
                }
            
            # Formata a resposta usando LLM
            formatted_response = await self._format_web_response(message, web_results)
            
            return {
                "response": formatted_response,
                "evidence": web_results.get("evidence", ""),
                "tool_used": "web"
            }
            
        except Exception as e:
            logger.error(f"Erro na web search: {e}")
            return {
                "response": "Erro ao buscar informações na web.",
                "evidence": "",
                "tool_used": "web"
            }
    
    async def _handle_general_query(self, message: str) -> Dict[str, Any]:
        """
        Processa consulta geral usando apenas LLM
        
        Args:
            message: Mensagem do usuário
        
        Returns:
            Resposta geral
        """
        try:
            system_prompt = self.llm.get_system_prompt()
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            response = await self.llm.generate_response(messages)
            
            return {
                "response": response,
                "evidence": "",
                "tool_used": "general"
            }
            
        except Exception as e:
            logger.error(f"Erro na consulta geral: {e}")
            return {
                "response": "Desculpe, não consegui processar sua consulta.",
                "evidence": "",
                "tool_used": "general"
            }
    
    async def _format_rag_response(self, message: str, rag_results: Dict[str, Any]) -> str:
        """
        Formata resposta do RAG usando LLM
        
        Args:
            message: Mensagem original
            rag_results: Resultados do RAG
        
        Returns:
            Resposta formatada
        """
        data = rag_results.get("data", "")
        evidence = rag_results.get("evidence", "")
        
        prompt = f"""
        Com base nos dados de folha de pagamento fornecidos, responda à pergunta do usuário.
        
        Pergunta: {message}
        
        Dados encontrados:
        {data}
        
        Evidência:
        {evidence}
        
        Formate a resposta de forma clara e profissional, incluindo valores em Real (R$) quando aplicável.
        """
        
        messages = [
            {"role": "system", "content": "Você é um especialista em folha de pagamento."},
            {"role": "user", "content": prompt}
        ]
        
        return await self.llm.generate_response(messages)
    
    async def _format_web_response(self, message: str, web_results: Dict[str, Any]) -> str:
        """
        Formata resposta da web search usando LLM
        
        Args:
            message: Mensagem original
            web_results: Resultados da web
        
        Returns:
            Resposta formatada
        """
        results = web_results.get("results", [])
        evidence = web_results.get("evidence", "")
        
        # Prepara contexto dos resultados
        context = "\n".join([
            f"- {result.get('title', '')}: {result.get('snippet', '')}"
            for result in results[:3]  # Limita a 3 resultados
        ])
        
        prompt = f"""
        Com base nas informações encontradas na web, responda à pergunta do usuário sobre legislação trabalhista.
        
        Pergunta: {message}
        
        Informações encontradas:
        {context}
        
        Evidência:
        {evidence}
        
        Forneça uma resposta clara e baseada nas informações encontradas.
        """
        
        messages = [
            {"role": "system", "content": "Você é um especialista em legislação trabalhista brasileira."},
            {"role": "user", "content": prompt}
        ]
        
        return await self.llm.generate_response(messages)
