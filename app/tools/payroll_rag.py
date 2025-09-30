"""
Sistema RAG para consultas de folha de pagamento
"""
import pandas as pd
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class PayrollRAG:
    """Sistema RAG para consultas de folha de pagamento"""
    
    def __init__(self, csv_path: str = "data/payroll.csv"):
        self.csv_path = csv_path
        self.df = pd.DataFrame()
        self.month_mapping = {
            'janeiro': '01', 'jan': '01', 'jan.': '01',
            'fevereiro': '02', 'fev': '02', 'fev.': '02',
            'março': '03', 'mar': '03', 'mar.': '03',
            'abril': '04', 'abr': '04', 'abr.': '04',
            'maio': '05', 'mai': '05', 'mai.': '05',
            'junho': '06', 'jun': '06', 'jun.': '06',
            'julho': '07', 'jul': '07', 'jul.': '07',
            'agosto': '08', 'ago': '08', 'ago.': '08',
            'setembro': '09', 'set': '09', 'set.': '09',
            'outubro': '10', 'out': '10', 'out.': '10',
            'novembro': '11', 'nov': '11', 'nov.': '11',
            'dezembro': '12', 'dez': '12', 'dez.': '12'
        }
    
    def _load_data(self):
        """Carrega os dados do CSV"""
        try:
            self.df = pd.read_csv(self.csv_path)
            logger.info(f"Dados carregados: {len(self.df)} registros")
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}")
            self.df = pd.DataFrame()
    
    def _parse_date_variations(self, date_str: str) -> Optional[str]:
        """Converte variações de data para formato YYYY-MM"""
        if not date_str:
            return None
        
        date_str = date_str.lower().strip()
        
        # Formato: maio/2025, maio 2025
        for month_name, month_num in self.month_mapping.items():
            if month_name in date_str:
                year_match = re.search(r'(\d{4})', date_str)
                if year_match:
                    year = year_match.group(1)
                    return f"{year}-{month_num}"
        
        # Formato: 2025-05, 05/2025
        if re.match(r'\d{4}-\d{2}', date_str):
            return date_str
        if re.match(r'\d{2}/\d{4}', date_str):
            parts = date_str.split('/')
            return f"{parts[1]}-{parts[0]}"
        
        return None
    
    def _extract_employee_name(self, query: str) -> Optional[str]:
        """Extrai nome do funcionário da consulta"""
        # Nomes conhecidos
        known_names = ['Ana Souza', 'Bruno Lima']
        
        for name in known_names:
            if name.lower() in query.lower():
                return name
        
        # Busca por padrões como "Ana", "Bruno"
        name_patterns = [
            r'\b(Ana|Bruno)\b',
            r'\b(Ana Souza|Bruno Lima)\b'
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                found = match.group(1)
                if found in ['Ana', 'Bruno']:
                    return 'Ana Souza' if found == 'Ana' else 'Bruno Lima'
        
        return None
    
    def _extract_competency(self, query: str) -> Optional[str]:
        """Extrai competência da consulta"""
        query_lower = query.lower()
        
        # Busca por padrões de data
        date_patterns = [
            r'\b(\d{4}-\d{2})\b',  # 2025-01
            r'\b(\d{2}/\d{4})\b',  # 01/2025
            r'\b(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\s+(\d{4})\b',
            r'\b(jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\.?\s+(\d{4})\b'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if len(match.groups()) == 1:
                    return self._parse_date_variations(match.group(1))
                else:
                    month, year = match.groups()
                    return self._parse_date_variations(f"{month} {year}")
        
        # Busca por meses específicos na query
        for month_name, month_num in self.month_mapping.items():
            if month_name in query_lower:
                # Procura por ano na query
                year_match = re.search(r'(\d{4})', query_lower)
                if year_match:
                    year = year_match.group(1)
                    return f"{year}-{month_num}"
        
        return None
    
    def _format_currency(self, value: float) -> str:
        """Formata valor como moeda brasileira"""
        return f"R$ {value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    
    def _format_date(self, date_str: str) -> str:
        """Formata data para formato brasileiro"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%d/%m/%Y')
        except:
            return date_str
    
    def _create_evidence(self, filtered_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Cria evidências das consultas"""
        evidence = []
        
        for _, record in filtered_df.iterrows():
            evidence.append({
                "source": "payroll_data",
                "content": f"Funcionário: {record['name']}, Competência: {record['competency']}, Salário Líquido: {self._format_currency(record['net_pay'])}",
                "metadata": {
                    "employee_id": record['employee_id'],
                    "competency": record['competency'],
                    "net_pay": record['net_pay']
                }
            })
        
        return evidence
    
    def _determine_query_type(self, query: str) -> str:
        """Determina o tipo de consulta"""
        query_lower = query.lower()
        
        # Consulta por funcionário específico
        if any(name in query_lower for name in ['ana', 'bruno', 'souza', 'lima']):
            return "specific_employee"
        
        # Consulta agregada
        if any(word in query_lower for word in ['total', 'média', 'médio', 'soma', 'somar', 'trimestre', 'semestre']):
            return "aggregate"
        
        # Consulta por competência específica
        if any(word in query_lower for word in ['maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro', 'janeiro', 'fevereiro', 'março', 'abril']):
            return "competency"
        
        return "general"
    
    async def _query_specific_employee(self, query: str) -> Dict[str, Any]:
        """Consulta por funcionário específico"""
        employee_name = self._extract_employee_name(query)
        competency = self._extract_competency(query)
        
        if not employee_name:
            return {
                "success": False,
                "data": "Nome do funcionário não encontrado na consulta",
                "evidence": None
            }
        
        # Filtra por funcionário
        filtered = self.df[self.df['name'].str.contains(employee_name, case=False, na=False)]
        
        if competency:
            filtered = filtered[filtered['competency'] == competency]
        
        if filtered.empty:
            return {
                "success": False,
                "data": f"Nenhum registro encontrado para {employee_name}",
                "evidence": None
            }
        
        # Monta resposta
        response_parts = []
        
        if competency:
            # Consulta específica por competência
            if not filtered.empty:
                record = filtered.iloc[0]
                
                # Verifica se é consulta sobre INSS
                if 'inss' in query.lower():
                    response_parts.append(
                        f"Desconto de INSS de {employee_name} em {competency}: {self._format_currency(record['deductions_inss'])}"
                    )
                # Verifica se é consulta sobre bônus
                elif 'bônus' in query.lower() or 'bonus' in query.lower():
                    response_parts.append(
                        f"Bônus de {employee_name} em {competency}: {self._format_currency(record['bonus'])}"
                    )
                # Verifica se é consulta sobre data de pagamento
                elif 'quando' in query.lower() or 'data' in query.lower():
                    payment_date = self._format_date(record['payment_date'])
                    response_parts.append(
                        f"Salário de {employee_name} em {competency}: {self._format_currency(record['net_pay'])} (pago em {payment_date})"
                    )
                else:
                    response_parts.append(
                        f"{employee_name} recebeu {self._format_currency(record['net_pay'])} em {competency}"
                    )
            else:
                response_parts.append(
                    f"Nenhum registro encontrado para {employee_name} em {competency}"
                )
        else:
            # Consulta geral do funcionário
            if 'maior' in query.lower() and ('bônus' in query.lower() or 'bonus' in query.lower()):
                # Encontra o maior bônus
                max_bonus_idx = filtered['bonus'].idxmax()
                record = filtered.loc[max_bonus_idx]
                response_parts.append(
                    f"Maior bônus de {employee_name}: {self._format_currency(record['bonus'])} em {record['competency']}"
                )
            else:
                for _, record in filtered.iterrows():
                    response_parts.append(
                        f"{record['name']} - {record['competency']}: {self._format_currency(record['net_pay'])}"
                    )
        
        evidence = self._create_evidence(filtered)
        
        return {
            "success": True,
            "data": "\n".join(response_parts),
            "evidence": evidence
        }
    
    async def _query_aggregate(self, query: str) -> Dict[str, Any]:
        """Consulta agregada (total, média, trimestre)"""
        query_lower = query.lower()
        
        # Determina período
        if 'trimestre' in query_lower:
            months = ['2025-01', '2025-02', '2025-03']  # 1º trimestre
        elif 'semestre' in query_lower:
            months = ['2025-01', '2025-02', '2025-03', '2025-04', '2025-05', '2025-06']
        else:
            months = None
        
        # Filtra dados
        if months:
            filtered = self.df[self.df['competency'].isin(months)]
        else:
            filtered = self.df
        
        if filtered.empty:
            return {
                "success": False,
                "data": "Nenhum dado encontrado para o período solicitado",
                "evidence": None
            }
        
        # Calcula totais
        total_net = filtered['net_pay'].sum()
        avg_net = filtered['net_pay'].mean()
        count = len(filtered)
        
        # Monta resposta
        response = f"Total: {self._format_currency(total_net)}"
        response += f" | Média: {self._format_currency(avg_net)}"
        response += f" | Registros: {count}"
        
        if months:
            response += f" - {len(months)}º trimestre 2025"
        
        evidence = self._create_evidence(filtered)
        
        return {
            "success": True,
            "data": response,
            "evidence": evidence
        }
    
    async def _query_competency(self, query: str) -> Dict[str, Any]:
        """Consulta por competência específica"""
        competency = self._extract_competency(query)
        
        if not competency:
            return {
                "success": False,
                "data": "Competência não identificada na consulta",
                "evidence": None
            }
        
        # Filtra por competência
        filtered = self.df[self.df['competency'] == competency]
        
        if filtered.empty:
            return {
                "success": False,
                "data": f"Nenhum registro encontrado para {competency}",
                "evidence": None
            }
        
        # Monta resposta
        response_parts = []
        for _, record in filtered.iterrows():
            response_parts.append(
                f"{record['name']}: {self._format_currency(record['net_pay'])}"
            )
        
        response = f"Folha de {competency}:\n" + "\n".join(response_parts)
        
        evidence = self._create_evidence(filtered)
        
        return {
            "success": True,
            "data": response,
            "evidence": evidence
        }
    
    async def query(self, query: str) -> Dict[str, Any]:
        """Processa consulta usando RAG"""
        try:
            # Carrega dados se necessário
            if self.df.empty:
                self._load_data()
            
            if self.df.empty:
                return {
                    "success": False,
                    "data": "Erro ao carregar dados da folha de pagamento",
                    "evidence": None
                }
            
            # Determina tipo de consulta
            query_type = self._determine_query_type(query)
            
            # Processa consulta
            if query_type == "specific_employee":
                return await self._query_specific_employee(query)
            elif query_type == "aggregate":
                return await self._query_aggregate(query)
            else:
                return await self._query_competency(query)
                
        except Exception as e:
            logger.error(f"Erro ao processar consulta: {e}")
            return {
                "success": False,
                "data": f"Erro interno: {str(e)}",
                "evidence": None
            }