"""
Utilitários de formatação para o sistema de folha de pagamento
Implementa formatação brasileira de moeda, datas e números
"""

import re
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

_CENT = Decimal("0.01")
# "1.500" ou "1.500.000": pontos como separador de milhar (padrão brasileiro).
_THOUSANDS_ONLY = re.compile(r"\d{1,3}(?:\.\d{3})+")


def _parse_decimal(value: str | None) -> Decimal | None:
    """Lê um valor monetário em texto ("R$ 1.500,50", "1500.50", "-10")."""
    cleaned = re.sub(r"[^\d,.-]", "", value or "")
    negative = cleaned.startswith("-")
    cleaned = cleaned.replace("-", "")
    if not cleaned:
        return None
    if "," in cleaned:
        # Vírgula decimal e pontos de milhar: 1.500,50
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif _THOUSANDS_ONLY.fullmatch(cleaned):
        cleaned = cleaned.replace(".", "")
    try:
        amount = Decimal(cleaned)
    except InvalidOperation:
        return None
    return -amount if negative else amount


def format_currency(value: float | str | Decimal) -> str:
    """
    Formata valor em moeda brasileira (R$ 1.500,50; negativos como -R$ 10,00).

    Arredonda meio centavo para cima (2,675 -> R$ 2,68), sem os desvios de
    ponto flutuante de ``f"{x:.2f}"``. Valores inválidos viram "R$ 0,00".
    """
    try:
        if isinstance(value, str):
            amount = _parse_decimal(value)
            if amount is None:
                return "R$ 0,00"
        else:
            amount = Decimal(str(value))
        amount = amount.quantize(_CENT, rounding=ROUND_HALF_UP)
        sign = "-" if amount < 0 else ""
    except (InvalidOperation, ValueError, TypeError):
        return "R$ 0,00"

    formatted = f"{abs(amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{sign}R$ {formatted}"


def parse_currency(value: str | None) -> float | None:
    """
    Converte string de moeda para float ("R$ 1.500,50" -> 1500.5, "1.500" -> 1500.0).

    Returns:
        Float com o valor ou None se inválido
    """
    amount = _parse_decimal(value)
    return float(amount) if amount is not None else None


def format_date(date_input: str | datetime) -> str:
    """
    Formata data para formato brasileiro (dd/mm/aaaa)

    Args:
        date_input: Data em string ou datetime

    Returns:
        String formatada em dd/mm/aaaa
    """
    try:
        if isinstance(date_input, str):
            # Tenta diferentes formatos de entrada
            formats = [
                "%Y-%m-%d",  # 2025-01-28
                "%d/%m/%Y",  # 28/01/2025
                "%d-%m-%Y",  # 28-01-2025
                "%Y/%m/%d",  # 2025/01/28
            ]

            for fmt in formats:
                try:
                    date_obj = datetime.strptime(date_input, fmt)
                    return date_obj.strftime("%d/%m/%Y")
                except ValueError:
                    continue

            # Se nenhum formato funcionou, retorna como está
            return date_input

        return date_input.strftime("%d/%m/%Y")

    except (ValueError, TypeError, AttributeError):
        return "Data inválida"


def parse_date(date_str: str) -> str | None:
    """
    Converte string de data para formato YYYY-MM-DD

    Args:
        date_str: String com data

    Returns:
        String no formato YYYY-MM-DD ou None se inválido
    """
    try:
        if not date_str:
            return None

        # Remove espaços extras
        date_str = date_str.strip()

        # Tenta diferentes formatos de entrada
        formats = [
            "%d/%m/%Y",  # 28/01/2025
            "%d-%m-%Y",  # 28-01-2025
            "%Y-%m-%d",  # 2025-01-28
            "%Y/%m/%d",  # 2025/01/28
        ]

        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    except (ValueError, TypeError, AttributeError):
        return None


def format_competency(competency: str) -> str:
    """
    Formata competência para exibição

    Args:
        competency: Competência no formato YYYY-MM

    Returns:
        Competência formatada
    """
    try:
        if not competency:
            return ""

        # Se já está no formato YYYY-MM
        if re.match(r"\d{4}-\d{2}", competency):
            year, month = competency.split("-")

            # Mapeamento de meses
            month_names = {
                "01": "Janeiro",
                "02": "Fevereiro",
                "03": "Março",
                "04": "Abril",
                "05": "Maio",
                "06": "Junho",
                "07": "Julho",
                "08": "Agosto",
                "09": "Setembro",
                "10": "Outubro",
                "11": "Novembro",
                "12": "Dezembro",
            }

            month_name = month_names.get(month, month)
            return f"{month_name}/{year}"

        return competency

    except (ValueError, TypeError, AttributeError):
        return competency
