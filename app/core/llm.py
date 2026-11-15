"""Configuração e chamada do LLM (OpenAI)."""
import logging
import os

from dotenv import load_dotenv
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

load_dotenv()

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """Você é um assistente de folha de pagamento brasileiro, cordial e objetivo.

- Responda em português do Brasil, de forma clara e educada.
- Quem fornece números, datas e fontes é o sistema. Nunca invente valores e
  nunca altere os que receber.
- Valores de folha (salários, descontos, bônus, datas de pagamento): só repita
  os que já apareceram literalmente na conversa. Nunca calcule, estime nem
  deduza um valor novo; peça o funcionário e a competência (ex.: "líquido da
  Ana em junho/2025") para o sistema consultar.
- Formate dinheiro como R$ 1.234,56 e datas como dd/mm/aaaa.
- Se não souber, diga que não sabe e sugira onde a pessoa pode confirmar.
- Seja breve: uma resposta útil, sem enrolação."""


class LLMConfig:
    """Configuração e acesso ao modelo de linguagem."""

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "600"))
        self.request_timeout = float(os.getenv("OPENAI_TIMEOUT", "30"))

        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente")

        self.client = AsyncOpenAI(api_key=self.api_key, timeout=self.request_timeout)

    @staticmethod
    def get_system_prompt() -> str:
        return _SYSTEM_PROMPT

    async def generate_response(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Gera uma resposta conversacional, opcionalmente com histórico recente."""
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": self.get_system_prompt()}
        ]
        for turn in history or []:
            role, content = turn.get("role"), turn.get("content")
            if not content:
                continue
            if role == "user":
                messages.append({"role": "user", "content": content})
            elif role == "assistant":
                messages.append({"role": "assistant", "content": content})
        messages.append({"role": "user", "content": message})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
            )
        except Exception as exc:
            logger.error("Erro ao chamar o LLM: %s", exc)
            raise

        content = response.choices[0].message.content if response.choices else None
        return content.strip() if content else "Desculpe, não consegui gerar uma resposta agora."
