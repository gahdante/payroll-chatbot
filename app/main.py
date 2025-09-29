"""
Entry point do FastAPI - Define o endpoint /chat
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

from .core.agent import PayrollAgent
from .utils.models import ChatRequest, ChatResponse

# Carrega variáveis de ambiente
load_dotenv()

app = FastAPI(
    title="Payroll Chatbot API",
    description="API para consultas sobre folha de pagamento",
    version="1.0.0"
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializa o agente
agent = PayrollAgent()

@app.get("/")
async def root():
    """Endpoint de health check"""
    return {"message": "Payroll Chatbot API is running"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Endpoint principal para conversas com o chatbot
    """
    try:
        response = await agent.process_query(request.message)
        return ChatResponse(
            response=response["response"],
            evidence=response.get("evidence", ""),
            tool_used=response.get("tool_used", "unknown")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@app.get("/health")
async def health_check():
    """Endpoint de health check detalhado"""
    return {
        "status": "healthy",
        "agent_initialized": agent is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
