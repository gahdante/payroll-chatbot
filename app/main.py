"""API FastAPI do chatbot de folha de pagamento."""

import logging
import os
from collections.abc import Mapping
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Annotated, Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Path, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.agent import PayrollAgent
from .utils.models import (
    MAX_MESSAGE_LENGTH,
    MAX_SESSION_ID_LENGTH,
    ChatRequest,
    ChatResponse,
    HealthCheck,
)

# Antes de ler qualquer variável: LOG_LEVEL e ALLOWED_ORIGINS logo abaixo, e as
# chaves da OpenAI e do Google quando o agente é criado.
load_dotenv()

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"

_state: dict[str, PayrollAgent | None] = {"agent": None}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Inicializando o chatbot de folha de pagamento...")
    _state["agent"] = PayrollAgent()
    logger.info("Agente pronto.")
    yield
    _state["agent"] = None
    logger.info("Aplicação finalizada.")


app = FastAPI(
    title="Chatbot de Folha de Pagamento",
    description="Consultas de folha de pagamento com RAG, busca web e memória de conversa.",
    version=APP_VERSION,
    lifespan=lifespan,
)

_allowed_origins = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173").split(
        ","
    )
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)


def get_agent() -> PayrollAgent:
    agent = _state.get("agent")
    if agent is None:
        raise HTTPException(status_code=503, detail="Agente não inicializado")
    return agent


@app.get("/")
async def root():
    return {
        "message": "Chatbot de Folha de Pagamento API",
        "version": APP_VERSION,
        "status": "running",
    }


@app.get("/health", response_model=HealthCheck)
async def health_check(agent: PayrollAgent = Depends(get_agent)):
    agent.rag.ensure_loaded()
    dependencies = {
        "rag": "ok" if not agent.rag.df.empty else "sem dados",
        "llm": "ok" if agent.llm.available else "sem OPENAI_API_KEY",
        "web_search": "google" if not agent.web_search.use_fallback else "referencia-local",
        "memory": f"{len(agent.memory.sessions)} sessao(oes)",
    }
    healthy = dependencies["rag"] == "ok" and dependencies["llm"] == "ok"
    return HealthCheck(
        status="healthy" if healthy else "degraded",
        version=APP_VERSION,
        dependencies=dependencies,
    )


async def _run_chat(agent: PayrollAgent, message: str, session_id: str | None) -> ChatResponse:
    try:
        result = await agent.process_query(message, session_id)
    except Exception:
        logger.exception("Erro no /chat")
        raise HTTPException(
            status_code=500, detail="Erro interno ao processar a mensagem"
        ) from None
    return ChatResponse(
        response=result["response"],
        evidence=result.get("evidence"),
        tool_used=result["tool_used"],
        session_id=result.get("session_id"),
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, agent: PayrollAgent = Depends(get_agent)):
    return await _run_chat(agent, request.message, request.session_id)


@app.post("/chat/{session_id}", response_model=ChatResponse)
async def chat_with_session(
    session_id: Annotated[str, Path(max_length=MAX_SESSION_ID_LENGTH)],
    request: ChatRequest,
    agent: PayrollAgent = Depends(get_agent),
):
    return await _run_chat(agent, request.message, session_id)


@app.get("/sessions/{session_id}/context")
async def session_context(session_id: str, agent: PayrollAgent = Depends(get_agent)):
    return agent.get_context_summary(session_id)


@app.get("/sessions/stats")
async def sessions_stats(agent: PayrollAgent = Depends(get_agent)):
    return agent.get_session_stats()


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, agent: PayrollAgent = Depends(get_agent)):
    if not agent.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    return {"message": f"Sessão {session_id} removida"}


@app.get("/examples")
async def examples():
    return {
        "rag": [
            "Quanto recebi (líquido) em maio/2025? (Ana Souza)",
            "Qual o total líquido de Ana Souza no 1º trimestre de 2025?",
            "Qual foi o desconto de INSS do Bruno em jun/2025?",
            "Quando foi pago o salário de abril/2025 do Bruno e qual o líquido?",
            "Qual foi o maior bônus do Bruno e em que mês?",
        ],
        "web": [
            "Traga a taxa Selic atual e cite a fonte",
            "Como calcular férias proporcionais?",
            "Como funciona o 13º salário?",
        ],
        "geral": ["Olá, tudo bem?", "Obrigado pela ajuda"],
    }


# Erros --------------------------------------------------------------------------
# Todos os erros saem no mesmo formato: {"error", "status_code", "timestamp"},
# mais "details" nos erros de validação.


def _error_response(
    status_code: int,
    message: str,
    details: list[dict[str, str]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    content: dict[str, Any] = {
        "error": message,
        "status_code": status_code,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if details is not None:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content, headers=headers)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    # Também cobre os 404/405 de rota inexistente, que o Starlette gera sozinho.
    return _error_response(exc.status_code, str(exc.detail), headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    errors = [dict(error) for error in exc.errors()]
    fields = {str(part) for error in errors for part in error.get("loc", ())}
    if "message" in fields:
        message = f"A mensagem precisa ter entre 1 e {MAX_MESSAGE_LENGTH} caracteres."
    elif "session_id" in fields:
        message = f"O session_id pode ter no máximo {MAX_SESSION_ID_LENGTH} caracteres."
    else:
        message = "Dados inválidos na requisição."
    details = [
        {
            "campo": ".".join(str(part) for part in error.get("loc", ())),
            "mensagem": str(error.get("msg", "")),
        }
        for error in errors
    ]
    return _error_response(422, message, details=details)


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    logger.exception("Erro não tratado: %s", exc)
    return _error_response(500, "Erro interno do servidor")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
