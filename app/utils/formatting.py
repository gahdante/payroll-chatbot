"""
Funções para R$ (BRL) e parsing/validação de datas
"""
import re
from typing import Optional, Union
from datetime import datetime
import locale

def format_currency(value: Union[float, int, str]) -> str:
    """
    Formata valor monetário em Real brasileiro (R$)
    
    Args:
        value: Valor a ser formatado
    
    Returns:
        String formatada em R$ brasileiro
    """
    try:
        # Converte para float se necessário
        if isinstance(value, str):
            # Remove caracteres não numéricos exceto ponto e vírgula
            clean_value = re.sub(r'[^\d.,]', '', value)
            # Substitui vírgula por ponto para conversão
            clean_value = clean_value.replace(',', '.')
            value = float(clean_value)
        elif isinstance(value, int):
            value = float(value)
        
        # Formata com 2 casas decimais
        formatted = f"R$ {value:,.2f}"
        
        # Substitui vírgula por ponto para separador de milhares
        # e ponto por vírgula para separador decimal (padrão brasileiro)
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        return formatted
        
    except (ValueError, TypeError):
        return "R$ 0,00"

def parse_currency(value: str) -> Optional[float]:
    """
    Converte string de moeda para float
    
    Args:
        value: String com valor monetário (ex: "R$ 1.500,00")
    
    Returns:
        Float com o valor ou None se inválido
    """
    try:
        # Remove R$ e espaços
        clean_value = re.sub(r'R\$\s*', '', value)
        
        # Remove pontos (separadores de milhares)
        clean_value = clean_value.replace('.', '')
        
        # Substitui vírgula por ponto (separador decimal)
        clean_value = clean_value.replace(',', '.')
        
        return float(clean_value)
        
    except (ValueError, TypeError):
        return None

def format_date(date_value: Union[str, datetime], format_input: str = "%Y-%m-%d") -> str:
    """
    Formata data para padrão brasileiro (dd/mm/aaaa)
    
    Args:
        date_value: Data a ser formatada
        format_input: Formato de entrada da data
    
    Returns:
        String formatada em dd/mm/aaaa
    """
    try:
        if isinstance(date_value, str):
            date_obj = datetime.strptime(date_value, format_input)
        else:
            date_obj = date_value
        
        return date_obj.strftime("%d/%m/%Y")
        
    except (ValueError, TypeError):
        return "Data inválida"

def parse_date(date_string: str, format_output: str = "%Y-%m-%d") -> Optional[str]:
    """
    Converte data do formato brasileiro para formato ISO
    
    Args:
        date_string: Data em formato brasileiro (dd/mm/aaaa)
        format_output: Formato de saída desejado
    
    Returns:
        String com data no formato ISO ou None se inválida
    """
    try:
        # Tenta diferentes formatos de entrada
        formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"]
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_string, fmt)
                return date_obj.strftime(format_output)
            except ValueError:
                continue
        
        return None
        
    except (ValueError, TypeError):
        return None

def validate_date_range(start_date: str, end_date: str) -> bool:
    """
    Valida se o intervalo de datas é válido
    
    Args:
        start_date: Data inicial
        end_date: Data final
    
    Returns:
        True se válido, False caso contrário
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        return start <= end
        
    except (ValueError, TypeError):
        return False

def format_percentage(value: Union[float, int], decimals: int = 2) -> str:
    """
    Formata valor como porcentagem
    
    Args:
        value: Valor a ser formatado
        decimals: Número de casas decimais
    
    Returns:
        String formatada como porcentagem
    """
    try:
        if isinstance(value, str):
            value = float(value)
        
        return f"{value:.{decimals}f}%"
        
    except (ValueError, TypeError):
        return "0,00%"

def format_number(value: Union[float, int, str], decimals: int = 2) -> str:
    """
    Formata número com separadores de milhares
    
    Args:
        value: Valor a ser formatado
        decimals: Número de casas decimais
    
    Returns:
        String formatada com separadores
    """
    try:
        if isinstance(value, str):
            value = float(value)
        
        # Formata com separadores
        formatted = f"{value:,.{decimals}f}"
        
        # Ajusta para padrão brasileiro
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        return formatted
        
    except (ValueError, TypeError):
        return "0,00"

def clean_text(text: str) -> str:
    """
    Limpa texto removendo caracteres especiais e normalizando
    
    Args:
        text: Texto a ser limpo
    
    Returns:
        Texto limpo
    """
    if not text:
        return ""
    
    # Remove caracteres especiais
    cleaned = re.sub(r'[^\w\s]', '', text)
    
    # Remove espaços extras
    cleaned = re.sub(r'\s+', ' ', cleaned)
    
    # Remove espaços no início e fim
    cleaned = cleaned.strip()
    
    return cleaned

def extract_numbers(text: str) -> list:
    """
    Extrai números de um texto
    
    Args:
        text: Texto para extrair números
    
    Returns:
        Lista de números encontrados
    """
    numbers = re.findall(r'\d+\.?\d*', text)
    return [float(num) for num in numbers if num]

def format_employee_name(name: str) -> str:
    """
    Formata nome do funcionário (primeira letra maiúscula)
    
    Args:
        name: Nome do funcionário
    
    Returns:
        Nome formatado
    """
    if not name:
        return ""
    
    # Divide em palavras
    words = name.split()
    
    # Capitaliza cada palavra
    formatted_words = [word.capitalize() for word in words]
    
    return " ".join(formatted_words)

def format_department_name(dept: str) -> str:
    """
    Formata nome do departamento
    
    Args:
        dept: Nome do departamento
    
    Returns:
        Nome formatado
    """
    if not dept:
        return ""
    
    # Converte para maiúsculo
    return dept.upper()

def format_position_name(position: str) -> str:
    """
    Formata nome do cargo
    
    Args:
        position: Nome do cargo
    
    Returns:
        Nome formatado
    """
    if not position:
        return ""
    
    # Capitaliza primeira letra de cada palavra
    words = position.split()
    formatted_words = [word.capitalize() for word in words]
    
    return " ".join(formatted_words)
