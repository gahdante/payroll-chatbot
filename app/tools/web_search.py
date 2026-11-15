"""Busca na web para dúvidas de legislação trabalhista.

- Selic: consulta ao vivo a série 432 (meta Selic) da API pública do Banco
  Central, que não exige chave.
- Demais temas: Google Custom Search API quando ``GOOGLE_API_KEY`` e
  ``GOOGLE_SEARCH_ENGINE_ID`` estão configurados. Atenção: essa API não aceita
  novos clientes e será desligada pelo Google em 01/01/2027.
- Sem busca ao vivo, cai em uma base de referência local, e a resposta avisa
  que o dado pode estar desatualizado.
"""
import logging
import os
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx

from ..utils.text import contains_any

logger = logging.getLogger(__name__)

_FALLBACK_NOTE = (
    "Resposta baseada em uma base de referência local e que pode estar desatualizada. "
    "Confirme na fonte oficial citada."
)

_CLT_ENTRY = {
    "title": "Consolidação das Leis do Trabalho (CLT)",
    "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
    "snippet": "A CLT (Decreto-Lei 5.452/1943) reúne as normas que regulam as relações de trabalho no Brasil.",
    "reference": "Decreto-Lei nº 5.452/1943",
}

_REFERENCE = [
    (("selic", "taxa básica", "taxa basica", "taxa de juros"), {
        "title": "Taxa Selic — Banco Central do Brasil",
        "url": "https://www.bcb.gov.br/controleinflacao/taxaselic",
        "snippet": "A Selic é a taxa básica de juros da economia brasileira, definida pelo Copom.",
        "reference": "Banco Central do Brasil (Copom)",
        "detail": "O valor vigente muda a cada reunião do Copom; consulte o site do BC para a taxa atual.",
    }),
    (("férias", "ferias"), {
        "title": "Férias — CLT, arts. 129 a 145",
        "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
        "snippet": "Férias proporcionais correspondem a 1/12 por mês trabalhado (ou fração superior a 14 dias).",
        "reference": "CLT, arts. 130 e 146",
        "detail": "Sobre a remuneração de férias incide o adicional de 1/3 (CF, art. 7º, XVII).",
    }),
    (("fgts", "fundo de garantia"), {
        "title": "FGTS — Fundo de Garantia do Tempo de Serviço",
        "url": "https://www.gov.br/fgts",
        "snippet": "O empregador deposita mensalmente 8% da remuneração do empregado em conta vinculada do FGTS.",
        "reference": "Lei nº 8.036/1990",
        "detail": "No contrato de aprendizagem a alíquota é de 2%.",
    }),
    (("inss", "previdência", "previdencia", "contribuição previdenciária"), {
        "title": "Contribuição ao INSS — tabela progressiva",
        "url": "https://www.gov.br/inss",
        "snippet": "O desconto previdenciário do empregado segue alíquotas progressivas de 7,5% a 14% sobre o salário de contribuição.",
        "reference": "Lei nº 8.212/1991 e portaria interministerial anual",
        "detail": "Há um teto do salário de contribuição, reajustado todo ano.",
    }),
    (("13º", "13o", "décimo terceiro", "decimo terceiro", "gratificação natalina"), {
        "title": "13º salário (gratificação natalina)",
        "url": "https://www.planalto.gov.br/ccivil_03/leis/l4090.htm",
        "snippet": "O 13º equivale a 1/12 da remuneração por mês trabalhado no ano, pago em duas parcelas.",
        "reference": "Lei nº 4.090/1962 e Lei nº 4.749/1965",
        "detail": "A 1ª parcela vai até 30/11 e a 2ª até 20/12.",
    }),
]


class WebSearch:
    """Busca na web (Google CSE) com fallback para base de referência local."""

    GOOGLE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
    BCB_SELIC_SERIES = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"
    BCB_SELIC_PAGE = "https://www.bcb.gov.br/controleinflacao/taxaselic"

    def __init__(self, transport: Optional[httpx.AsyncBaseTransport] = None) -> None:
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.use_fallback = not (self.api_key and self.search_engine_id)
        if self.use_fallback:
            logger.info("Busca web sem Google CSE: usando a base de referência local.")
        self._transport = transport  # injetável nos testes (httpx.MockTransport)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=10.0, transport=self._transport)

    async def search(self, query: str) -> Dict[str, Any]:
        if self.use_fallback:
            return self._reference_search(query)
        try:
            return await self._google_search(query)
        except Exception as exc:
            logger.warning("Busca Google falhou (%s); usando base de referência.", exc)
            return self._reference_search(query)

    async def _google_search(self, query: str) -> Dict[str, Any]:
        params = {
            "key": self.api_key,
            "cx": self.search_engine_id,
            "q": query,
            "num": 5,
            "lr": "lang_pt",
        }
        async with self._client() as client:
            resp = await client.get(self.GOOGLE_ENDPOINT, params=params)
            resp.raise_for_status()
            payload = resp.json()

        results = [
            {
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
            for item in payload.get("items", [])
        ]
        return {"success": bool(results), "results": results, "query": query, "fallback": False}

    def _reference_search(self, query: str) -> Dict[str, Any]:
        q = query.lower()
        chosen = next((entry for keys, entry in _REFERENCE if any(k in q for k in keys)), _CLT_ENTRY)
        return {"success": True, "results": [chosen], "query": query, "fallback": True}

    async def _selic_bcb(self, today: Optional[date] = None) -> Dict[str, Any]:
        """Meta Selic vigente, direto da série 432 do SGS/Banco Central.

        Consulta por intervalo até hoje: ``ultimos/1`` devolve a data da próxima
        reunião do Copom, que fica no futuro.
        """
        today = today or date.today()
        params = {
            "formato": "json",
            "dataInicial": (today - timedelta(days=30)).strftime("%d/%m/%Y"),
            "dataFinal": today.strftime("%d/%m/%Y"),
        }
        async with self._client() as client:
            resp = await client.get(self.BCB_SELIC_SERIES, params=params)
            resp.raise_for_status()
            series = resp.json()

        latest = series[-1]
        rate = f"{Decimal(latest['valor']):.2f}".replace(".", ",")
        day = latest["data"]
        data = (
            f"Taxa Selic (meta definida pelo Copom): {rate}% ao ano, em vigor em {day}.\n\n"
            f"Fonte: Banco Central do Brasil — SGS, série 432 ({self.BCB_SELIC_PAGE})"
        )
        evidence = {
            "sources": [{
                "title": "Banco Central do Brasil — Meta Selic (SGS, série 432)",
                "url": self.BCB_SELIC_PAGE,
                "snippet": f"Meta Selic de {rate}% a.a. em {day}.",
            }],
            "query_type": "web",
        }
        return {"success": True, "data": data, "evidence": evidence}

    async def search_with_citation(self, query: str) -> Dict[str, Any]:
        if contains_any(query, ("selic",)):
            try:
                return await self._selic_bcb()
            except Exception as exc:
                logger.warning("Consulta da Selic no BCB falhou (%s); seguindo com a busca.", exc)

        try:
            result = await self.search(query)
        except Exception as exc:
            logger.error("Erro na busca web: %s", exc)
            return {"success": False, "data": "Não foi possível realizar a busca na web.", "evidence": None}

        results: List[Dict[str, Any]] = result.get("results", [])
        if not result.get("success") or not results:
            return {"success": False, "data": "Nenhum resultado encontrado na busca.", "evidence": None}

        top = results[0]
        lines = [f'Sobre "{query}":', "", top.get("snippet", "")]
        if top.get("reference"):
            lines.append(f"Base legal: {top['reference']}")
        if top.get("detail"):
            lines.append(top["detail"])
        lines += ["", f"Fonte: {top.get('url', 'sem URL')}"]
        data = "\n".join(line for line in lines if line is not None)

        evidence = {
            "sources": [
                {"title": r.get("title", ""), "url": r.get("url", ""), "snippet": r.get("snippet", "")}
                for r in results
            ],
            "query_type": "web",
        }
        out: Dict[str, Any] = {"success": True, "data": data, "evidence": evidence}
        if result.get("fallback"):
            out["note"] = _FALLBACK_NOTE
        return out
