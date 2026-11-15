"""Configuração e chamada do LLM (OpenAI)."""

import logging
import os

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

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


class LLMUnavailableError(RuntimeError):
    """O LLM não está configurado (falta OPENAI_API_KEY)."""


class LLMConfig:
    """Configuração e acesso ao modelo de linguagem.

    Sem ``OPENAI_API_KEY`` o LLM fica indisponível, mas o resto do chatbot
    (consultas de folha e busca web) não depende dele e continua funcionando.
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY") or None
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2"))
        self.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", "600"))
        self.request_timeout = float(os.getenv("OPENAI_TIMEOUT", "30"))

        self.client: AsyncOpenAI | None = None
        if self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key, timeout=self.request_timeout)
        else:
            logger.warning(
                "OPENAI_API_KEY não definida: a conversa geral vai responder com uma "
                "mensagem padrão. Consultas de folha e busca web funcionam normalmente."
            )

    @property
    def available(self) -> bool:
        return self.client is not None

    @staticmethod
    def get_system_prompt() -> str:
        return _SYSTEM_PROMPT

    async def generate_response(
        self,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> str:
        """Gera uma resposta conversacional, opcionalmente com histórico recente.

        Levanta ``LLMUnavailableError`` se o LLM não estiver configurado.
        """
        if self.client is None:
            raise LLMUnavailableError("OPENAI_API_KEY não configurada")

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
