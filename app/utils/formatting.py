"""
Utilitários de formatação para o sistema de folha de pagamento
Implementa formatação brasileira de moeda, datas e números
"""
import re
from datetime import datetime
from typing import Union, Optional, List

def format_currency(value: Union[float, str, int]) -> str:
    """
    Formata valor em moeda brasileira (R$ 1.500,50)
    
    Args:
        value: Valor a ser formatado
        
    Returns:
        String formatada em moeda brasileira
    """
    try:
        # Converte para float se necessário
        if isinstance(value, str):
            # Remove caracteres não numéricos exceto vírgula e ponto
            value = re.sub(r'[^\d,.-]', '', value)
            # Substitui vírgula por ponto para conversão
            value = value.replace(',', '.')
            value = float(value)
        
        # Formata com 2 casas decimais
        formatted = f"{float(value):,.2f}"
        
        # Substitui vírgula por X, ponto por vírgula, X por ponto
        formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        return f"R$ {formatted}"
        
    except (ValueError, TypeError):
        return "R$ 0,00"

def parse_currency(value: str) -> Optional[float]:
    """
    Converte string de moeda para float
    
    Args:
        value: String com valor monetário
        
    Returns:
        Float com o valor ou None se inválido
    """
    try:
        if not value:
            return None
            
        # Remove caracteres não numéricos exceto vírgula e ponto
        cleaned = re.sub(r'[^\d,.-]', '', value)
        
        if not cleaned:
            return None
        
        # Se tem vírgula e ponto, assume formato brasileiro (1.500,50)
        if ',' in cleaned and '.' in cleaned:
            # Remove pontos de milhares e substitui vírgula por ponto
            cleaned = cleaned.replace('.', '').replace(',', '.')
        elif ',' in cleaned and '.' not in cleaned:
            # Apenas vírgula, assume formato brasileiro
            cleaned = cleaned.replace(',', '.')
        
        return float(cleaned)
        
    except (ValueError, TypeError):
        return None

def format_date(date_input: Union[str, datetime]) -> str:
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
                '%Y-%m-%d',      # 2025-01-28
                '%d/%m/%Y',      # 28/01/2025
                '%d-%m-%Y',      # 28-01-2025
                '%Y/%m/%d',      # 2025/01/28
            ]
            
            for fmt in formats:
                try:
                    date_obj = datetime.strptime(date_input, fmt)
                    return date_obj.strftime('%d/%m/%Y')
                except ValueError:
                    continue
            
            # Se nenhum formato funcionou, retorna como está
            return date_input
            
        elif isinstance(date_input, datetime):
            return date_input.strftime('%d/%m/%Y')
        else:
            return str(date_input)
            
    except Exception:
        return "Data inválida"

def parse_date(date_str: str) -> Optional[str]:
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
            '%d/%m/%Y',      # 28/01/2025
            '%d-%m-%Y',      # 28-01-2025
            '%Y-%m-%d',      # 2025-01-28
            '%Y/%m/%d',      # 2025/01/28
        ]
        
        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        return None
        
    except Exception:
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
        if re.match(r'\d{4}-\d{2}', competency):
            year, month = competency.split('-')
            
            # Mapeamento de meses
            month_names = {
                '01': 'Janeiro', '02': 'Fevereiro', '03': 'Março',
                '04': 'Abril', '05': 'Maio', '06': 'Junho',
                '07': 'Julho', '08': 'Agosto', '09': 'Setembro',
                '10': 'Outubro', '11': 'Novembro', '12': 'Dezembro'
            }
            
            month_name = month_names.get(month, month)
            return f"{month_name}/{year}"
        
        return competency
        
    except Exception:
        return competency

def parse_competency(competency: str) -> Optional[str]:
    """
    Converte competência para formato YYYY-MM
    
    Args:
        competency: Competência em formato variado
        
    Returns:
        Competência no formato YYYY-MM ou None se inválido
    """
    try:
        if not competency:
            return None
        
        competency = competency.strip()
        
        # Se já está no formato YYYY-MM
        if re.match(r'\d{4}-\d{2}', competency):
            return competency
        
        # Tenta converter de outros formatos
        # Ex: "Janeiro/2025" -> "2025-01"
        month_mapping = {
            'janeiro': '01', 'fevereiro': '02', 'março': '03',
            'abril': '04', 'maio': '05', 'junho': '06',
            'julho': '07', 'agosto': '08', 'setembro': '09',
            'outubro': '10', 'novembro': '11', 'dezembro': '12'
        }
        
        # Padrão: mês/ano ou mês-ano
        pattern = r'(\w+)[/-](\d{4})'
        match = re.search(pattern, competency.lower())
        
        if match:
            month_name, year = match.groups()
            month_num = month_mapping.get(month_name)
            if month_num:
                return f"{year}-{month_num}"
        
        return None
        
    except Exception:
        return None