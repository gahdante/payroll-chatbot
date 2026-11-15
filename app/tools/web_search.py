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
from typing import Any

import httpx

from ..utils.text import contains_any

logger = logging.getLogger(__name__)

# Rede/status HTTP, JSON inválido, resposta sem o formato esperado, valor não numérico.
_BCB_ERRORS = (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, ArithmeticError)

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

# Base de referência local. Cada tema casa por palavra inteira, sem acento e sem
# diferenciar maiúsculas (ver utils.text). Vale o primeiro tema que casar, então
# os mais específicos vêm antes. Só regras estáveis: valores que mudam todo ano
# (salário mínimo, faixas de IRRF e INSS) ficam para a fonte oficial citada.
_REFERENCE = [
    (
        ("selic", "taxa basica", "taxa de juros"),
        {
            "title": "Taxa Selic — Banco Central do Brasil",
            "url": "https://www.bcb.gov.br/controleinflacao/taxaselic",
            "snippet": "A Selic é a taxa básica de juros da economia brasileira, definida pelo Copom.",
            "reference": "Banco Central do Brasil (Copom)",
            "detail": "O valor vigente muda a cada reunião do Copom; consulte o site do BC para a taxa atual.",
        },
    ),
    (
        ("aviso previo",),
        {
            "title": "Aviso prévio — CLT e Lei nº 12.506/2011",
            "url": "https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2011/lei/l12506.htm",
            "snippet": "O aviso prévio é de 30 dias para até 1 ano de serviço na mesma empresa, com mais 3 dias por ano completo, até o máximo de 90 dias.",
            "reference": "CLT, art. 487, e Lei nº 12.506/2011",
            "detail": "No aviso trabalhado dado pelo empregador, o empregado pode reduzir a jornada em 2 horas por dia ou faltar 7 dias corridos, sem desconto no salário (CLT, art. 488).",
        },
    ),
    (
        ("ferias",),
        {
            "title": "Férias — CLT, arts. 129 a 145",
            "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
            "snippet": "Férias proporcionais correspondem a 1/12 por mês trabalhado (ou fração superior a 14 dias).",
            "reference": "CLT, arts. 130 e 146",
            "detail": "Sobre a remuneração de férias incide o adicional de 1/3 (CF, art. 7º, XVII).",
        },
    ),
    (
        (
            "rescisao",
            "rescisoria",
            "rescisorias",
            "demissao",
            "dispensa",
            "justa causa",
        ),
        {
            "title": "Rescisão do contrato de trabalho — CLT, art. 477",
            "url": "https://www.planalto.gov.br/ccivil_03/decreto-lei/del5452.htm",
            "snippet": "As verbas rescisórias devem ser pagas em até 10 dias contados do término do contrato.",
            "reference": "CLT, art. 477, § 6º",
            "detail": "Na dispensa sem justa causa, o empregador também deposita multa de 40% sobre o saldo do FGTS (Lei nº 8.036/1990, art. 18, § 1º).",
        },
    ),
    (
        ("salario minimo",),
        {
            "title": "Salário mínimo — Constituição Federal, art. 7º, IV",
            "url": "https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm",
            "snippet": "A Constituição garante um salário mínimo fixado em lei e nacionalmente unificado.",
            "reference": "Constituição Federal, art. 7º, IV",
            "detail": "O valor é reajustado todo ano, e alguns estados têm pisos regionais maiores (Lei Complementar nº 103/2000). Confirme o valor vigente em fonte oficial.",
        },
    ),
    (
        ("irrf", "imposto de renda"),
        {
            "title": "IRRF sobre salários — tabela progressiva mensal",
            "url": "https://www.gov.br/receitafederal/pt-br",
            "snippet": "O imposto de renda retido na fonte sobre salários segue a tabela progressiva mensal, com alíquotas que sobem por faixa de renda.",
            "reference": "Lei nº 7.713/1988 e tabela progressiva vigente (Receita Federal)",
            "detail": "Da base de cálculo saem a contribuição ao INSS e o valor por dependente (ou o desconto simplificado mensal). As faixas mudam por lei; confirme a tabela vigente no site da Receita Federal.",
        },
    ),
    (
        ("fgts", "fundo de garantia"),
        {
            "title": "FGTS — Fundo de Garantia do Tempo de Serviço",
            "url": "https://www.gov.br/fgts",
            "snippet": "O empregador deposita mensalmente 8% da remuneração do empregado em conta vinculada do FGTS.",
            "reference": "Lei nº 8.036/1990",
            "detail": "No contrato de aprendizagem a alíquota é de 2%.",
        },
    ),
    (
        ("inss", "previdencia", "contribuicao previdenciaria"),
        {
            "title": "Contribuição ao INSS — tabela progressiva",
            "url": "https://www.gov.br/inss",
            "snippet": "O desconto previdenciário do empregado segue alíquotas progressivas de 7,5% a 14% sobre o salário de contribuição.",
            "reference": "Lei nº 8.212/1991 e portaria interministerial anual",
            "detail": "Há um teto do salário de contribuição, reajustado todo ano.",
        },
    ),
    (
        ("13o", "decimo terceiro", "gratificacao natalina"),
        {
            "title": "13º salário (gratificação natalina)",
            "url": "https://www.planalto.gov.br/ccivil_03/leis/l4090.htm",
            "snippet": "O 13º equivale a 1/12 da remuneração por mês trabalhado no ano, pago em duas parcelas.",
            "reference": "Lei nº 4.090/1962 e Lei nº 4.749/1965",
            "detail": "A 1ª parcela vai até 30/11 e a 2ª até 20/12.",
        },
    ),
]


class WebSearch:
    """Busca na web (Google CSE) com fallback para base de referência local."""

    GOOGLE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"
    BCB_SELIC_SERIES = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados"
    BCB_SELIC_PAGE = "https://www.bcb.gov.br/controleinflacao/taxaselic"

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.api_key = os.getenv("GOOGLE_API_KEY")
        self.search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        self.use_fallback = not (self.api_key and self.search_engine_id)
        if self.use_fallback:
            logger.info("Busca web sem Google CSE: usando a base de referência local.")
        self._transport = transport  # injetável nos testes (httpx.MockTransport)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=10.0, transport=self._transport)

    async def search(self, query: str) -> dict[str, Any]:
        if self.use_fallback:
            return self._reference_search(query)
        try:
            return await self._google_search(query)
        except (httpx.HTTPError, ValueError) as exc:  # rede, status HTTP ou JSON inválido
            logger.warning("Busca Google falhou (%s); usando base de referência.", exc)
            return self._reference_search(query)

    async def _google_search(self, query: str) -> dict[str, Any]:
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

    def _reference_search(self, query: str) -> dict[str, Any]:
        chosen = next(
            (entry for keys, entry in _REFERENCE if contains_any(query, keys)), _CLT_ENTRY
        )
        return {"success": True, "results": [chosen], "query": query, "fallback": True}

    async def _selic_bcb(self, today: date | None = None) -> dict[str, Any]:
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
            "sources": [
                {
                    "title": "Banco Central do Brasil — Meta Selic (SGS, série 432)",
                    "url": self.BCB_SELIC_PAGE,
                    "snippet": f"Meta Selic de {rate}% a.a. em {day}.",
                }
            ],
            "query_type": "web",
        }
        return {"success": True, "data": data, "evidence": evidence}

    async def search_with_citation(self, query: str) -> dict[str, Any]:
        if contains_any(query, ("selic",)):
            try:
                return await self._selic_bcb()
            except _BCB_ERRORS as exc:
                logger.warning("Consulta da Selic no BCB falhou (%s); seguindo com a busca.", exc)

        result = await self.search(query)  # já cai na base local se a busca falhar
        results: list[dict[str, Any]] = result.get("results", [])
        if not result.get("success") or not results:
            return {
                "success": False,
                "data": "Nenhum resultado encontrado na busca.",
                "evidence": None,
            }

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
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("snippet", ""),
                }
                for r in results
            ],
            "query_type": "web",
        }
        out: dict[str, Any] = {"success": True, "data": data, "evidence": evidence}
        if result.get("fallback"):
            out["note"] = _FALLBACK_NOTE
        return out
