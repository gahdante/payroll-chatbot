"""
Implementa a busca na web (via Google Search API, por exemplo)
"""
import os
import requests
import logging
from typing import Dict, Any, List, Optional
import json

logger = logging.getLogger(__name__)

class WebSearch:
    """Sistema de busca na web para questões de legislação trabalhista"""
    
    def __init__(self):
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.base_url = "https://www.googleapis.com/customsearch/v1"
        
        # Fallback para busca simples se não tiver API key
        self.use_fallback = not (self.api_key and self.search_engine_id)
    
    async def search(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """
        Realiza busca na web
        
        Args:
            query: Consulta de busca
            num_results: Número de resultados desejados
        
        Returns:
            Dicionário com resultados e evidência
        """
        try:
            if self.use_fallback:
                return await self._fallback_search(query, num_results)
            else:
                return await self._google_search(query, num_results)
                
        except Exception as e:
            logger.error(f"Erro na busca web: {e}")
            return {
                "results": [],
                "evidence": f"Erro na busca: {str(e)}",
                "success": False
            }
    
    async def _google_search(self, query: str, num_results: int) -> Dict[str, Any]:
        """
        Busca usando Google Custom Search API
        
        Args:
            query: Consulta de busca
            num_results: Número de resultados
        
        Returns:
            Resultados da busca
        """
        try:
            # Adiciona termos específicos para legislação trabalhista
            enhanced_query = f"{query} legislação trabalhista brasileira CLT"
            
            params = {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": enhanced_query,
                "num": min(num_results, 10),  # Google limita a 10
                "lr": "lang_pt",  # Busca em português
                "safe": "medium"
            }
            
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if "items" not in data:
                return {
                    "results": [],
                    "evidence": "Nenhum resultado encontrado",
                    "success": False
                }
            
            # Formata os resultados
            results = []
            for item in data["items"]:
                result = {
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "display_link": item.get("displayLink", "")
                }
                results.append(result)
            
            return {
                "results": results,
                "evidence": f"Baseado em {len(results)} resultados da web",
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Erro na busca Google: {e}")
            return {
                "results": [],
                "evidence": f"Erro na busca Google: {str(e)}",
                "success": False
            }
    
    async def _fallback_search(self, query: str, num_results: int) -> Dict[str, Any]:
        """
        Busca de fallback quando não há API key
        
        Args:
            query: Consulta de busca
            num_results: Número de resultados
        
        Returns:
            Resultados simulados
        """
        # Simula resultados para demonstração
        mock_results = [
            {
                "title": "Consolidação das Leis do Trabalho (CLT)",
                "link": "https://www.gov.br/trabalho-e-emprego/pt-br",
                "snippet": "A CLT é a principal legislação trabalhista brasileira, regulamentando as relações de trabalho.",
                "display_link": "gov.br"
            },
            {
                "title": "Direitos Trabalhistas - Ministério do Trabalho",
                "link": "https://www.gov.br/trabalho-e-emprego/pt-br/assuntos/direitos-trabalhistas",
                "snippet": "Informações sobre direitos trabalhistas, férias, 13º salário, FGTS e outros benefícios.",
                "display_link": "gov.br"
            },
            {
                "title": "Cálculo de Férias - Guia Completo",
                "link": "https://www.trabalhador.gov.br/ferias",
                "snippet": "Como calcular férias proporcionais, 1/3 constitucional e outros aspectos legais.",
                "display_link": "trabalhador.gov.br"
            }
        ]
        
        return {
            "results": mock_results[:num_results],
            "evidence": "Resultados simulados para demonstração (API key não configurada)",
            "success": True
        }
    
    def _enhance_query_for_workplace(self, query: str) -> str:
        """
        Enriquece a consulta com termos específicos de legislação trabalhista
        
        Args:
            query: Consulta original
        
        Returns:
            Consulta enriquecida
        """
        workplace_terms = [
            "legislação trabalhista",
            "CLT",
            "direitos trabalhistas",
            "lei trabalhista",
            "Brasil"
        ]
        
        # Adiciona termos relevantes se não estiverem presentes
        query_lower = query.lower()
        for term in workplace_terms:
            if term not in query_lower:
                query += f" {term}"
                break
        
        return query
    
    def _filter_workplace_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filtra resultados para manter apenas os relevantes para legislação trabalhista
        
        Args:
            results: Lista de resultados
        
        Returns:
            Resultados filtrados
        """
        workplace_keywords = [
            "trabalho", "trabalhista", "clt", "lei", "direito", "funcionário",
            "salário", "férias", "fgts", "inss", "tributo", "encargo"
        ]
        
        filtered_results = []
        for result in results:
            title_snippet = f"{result.get('title', '')} {result.get('snippet', '')}".lower()
            
            # Verifica se contém palavras-chave relevantes
            if any(keyword in title_snippet for keyword in workplace_keywords):
                filtered_results.append(result)
        
        return filtered_results
