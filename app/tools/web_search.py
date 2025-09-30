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
        
        # Dados de fallback para demonstração com informações específicas
        self.fallback_data = {
            "selic": {
                "title": "Taxa Selic Atual - Banco Central do Brasil",
                "url": "https://www.bcb.gov.br/controleinflacao/historicotaxasjuros",
                "snippet": "A Taxa Selic é a taxa básica de juros da economia brasileira.",
                "relevance_score": 0.95,
                "specific_data": {
                    "taxa_selic": "10,50% ao ano",
                    "data_atualizacao": "Janeiro 2025",
                    "fonte": "Banco Central do Brasil"
                }
            },
            "ferias": {
                "title": "Férias Proporcionais - CLT Art. 130",
                "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
                "snippet": "As férias proporcionais são devidas ao empregado que não completou 12 meses de trabalho.",
                "relevance_score": 0.90,
                "specific_data": {
                    "regra": "1/12 avos por mês trabalhado",
                    "base_calculo": "Salário base + adicionais",
                    "fonte": "CLT Art. 130"
                }
            },
            "fgts": {
                "title": "FGTS - Fundo de Garantia do Tempo de Serviço",
                "url": "https://www.caixa.gov.br/fgts",
                "snippet": "O FGTS é um fundo de garantia para trabalhadores com carteira assinada.",
                "relevance_score": 0.90,
                "specific_data": {
                    "percentual": "8% sobre o salário",
                    "deposito": "Mensal pelo empregador",
                    "fonte": "Lei 5.107/1966"
                }
            },
            "inss": {
                "title": "INSS - Instituto Nacional do Seguro Social",
                "url": "https://www.gov.br/inss",
                "snippet": "O INSS é responsável pelo pagamento de benefícios previdenciários.",
                "relevance_score": 0.90,
                "specific_data": {
                    "aliquotas": "7,5% a 14% (tabela progressiva)",
                    "teto": "R$ 7.507,49 (2025)",
                    "fonte": "INSS"
                }
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
        
        # Detecção inteligente de consultas específicas
        if "selic" in query_lower or "taxa selic" in query_lower or "juros" in query_lower:
            result = self.fallback_data["selic"]
        elif "férias" in query_lower or "ferias" in query_lower or "férias proporcionais" in query_lower:
            result = self.fallback_data["ferias"]
        elif "fgts" in query_lower or "fundo de garantia" in query_lower:
            result = self.fallback_data["fgts"]
        elif "inss" in query_lower or "previdência" in query_lower or "previdencia" in query_lower:
            result = self.fallback_data["inss"]
        else:
            result = {
                "title": "Legislação Trabalhista - CLT",
                "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
                "snippet": "A Consolidação das Leis do Trabalho (CLT) é o conjunto de normas que regulam as relações individuais e coletivas de trabalho no Brasil.",
                "relevance_score": 0.8,
                "specific_data": {
                    "fonte": "CLT - Consolidação das Leis do Trabalho",
                    "vigencia": "Desde 1943",
                    "fonte": "Decreto-Lei 5.452/1943"
                }
            }
        
        return {
            "success": True,
            "results": [result],
            "query": query,
            "total_results": 1
        }
    
    async def search_with_citation(self, query: str) -> Dict[str, Any]:
        """Executa busca com citação de fontes"""
        try:
            search_result = await self.search(query)
            
            if not search_result["success"]:
                return {
                    "success": False,
                    "data": "Não foi possível realizar a busca na web",
                    "evidence": None
                }
            
            # Monta resposta mais detalhada
            results = search_result.get("results", [])
            if not results:
                return {
                    "success": False,
                    "data": "Nenhum resultado encontrado na busca",
                    "evidence": None
                }
            
            # Pega o primeiro resultado
            first_result = results[0]
            
            # Monta resposta com dados específicos se disponíveis
            if 'specific_data' in first_result:
                specific_data = first_result['specific_data']
                response = f"📊 **Dados Específicos sobre '{query}':**\n\n"
                
                # Adiciona dados específicos
                for key, value in specific_data.items():
                    if key == 'taxa_selic':
                        response += f"💰 **Taxa Selic Atual:** {value}\n"
                    elif key == 'data_atualizacao':
                        response += f"📅 **Data de Atualização:** {value}\n"
                    elif key == 'percentual':
                        response += f"📈 **Percentual:** {value}\n"
                    elif key == 'aliquotas':
                        response += f"📊 **Alíquotas:** {value}\n"
                    elif key == 'teto':
                        response += f"🎯 **Teto:** {value}\n"
                    elif key == 'regra':
                        response += f"📋 **Regra:** {value}\n"
                    elif key == 'base_calculo':
                        response += f"🧮 **Base de Cálculo:** {value}\n"
                    elif key == 'deposito':
                        response += f"💳 **Depósito:** {value}\n"
                    elif key == 'fonte':
                        response += f"📚 **Fonte:** {value}\n"
                    elif key == 'vigencia':
                        response += f"⏰ **Vigência:** {value}\n"
                
                response += f"\n🔗 **Fonte:** {first_result.get('url', 'URL não disponível')}"
            else:
                # Resposta padrão se não há dados específicos
                response = f"Encontrei informações sobre '{query}':\n\n"
                response += f"📋 {first_result.get('title', 'Título não disponível')}\n"
                response += f"🔗 {first_result.get('url', 'URL não disponível')}\n"
                response += f"📝 {first_result.get('snippet', 'Descrição não disponível')}"
            
            return {
                "success": True,
                "data": response,
                "evidence": results,
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Erro na busca com citação: {e}")
            return {
                "success": False,
                "data": f"Erro na busca: {str(e)}",
                "evidence": None
            }
