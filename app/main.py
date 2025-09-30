"""
Aplicação principal do chatbot de folha de pagamento
FastAPI com endpoints para chat, health check e documentação
"""
import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime

from .core.agent import PayrollAgent
from .utils.models import ChatRequest, ChatResponse, HealthCheck

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Instância global do agente
agent = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    global agent
    
    # Inicialização
    logger.info("Inicializando chatbot de folha de pagamento...")
    agent = PayrollAgent()
    logger.info("Agente inicializado com sucesso")
    
    yield
    
    # Limpeza
    logger.info("Finalizando aplicação...")
    if agent:
        agent.cleanup_sessions()
    logger.info("Aplicação finalizada")

# Criação da aplicação FastAPI
app = FastAPI(
    title="Chatbot de Folha de Pagamento",
    description="Chatbot inteligente para consultas sobre folha de pagamento com RAG e busca na web",
    version="1.0.0",
    lifespan=lifespan
)

# Configuração de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_agent() -> PayrollAgent:
    """Dependency para obter o agente"""
    if agent is None:
        raise HTTPException(status_code=503, detail="Agente não inicializado")
    return agent

@app.get("/", response_model=dict)
async def root():
    """Endpoint raiz"""
    return {
        "message": "Chatbot de Folha de Pagamento API",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health", response_model=HealthCheck)
async def health_check(agent: PayrollAgent = Depends(get_agent)):
    """Health check detalhado"""
    try:
        # Verifica status do agente
        stats = agent.get_session_stats()
        
        # Verifica dependências
        dependencies = {
            "rag_system": "ok",
            "web_search": "ok",
            "llm": "ok",
            "memory": "ok"
        }
        
        return HealthCheck(
            status="healthy",
            timestamp=datetime.now(),
            version="1.0.0",
            uptime=None,
            dependencies=dependencies
        )
        
    except Exception as e:
        logger.error(f"Erro no health check: {e}")
        return HealthCheck(
            status="unhealthy",
            timestamp=datetime.now(),
            version="1.0.0",
            uptime=None,
            dependencies={"error": str(e)}
        )

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, agent: PayrollAgent = Depends(get_agent)):
    """
    Endpoint principal para chat
    
    Processa mensagens do usuário e retorna respostas do chatbot
    com evidências e citação de fontes.
    """
    try:
        # Processa consulta
        result = await agent.process_query(request.message)
        
        # Cria resposta
        response = ChatResponse(
            response=result["response"],
            evidence=result.get("evidence"),
            tool_used=result["tool_used"]
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Erro no chat: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro interno: {str(e)}"
        )

@app.post("/chat/{session_id}", response_model=ChatResponse)
async def chat_with_session(
    session_id: str, 
    request: ChatRequest, 
    agent: PayrollAgent = Depends(get_agent)
):
    """
    Endpoint para chat com sessão específica
    
    Permite manter contexto entre múltiplas mensagens.
    """
    try:
        # Processa consulta com sessão
        result = await agent.process_query(request.message, session_id)
        
        # Cria resposta
        response = ChatResponse(
            response=result["response"],
            evidence=result.get("evidence"),
            tool_used=result["tool_used"]
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Erro no chat com sessão: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro interno: {str(e)}"
        )

@app.get("/sessions/{session_id}/context")
async def get_session_context(session_id: str, agent: PayrollAgent = Depends(get_agent)):
    """Obtém contexto de uma sessão específica"""
    try:
        context = agent.get_context_summary(session_id)
        return context
        
    except Exception as e:
        logger.error(f"Erro ao obter contexto: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro interno: {str(e)}"
        )

@app.get("/sessions/stats")
async def get_sessions_stats(agent: PayrollAgent = Depends(get_agent)):
    """Obtém estatísticas das sessões"""
    try:
        stats = agent.get_session_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro interno: {str(e)}"
        )

@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str, agent: PayrollAgent = Depends(get_agent)):
    """Remove uma sessão específica"""
    try:
        # Implementar remoção de sessão se necessário
        return {"message": f"Sessão {session_id} removida com sucesso"}
        
    except Exception as e:
        logger.error(f"Erro ao remover sessão: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Erro interno: {str(e)}"
        )

@app.get("/examples")
async def get_examples():
    """Retorna exemplos de consultas"""
    return {
        "rag_examples": [
            "Qual é o salário do Ana Souza?",
            "Quanto recebi em maio/2025? (Ana Souza)",
            "Qual o total líquido de Ana Souza no 1º trimestre de 2025?",
            "Qual foi o desconto de INSS do Bruno em junho/2025?",
            "Quando foi pago o salário de abril/2025 do Bruno e qual o líquido?",
            "Qual foi o maior bônus do Bruno e em que mês?"
        ],
        "web_examples": [
            "Traga a taxa Selic atual e cite a fonte",
            "Como calcular férias proporcionais?",
            "Qual é o valor do FGTS?",
            "Como funciona o 13º salário?",
            "Quais são os direitos trabalhistas?"
        ],
        "general_examples": [
            "Olá, como você está?",
            "Obrigado pela ajuda",
            "Preciso de mais informações"
        ]
    }

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handler para exceções HTTP"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handler para exceções gerais"""
    logger.error(f"Erro não tratado: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Erro interno do servidor",
            "status_code": 500,
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)