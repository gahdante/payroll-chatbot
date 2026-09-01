"""Fixtures compartilhadas dos testes."""
import os
from pathlib import Path

import pytest

# O agente instancia LLMConfig na criação; os testes não fazem chamadas reais.
os.environ.setdefault("OPENAI_API_KEY", "test-key")

DATA_CSV = Path(__file__).resolve().parents[1] / "data" / "payroll.csv"


@pytest.fixture
def payroll_csv() -> str:
    """Caminho para o CSV real da folha usado no desafio."""
    return str(DATA_CSV)
