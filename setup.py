"""
Script de configuração inicial do projeto
"""
import os
import shutil
from pathlib import Path

def setup_project():
    """Configura o projeto inicial"""
    print("🚀 Configurando o projeto Chatbot de Folha de Pagamento...")
    
    # Cria arquivo .env se não existir
    env_file = Path(".env")
    config_example = Path("config.example")
    
    if not env_file.exists() and config_example.exists():
        shutil.copy(config_example, env_file)
        print("✅ Arquivo .env criado a partir do config.example")
        print("⚠️  Lembre-se de configurar suas chaves de API no arquivo .env")
    else:
        print("ℹ️  Arquivo .env já existe ou config.example não encontrado")
    
    # Verifica se o dataset existe
    data_file = Path("data/payroll.csv")
    if data_file.exists():
        print("✅ Dataset de folha de pagamento encontrado")
    else:
        print("⚠️  Dataset não encontrado em data/payroll.csv")
    
    # Cria diretórios necessários
    directories = ["logs", "temp"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Diretório {directory} criado")
    
    print("\n🎉 Configuração concluída!")
    print("\n📋 Próximos passos:")
    print("1. Configure suas chaves de API no arquivo .env")
    print("2. Instale as dependências: pip install -r requirements.txt")
    print("3. Execute a aplicação: python -m uvicorn app.main:app --reload")
    print("4. Acesse http://localhost:8000/docs para ver a documentação")

if __name__ == "__main__":
    setup_project()
