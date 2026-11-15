"""Normalização de texto para casar termos sem depender de acentos ou caixa."""
import re
import unicodedata
from collections.abc import Iterable
from functools import cache
from re import Pattern


def normalize(text: str) -> str:
    """Minúsculas e sem acentos: "Salário Líquido" -> "salario liquido", "1º" -> "1o"."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


@cache
def _terms_pattern(terms: tuple[str, ...]) -> Pattern[str]:
    alternatives = "|".join(
        re.escape(normalize(term)) for term in sorted(terms, key=len, reverse=True)
    )
    return re.compile(rf"\b(?:{alternatives})\b")


def contains_any(text: str, terms: Iterable[str]) -> bool:
    """True se algum termo aparece em ``text`` como palavra inteira.

    Ao contrário de ``term in text``, "ana" não casa com "semana" e "lei" não
    casa com "leitura".
    """
    return bool(_terms_pattern(tuple(terms)).search(normalize(text)))
