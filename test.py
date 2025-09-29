"""
Script para executar testes
"""
import os
import sys
import subprocess
from pathlib import Path

def run_tests():
    """Executa os testes do projeto"""
    print("🧪 Executando testes do Chatbot de Folha de Pagamento...")
    
    # Verifica se estamos no diretório correto
    if not Path("tests").exists():
        print("❌ Erro: Execute este script a partir do diretório raiz do projeto")
        sys.exit(1)
    
    # Verifica se pytest está instalado
    try:
        import pytest
    except ImportError:
        print("❌ pytest não está instalado")
        print("💡 Execute: pip install pytest pytest-asyncio")
        sys.exit(1)
    
    # Executa os testes
    test_args = [
        "pytest",
        "tests/",
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    # Adiciona argumentos opcionais
    if "--coverage" in sys.argv:
        test_args.extend(["--cov=app", "--cov-report=html", "--cov-report=term"])
        print("📊 Executando com cobertura de código...")
    
    if "--fast" in sys.argv:
        test_args.extend(["-x", "--tb=line"])
        print("⚡ Executando em modo rápido...")
    
    try:
        result = subprocess.run(test_args, check=True)
        print("\n✅ Todos os testes passaram!")
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Alguns testes falharam (código: {e.returncode})")
        return e.returncode
    except KeyboardInterrupt:
        print("\n🛑 Testes interrompidos pelo usuário")
        return 1

def main():
    """Função principal"""
    print("🔧 Opções disponíveis:")
    print("  python test.py           - Executa todos os testes")
    print("  python test.py --coverage - Executa com cobertura de código")
    print("  python test.py --fast    - Executa em modo rápido")
    print()
    
    return run_tests()

if __name__ == "__main__":
    sys.exit(main())
