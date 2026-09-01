"""Sobe a API em modo de desenvolvimento."""
import os
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    if not Path("app/main.py").exists():
        print("Erro: execute este script a partir da raiz do projeto.")
        sys.exit(1)

    if not Path(".env").exists():
        print("Aviso: .env não encontrado.")
        print("Copie .env.example para .env e preencha OPENAI_API_KEY.")

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"API em http://{host}:{port}  (documentação em /docs)")
    print("Ctrl+C para parar.")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )


if __name__ == "__main__":
    main()
