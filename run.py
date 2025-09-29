"""
Script para executar a aplicação
"""
import os
import sys
import uvicorn
from pathlib import Path

def main():
    """Executa a aplicação"""
    # Verifica se estamos no diretório correto
    if not Path("app/main.py").exists():
        print("❌ Erro: Execute este script a partir do diretório raiz do projeto")
        sys.exit(1)
    
    # Verifica se o arquivo .env existe
    if not Path(".env").exists():
        print("⚠️  Arquivo .env não encontrado")
        print("💡 Execute: python setup.py para configurar o projeto")
        print("💡 Ou copie config.example para .env e configure suas chaves de API")
    
    print("Iniciando Chatbot de Folha de Pagamento...")
    print("API disponivel em: http://localhost:8000")
    print("Documentacao em: http://localhost:8000/docs")
    print("Pressione Ctrl+C para parar")
    
    # Executa a aplicação
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

if __name__ == "__main__":
    main()
