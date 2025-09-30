"""
Configuração do LLM (modelo, chaves, etc.)
"""
import os
from openai import AsyncOpenAI
from typing import Optional, Dict, Any
import logging
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

logger = logging.getLogger(__name__)

class LLMConfig:
    """Configuração e gerenciamento do LLM"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = 0.1  # Baixa temperatura para respostas mais consistentes
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
        
        self.client = AsyncOpenAI(api_key=self.api_key)
    
    async def generate_response(
        self, 
        message: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Gera resposta do LLM para consultas gerais
        
        Args:
            message: Mensagem do usuário
            context: Contexto da conversa (opcional)
        
        Returns:
            Resposta gerada pelo LLM
        """
        try:
            # Monta mensagens para o chat
            messages = [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": message}
            ]
            
            # Adiciona contexto se disponível
            if context:
                context_text = f"Contexto da conversa: {context}"
                messages.insert(-1, {"role": "system", "content": context_text})
            
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature
            )
            
            return response.choices[0].message.content.strip()
        
        except Exception as e:
            logger.error(f"Erro ao gerar resposta do LLM: {e}")
            raise
    
    
    def get_system_prompt(self) -> str:
        """
        Retorna o prompt do sistema para o chatbot de folha de pagamento
        """
        return """Você é um assistente especializado em folha de pagamento. Sua função é:

1. Responder perguntas sobre dados de folha de pagamento com base em informações fornecidas
2. Buscar informações na web quando necessário para questões gerais sobre legislação trabalhista
3. Sempre fornecer evidências claras das suas respostas
4. Formatar valores monetários em Real (R$) brasileiro
5. Ser preciso e confiável nas informações

Quando usar ferramentas:
- Use RAG (consulta ao CSV) para perguntas sobre dados específicos de funcionários
- Use Web Search para questões gerais sobre legislação, direitos trabalhistas, etc.

Sempre seja claro sobre qual fonte de informação você está usando."""
