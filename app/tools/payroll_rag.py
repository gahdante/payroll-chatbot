"""
Implementa a consulta ao CSV via Pandas
"""
import pandas as pd
import os
import logging
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)

class PayrollRAG:
    """Sistema RAG para consultas ao dataset de folha de pagamento"""
    
    def __init__(self, csv_path: str = "data/payroll.csv"):
        self.csv_path = csv_path
        self.df = None
        self._load_data()
    
    def _load_data(self):
        """Carrega o dataset CSV"""
        try:
            if os.path.exists(self.csv_path):
                self.df = pd.read_csv(self.csv_path)
                logger.info(f"Dataset carregado com {len(self.df)} registros")
            else:
                logger.warning(f"Arquivo {self.csv_path} não encontrado")
                self.df = pd.DataFrame()
        except Exception as e:
            logger.error(f"Erro ao carregar dataset: {e}")
            self.df = pd.DataFrame()
    
    async def query(self, question: str) -> Dict[str, Any]:
        """
        Processa consulta ao dataset de folha de pagamento
        
        Args:
            question: Pergunta do usuário
        
        Returns:
            Dicionário com dados e evidência
        """
        if self.df is None or self.df.empty:
            return {
                "data": "Dataset não disponível",
                "evidence": "Nenhum dado encontrado",
                "success": False
            }
        
        try:
            # Analisa o tipo de consulta
            query_type = self._analyze_query_type(question)
            
            if query_type == "specific_employee":
                return await self._query_specific_employee(question)
            elif query_type == "aggregate":
                return await self._query_aggregate(question)
            elif query_type == "filter":
                return await self._query_filter(question)
            else:
                return await self._query_general(question)
                
        except Exception as e:
            logger.error(f"Erro na consulta RAG: {e}")
            return {
                "data": f"Erro ao processar consulta: {str(e)}",
                "evidence": "",
                "success": False
            }
    
    def _analyze_query_type(self, question: str) -> str:
        """
        Analisa o tipo de consulta baseado na pergunta
        
        Args:
            question: Pergunta do usuário
        
        Returns:
            Tipo de consulta: "specific_employee", "aggregate", "filter", "general"
        """
        question_lower = question.lower()
        
        # Consulta por funcionário específico
        if re.search(r'\b(nome|funcionário)\b', question_lower):
            return "specific_employee"
        
        # Consulta agregada
        if any(word in question_lower for word in ["total", "soma", "média", "máximo", "mínimo", "quantos"]):
            return "aggregate"
        
        # Consulta com filtros
        if any(word in question_lower for word in ["onde", "quando", "departamento", "cargo"]):
            return "filter"
        
        return "general"
    
    async def _query_specific_employee(self, question: str) -> Dict[str, Any]:
        """
        Consulta por funcionário específico
        
        Args:
            question: Pergunta do usuário
        
        Returns:
            Dados do funcionário
        """
        try:
            # Extrai nome do funcionário da pergunta
            employee_name = self._extract_employee_name(question)
            
            if not employee_name:
                return {
                    "data": "Nome do funcionário não identificado na pergunta",
                    "evidence": "",
                    "success": False
                }
            
            # Busca o funcionário
            employee_data = self.df[self.df['nome'].str.contains(employee_name, case=False, na=False)]
            
            if employee_data.empty:
                return {
                    "data": f"Nenhum funcionário encontrado com o nome '{employee_name}'",
                    "evidence": "",
                    "success": False
                }
            
            # Formata os dados
            formatted_data = self._format_employee_data(employee_data)
            
            return {
                "data": formatted_data,
                "evidence": f"Dados do funcionário {employee_name}",
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Erro na consulta por funcionário: {e}")
            return {
                "data": f"Erro ao buscar funcionário: {str(e)}",
                "evidence": "",
                "success": False
            }
    
    async def _query_aggregate(self, question: str) -> Dict[str, Any]:
        """
        Consulta agregada (totais, médias, etc.)
        
        Args:
            question: Pergunta do usuário
        
        Returns:
            Dados agregados
        """
        try:
            question_lower = question.lower()
            
            # Calcula estatísticas básicas
            total_employees = len(self.df)
            total_salary = self.df['salario'].sum() if 'salario' in self.df.columns else 0
            avg_salary = self.df['salario'].mean() if 'salario' in self.df.columns else 0
            max_salary = self.df['salario'].max() if 'salario' in self.df.columns else 0
            min_salary = self.df['salario'].min() if 'salario' in self.df.columns else 0
            
            # Formata os dados
            formatted_data = f"""
            Estatísticas da folha de pagamento:
            - Total de funcionários: {total_employees}
            - Soma total dos salários: R$ {total_salary:,.2f}
            - Salário médio: R$ {avg_salary:,.2f}
            - Maior salário: R$ {max_salary:,.2f}
            - Menor salário: R$ {min_salary:,.2f}
            """
            
            return {
                "data": formatted_data,
                "evidence": f"Baseado em {total_employees} funcionários",
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Erro na consulta agregada: {e}")
            return {
                "data": f"Erro ao calcular estatísticas: {str(e)}",
                "evidence": "",
                "success": False
            }
    
    async def _query_filter(self, question: str) -> Dict[str, Any]:
        """
        Consulta com filtros
        
        Args:
            question: Pergunta do usuário
        
        Returns:
            Dados filtrados
        """
        try:
            # Aplica filtros baseados na pergunta
            filtered_df = self.df.copy()
            
            # Filtro por departamento
            if "departamento" in question.lower():
                dept = self._extract_department(question)
                if dept:
                    filtered_df = filtered_df[filtered_df['departamento'].str.contains(dept, case=False, na=False)]
            
            # Filtro por cargo
            if "cargo" in question.lower():
                position = self._extract_position(question)
                if position:
                    filtered_df = filtered_df[filtered_df['cargo'].str.contains(position, case=False, na=False)]
            
            if filtered_df.empty:
                return {
                    "data": "Nenhum funcionário encontrado com os filtros aplicados",
                    "evidence": "",
                    "success": False
                }
            
            # Formata os dados
            formatted_data = self._format_filtered_data(filtered_df)
            
            return {
                "data": formatted_data,
                "evidence": f"Baseado em {len(filtered_df)} funcionários filtrados",
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Erro na consulta com filtros: {e}")
            return {
                "data": f"Erro ao aplicar filtros: {str(e)}",
                "evidence": "",
                "success": False
            }
    
    async def _query_general(self, question: str) -> Dict[str, Any]:
        """
        Consulta geral
        
        Args:
            question: Pergunta do usuário
        
        Returns:
            Dados gerais
        """
        try:
            # Retorna informações gerais sobre o dataset
            total_employees = len(self.df)
            columns = list(self.df.columns)
            
            formatted_data = f"""
            Informações gerais do dataset:
            - Total de funcionários: {total_employees}
            - Colunas disponíveis: {', '.join(columns)}
            - Período dos dados: {self.df['data'].min() if 'data' in self.df.columns else 'N/A'} a {self.df['data'].max() if 'data' in self.df.columns else 'N/A'}
            """
            
            return {
                "data": formatted_data,
                "evidence": f"Baseado em {total_employees} registros",
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Erro na consulta geral: {e}")
            return {
                "data": f"Erro ao processar consulta: {str(e)}",
                "evidence": "",
                "success": False
            }
    
    def _extract_employee_name(self, question: str) -> Optional[str]:
        """Extrai nome do funcionário da pergunta"""
        # Implementação simples - pode ser melhorada com NLP
        words = question.split()
        for i, word in enumerate(words):
            if word.lower() in ["funcionário", "funcionarios", "nome"]:
                if i + 1 < len(words):
                    return words[i + 1]
        return None
    
    def _extract_department(self, question: str) -> Optional[str]:
        """Extrai departamento da pergunta"""
        # Implementação simples
        words = question.split()
        for i, word in enumerate(words):
            if word.lower() == "departamento":
                if i + 1 < len(words):
                    return words[i + 1]
        return None
    
    def _extract_position(self, question: str) -> Optional[str]:
        """Extrai cargo da pergunta"""
        # Implementação simples
        words = question.split()
        for i, word in enumerate(words):
            if word.lower() == "cargo":
                if i + 1 < len(words):
                    return words[i + 1]
        return None
    
    def _format_employee_data(self, employee_data: pd.DataFrame) -> str:
        """Formata dados do funcionário"""
        if employee_data.empty:
            return "Nenhum funcionário encontrado"
        
        result = []
        for _, row in employee_data.iterrows():
            employee_info = f"""
            Funcionário: {row.get('nome', 'N/A')}
            Cargo: {row.get('cargo', 'N/A')}
            Departamento: {row.get('departamento', 'N/A')}
            Salário: R$ {row.get('salario', 0):,.2f}
            Data: {row.get('data', 'N/A')}
            """
            result.append(employee_info)
        
        return "\n".join(result)
    
    def _format_filtered_data(self, filtered_df: pd.DataFrame) -> str:
        """Formata dados filtrados"""
        if filtered_df.empty:
            return "Nenhum funcionário encontrado"
        
        result = []
        for _, row in filtered_df.iterrows():
            employee_info = f"""
            {row.get('nome', 'N/A')} - {row.get('cargo', 'N/A')} - R$ {row.get('salario', 0):,.2f}
            """
            result.append(employee_info)
        
        return "\n".join(result)
