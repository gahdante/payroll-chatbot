"""
Sistema de busca na web para consultas de legislação trabalhista
"""
import os
import requests
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class WebSearch:
    """Sistema de busca na web para legislação trabalhista"""
    
    def __init__(self):
        """Inicializa o sistema de busca"""
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.use_fallback = not (self.api_key and self.search_engine_id)
        
        # Dados de fallback para demonstração
        self.fallback_data = {
            "selic": {
                "title": "Taxa Selic Atual - Banco Central do Brasil",
                "url": "https://www.bcb.gov.br/controleinflacao/historicotaxasjuros",
                "snippet": "A Taxa Selic é a taxa básica de juros da economia brasileira.",
                "relevance_score": 0.95
            },
            "ferias": {
                "title": "Férias Proporcionais - CLT Art. 130",
                "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
                "snippet": "As férias proporcionais são devidas ao empregado que não completou 12 meses de trabalho.",
                "relevance_score": 0.90
            }
        }
    
    async def search(self, query: str) -> Dict[str, Any]:
        """Executa busca na web"""
        try:
            if self.use_fallback:
                return await self._fallback_search(query)
            else:
                return await self._google_search(query)
        except Exception as e:
            logger.error(f"Erro na busca: {e}")
            return await self._fallback_search(query)
    
    async def _google_search(self, query: str) -> Dict[str, Any]:
        """Executa busca usando Google Custom Search API"""
        try:
            base_url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "q": query,
                "num": 10,
                "lr": "lang_pt"
            }
            
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            results = []
            if "items" in data:
                for item in data["items"]:
                    result = {
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "date": item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time", "")
                    }
                    results.append(result)
            
            return {
                "success": True,
                "results": results[:5],
                "query": query,
                "total_results": len(results)
            }
            
        except Exception as e:
            logger.error(f"Erro na busca Google: {e}")
            return await self._fallback_search(query)
    
    async def _fallback_search(self, query: str) -> Dict[str, Any]:
        """Busca de fallback com dados pré-definidos"""
        query_lower = query.lower()
        
        if "selic" in query_lower:
            result = self.fallback_data["selic"]
        elif "férias" in query_lower or "ferias" in query_lower:
            result = self.fallback_data["ferias"]
        else:
            result = {
                "title": "Legislação Trabalhista - CLT",
                "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
                "snippet": "A Consolidação das Leis do Trabalho (CLT) é o conjunto de normas que regulam as relações individuais e coletivas de trabalho no Brasil.",
                "relevance_score": 0.8
            }
        
        return {
            "success": True,
            "results": [result],
            "query": query,
            "total_results": 1
        }
    
    async def search_with_citation(self, query: str) -> Dict[str, Any]:
        """Executa busca com citação de fontes"""
        search_result = await self.search(query)
        
        if not search_result["success"]:
            return search_result
        
        return {
            "success": True,
            "data": f"Resultado da busca: {search_result['results'][0]['title']}",
            "evidence": search_result["results"],
            "query": query
        }
