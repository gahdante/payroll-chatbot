"""RAG de folha de pagamento.

Consultas determinísticas sobre o CSV da folha. A camada de LLM (no agente)
não altera os números produzidos aqui: valores, datas e fontes saem prontos.

Cada pergunta vira um ``QueryParams`` (funcionário, competência, período,
métrica, maior/menor, total). Perguntas de seguimento ("E em junho?") são
completadas com os parâmetros do turno anterior via ``QueryParams.follow_up_of``.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from re import Pattern
from typing import Any, NamedTuple

import pandas as pd

from ..utils.formatting import format_competency, format_currency, format_date
from ..utils.text import contains_any, normalize

logger = logging.getLogger(__name__)

_DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "payroll.csv"

# Os padrões abaixo rodam sobre texto normalizado (minúsculo e sem acentos).
_MONTH_NAMES = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
    "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}
_MONTH_ABBR = {name[:3]: number for name, number in _MONTH_NAMES.items()}
# Nome completo do mês: o ano é opcional (sem ano, vale o mais recente dos dados).
_FULL_MONTH_RE = re.compile(rf"\b({'|'.join(_MONTH_NAMES)})\b")
# Abreviação ("jun/2025", "jun 2025"): exige o ano junto, porque "dez", "set",
# "mar" e "out" também são palavras comuns.
_ABBR_MONTH_RE = re.compile(
    rf"\b({'|'.join(_MONTH_ABBR)})\.?\s*(?:/|-|de\s+)?\s*(20\d{{2}})\b"
)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")
_ORDINALS = {
    "primeiro": 1, "segundo": 2, "terceiro": 3, "quarto": 4,
    "1": 1, "2": 2, "3": 3, "4": 4,
}
_PERIOD_RE = re.compile(
    r"\b(primeiro|segundo|terceiro|quarto|[1-4])\s*(?:o|°|\.)?\s*(trimestre|semestre)\b"
)
_LATEST_PERIOD_RE = re.compile(r"\b(?:ultimo|mais recente)\s+(trimestre|semestre)\b")
_PERIOD_WORD_RE = re.compile(r"\b(trimestre|semestre)\b")

_NAMED_PERIODS = {
    frozenset({"01", "02", "03"}): "1º trimestre",
    frozenset({"04", "05", "06"}): "2º trimestre",
    frozenset({"07", "08", "09"}): "3º trimestre",
    frozenset({"10", "11", "12"}): "4º trimestre",
    frozenset({f"{m:02d}" for m in range(1, 7)}): "1º semestre",
    frozenset({f"{m:02d}" for m in range(7, 13)}): "2º semestre",
    frozenset({f"{m:02d}" for m in range(1, 13)}): "ano",
}

_AGGREGATE_TERMS = ("total", "soma", "somar", "somado", "media", "medio", "acumulado")
_MAX_TERMS = ("maior", "mais alto", "mais alta", "maximo", "maxima")
_MIN_TERMS = ("menor", "mais baixo", "mais baixa", "minimo", "minima")
_NAME_STOPWORDS = {"da", "de", "do", "das", "dos", "e"}

# Ordem importa: "desconto de INSS" é INSS, não descontos em geral.
_METRIC_TERMS: list[tuple[str, tuple[str, ...]]] = [
    ("inss", ("inss",)),
    ("irrf", ("irrf", "imposto de renda")),
    ("bonus", ("bonus", "bonificacao")),
    ("deductions", ("desconto", "descontos")),
    ("benefits", ("beneficio", "beneficios", "vt", "vr", "vale transporte",
                  "vale refeicao", "vale alimentacao")),
    ("full", ("holerite", "contracheque", "detalhado", "detalhada", "detalhes",
              "detalhamento", "completo", "discriminado")),
    ("base_salary", ("salario base",)),
    ("payment_date", ("quando", "foi pago", "foi paga", "data de pagamento",
                      "data do pagamento")),
    ("net_pay", ("liquido", "recebi", "recebeu", "receber")),
]


class _Metric(NamedTuple):
    column: str
    short: str  # "INSS" -> "• Maio/2025: INSS R$ 880,00"
    noun: str   # "desconto de INSS" -> "O maior desconto de INSS de ..."
    total: str  # "Total de INSS"


_METRICS: dict[str, _Metric] = {
    "net_pay": _Metric("net_pay", "líquido", "salário líquido", "Total líquido"),
    "base_salary": _Metric("base_salary", "salário base", "salário base", "Total de salário base"),
    "bonus": _Metric("bonus", "bônus", "bônus", "Total de bônus"),
    "inss": _Metric("deductions_inss", "INSS", "desconto de INSS", "Total de INSS"),
    "irrf": _Metric("deductions_irrf", "IRRF", "desconto de IRRF", "Total de IRRF"),
    "deductions": _Metric("total_deductions", "descontos", "total de descontos", "Total de descontos"),
    "benefits": _Metric("benefits_vt_vr", "benefícios", "valor de benefícios (VT/VR)",
                        "Total de benefícios (VT/VR)"),
}

# Linhas extras do registro mensal, além de líquido e data (sempre exibidos).
_RECORD_FIELDS: dict[str, list[tuple[str, str]]] = {
    "inss": [("Desconto de INSS", "deductions_inss")],
    "irrf": [("Desconto de IRRF", "deductions_irrf")],
    "bonus": [("Bônus", "bonus")],
    "base_salary": [("Salário base", "base_salary")],
    "benefits": [("Benefícios (VT/VR)", "benefits_vt_vr")],
    "deductions": [
        ("Desconto de INSS", "deductions_inss"),
        ("Desconto de IRRF", "deductions_irrf"),
        ("Outros descontos", "other_deductions"),
        ("Total de descontos", "total_deductions"),
    ],
    "full": [
        ("Salário base", "base_salary"),
        ("Bônus", "bonus"),
        ("Benefícios (VT/VR)", "benefits_vt_vr"),
        ("Outros proventos", "other_earnings"),
        ("Desconto de INSS", "deductions_inss"),
        ("Desconto de IRRF", "deductions_irrf"),
        ("Outros descontos", "other_deductions"),
    ],
}


class PeriodError(ValueError):
    """Período pedido é ambíguo ou inválido (ex.: "trimestre" sem dizer qual)."""


@dataclass
class QueryParams:
    """O que foi entendido de uma pergunta sobre a folha."""

    name: str | None = None
    candidates: list[str] = field(default_factory=list)  # mais de um funcionário casou
    competency: str | None = None  # "2025-05"
    year_inferred: bool = False  # competência veio sem ano ("em junho")
    period: list[str] | None = None  # competências de um trimestre/semestre/ano
    period_error: str | None = None
    metric: str | None = None  # chave de _METRIC_TERMS; None = não citada
    extreme: str | None = None  # "max" | "min"
    aggregate: bool = False

    def has_signal(self) -> bool:
        """True se a pergunta traz algo que a folha sabe responder."""
        return bool(
            self.name or self.candidates or self.competency or self.period
            or self.period_error or self.metric or self.extreme or self.aggregate
        )

    def follow_up_of(self, prev: QueryParams) -> QueryParams:
        """Completa uma pergunta de seguimento ("E em junho?") com o turno anterior.

        O que a nova pergunta diz explicitamente prevalece; o resto vem de ``prev``.
        """
        if self.competency or self.period or self.period_error:
            competency, period = self.competency, self.period
            if self.competency and self.year_inferred:
                reference = prev.competency or (prev.period[0] if prev.period else None)
                if reference:
                    competency = f"{reference[:4]}{self.competency[4:]}"
        else:
            competency, period = prev.competency, prev.period
        return QueryParams(
            name=self.name or (None if self.candidates else prev.name),
            candidates=list(self.candidates),
            competency=competency,
            period=period,
            period_error=self.period_error,
            metric=self.metric or prev.metric,
            extreme=self.extreme or (None if self.competency else prev.extreme),
            aggregate=self.aggregate or (prev.aggregate and not self.competency),
        )


def _join_pt(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return f"{', '.join(items[:-1])} e {items[-1]}"


class PayrollRAG:
    """Consultas sobre a folha de pagamento a partir de um CSV."""

    def __init__(self, csv_path: str | Path | None = None) -> None:
        self.csv_path = Path(csv_path) if csv_path else _DEFAULT_CSV
        self.df = pd.DataFrame()
        self._full_names: list[tuple[Pattern[str], str]] = []
        self._name_tokens: list[tuple[Pattern[str], set[str]]] = []
        self.ensure_loaded()

    # ----------------------------------------------------------------- loading
    def ensure_loaded(self) -> None:
        if not self.df.empty:
            return
        try:
            df = pd.read_csv(self.csv_path)
            df["competency"] = df["competency"].astype(str)
            df["payment_date"] = df["payment_date"].astype(str)
            df["total_deductions"] = (
                df["deductions_inss"] + df["deductions_irrf"] + df["other_deductions"]
            )
            self.df = df
            self._build_name_lookup()
            logger.info("Folha carregada: %d registros de %s", len(df), self.csv_path)
        except (OSError, ValueError, KeyError) as exc:  # pragma: no cover - depende de I/O
            logger.error("Falha ao carregar %s: %s", self.csv_path, exc)
            self.df = pd.DataFrame()

    def _build_name_lookup(self) -> None:
        full_names: list[tuple[Pattern[str], str]] = []
        tokens: dict[str, set[str]] = {}
        for full in sorted(self.df["name"].dropna().astype(str).unique()):
            key = normalize(full).strip()
            full_names.append((re.compile(rf"\b{re.escape(key)}\b"), full))
            for token in key.split():
                if len(token) >= 3 and token not in _NAME_STOPWORDS:
                    tokens.setdefault(token, set()).add(full)
        self._full_names = full_names
        self._name_tokens = [
            (re.compile(rf"\b{re.escape(token)}\b"), names) for token, names in tokens.items()
        ]

    def _default_year(self) -> int:
        if self.df.empty:
            return 2025
        return int(self.df["competency"].str.slice(0, 4).astype(int).max())

    def _latest_competency(self, year: int | None = None) -> str | None:
        comps = self.df["competency"]
        if year:
            comps = comps[comps.str.startswith(f"{year}-")]
        return None if comps.empty else str(comps.max())

    # -------------------------------------------------------------- extraction
    def _match_employees(self, query: str) -> list[str]:
        """Funcionários citados na pergunta (mais de um = ambíguo)."""
        q = normalize(query)
        full_hits = {full for pattern, full in self._full_names if pattern.search(q)}
        if full_hits:
            return sorted(full_hits)
        hits = [names for pattern, names in self._name_tokens if pattern.search(q)]
        if not hits:
            return []
        # "Ana Maria" com duas Anas: a interseção desempata.
        common = hits[0].intersection(*hits[1:])
        return sorted(common or hits[0].union(*hits[1:]))

    def _extract_employee_name(self, query: str) -> str | None:
        matches = self._match_employees(query)
        return matches[0] if len(matches) == 1 else None

    def _parse_competency(self, query: str) -> tuple[str | None, bool]:
        """Competência citada e se o ano foi inferido (mês sem ano)."""
        q = normalize(query)
        m = re.search(r"\b(20\d{2})-(\d{2})\b", q)
        if m and 1 <= int(m.group(2)) <= 12:
            return f"{m.group(1)}-{m.group(2)}", False
        m = re.search(r"\b(\d{1,2})/(20\d{2})\b", q)
        if m and 1 <= int(m.group(1)) <= 12:
            return f"{m.group(2)}-{int(m.group(1)):02d}", False
        m = _ABBR_MONTH_RE.search(q)
        if m:
            return f"{m.group(2)}-{_MONTH_ABBR[m.group(1)]:02d}", False
        m = _FULL_MONTH_RE.search(q)
        if m:
            month = _MONTH_NAMES[m.group(1)]
            year = _YEAR_RE.search(q)
            if year:
                return f"{year.group(1)}-{month:02d}", False
            return f"{self._default_year()}-{month:02d}", True
        return None, False

    def _extract_competency(self, query: str) -> str | None:
        return self._parse_competency(query)[0]

    def _extract_period(self, query: str) -> list[str] | None:
        """Competências do trimestre/semestre pedido; ``PeriodError`` se ambíguo."""
        q = normalize(query)
        year_match = _YEAR_RE.search(q)
        year = int(year_match.group(1)) if year_match else None

        match = _PERIOD_RE.search(q)
        latest = _LATEST_PERIOD_RE.search(q)
        if match:
            n, kind = _ORDINALS[match.group(1)], match.group(2)
        elif latest:
            kind = latest.group(1)
            last = self._latest_competency(year)
            if last is None:
                raise PeriodError(f"Não há dados de folha de {year}." if year
                                  else "Não há dados de folha carregados.")
            year, month = int(last[:4]), int(last[5:7])
            n = (month - 1) // 3 + 1 if kind == "trimestre" else (1 if month <= 6 else 2)
        elif _PERIOD_WORD_RE.search(q):
            raise PeriodError(
                'Qual trimestre ou semestre? Por exemplo: "1º trimestre de 2025" '
                'ou "último trimestre".'
            )
        else:
            return None

        if kind == "semestre" and n > 2:
            raise PeriodError("O ano tem só dois semestres. Use 1º ou 2º semestre.")
        year = year or self._default_year()
        if kind == "trimestre":
            months = range((n - 1) * 3 + 1, (n - 1) * 3 + 4)
        else:
            months = range(1, 7) if n == 1 else range(7, 13)
        return [f"{year}-{month:02d}" for month in months]

    @staticmethod
    def _detect_metric(query: str) -> str | None:
        for metric, terms in _METRIC_TERMS:
            if contains_any(query, terms):
                return metric
        return None

    def parse(self, query: str) -> QueryParams:
        """Interpreta a pergunta sem consultar valores."""
        q = normalize(query)
        params = QueryParams()

        matches = self._match_employees(query)
        if len(matches) == 1:
            params.name = matches[0]
        elif matches:
            params.candidates = matches

        try:
            params.period = self._extract_period(query)
        except PeriodError as exc:
            params.period_error = str(exc)
        if not params.period and not params.period_error:
            params.competency, params.year_inferred = self._parse_competency(query)
            year = _YEAR_RE.search(q)
            if not params.competency and year:  # "em 2025" = o ano inteiro
                params.period = [f"{year.group(1)}-{m:02d}" for m in range(1, 13)]

        params.metric = self._detect_metric(query)
        if contains_any(q, _MAX_TERMS):
            params.extreme = "max"
        elif contains_any(q, _MIN_TERMS):
            params.extreme = "min"
        params.aggregate = contains_any(q, _AGGREGATE_TERMS) or params.period is not None
        return params

    # ------------------------------------------------------------------ labels
    @staticmethod
    def _metric(metric: str | None) -> _Metric:
        # "full" e "payment_date" não têm valor único para somar/comparar: usa o líquido.
        return _METRICS.get(metric or "net_pay", _METRICS["net_pay"])

    @staticmethod
    def _period_label(competencies: list[str] | None) -> str:
        if not competencies:
            return "todo o período disponível"
        months = sorted(competencies)
        if len(months) == 1:
            return format_competency(months[0])
        year = months[0][:4]
        if all(m[:4] == year for m in months):
            label = _NAMED_PERIODS.get(frozenset(m[5:7] for m in months))
            if label:
                return f"{label} de {year}"
        return f"{format_competency(months[0])} a {format_competency(months[-1])}"

    # ------------------------------------------------------------------ output
    def _build_evidence(self, rows: pd.DataFrame, query_type: str) -> dict[str, Any]:
        sources: list[dict[str, Any]] = []
        for _, r in rows.iterrows():
            sources.append({
                "employee_id": str(r["employee_id"]),
                "name": str(r["name"]),
                "competency": str(r["competency"]),
                "payment_date": str(r["payment_date"]),
                "base_salary": float(r["base_salary"]),
                "bonus": float(r["bonus"]),
                "benefits_vt_vr": float(r["benefits_vt_vr"]),
                "other_earnings": float(r["other_earnings"]),
                "deductions_inss": float(r["deductions_inss"]),
                "deductions_irrf": float(r["deductions_irrf"]),
                "other_deductions": float(r["other_deductions"]),
                "net_pay": float(r["net_pay"]),
            })
        return {
            "sources": sources,
            "employee_ids": sorted({s["employee_id"] for s in sources}),
            "competencies": sorted({s["competency"] for s in sources}),
            "total_records": len(sources),
            "query_type": query_type,
        }

    @staticmethod
    def _fail(message: str) -> dict[str, Any]:
        return {"success": False, "data": message, "evidence": None}

    def _ok(self, data: str, rows: pd.DataFrame, query_type: str) -> dict[str, Any]:
        return {"success": True, "data": data, "evidence": self._build_evidence(rows, query_type)}

    def _rows_for(self, name: str) -> pd.DataFrame:
        return self.df[self.df["name"] == name]

    # ------------------------------------------------------------------- query
    async def query(self, query: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Responde a pergunta. ``context`` são os ``params`` do turno anterior.

        Passe ``context`` só para perguntas de seguimento ("E em junho?"); o
        resultado traz ``params`` para alimentar o próximo turno.
        """
        try:
            self.ensure_loaded()
            if self.df.empty:
                return self._fail("Não consegui carregar os dados da folha de pagamento.")
            if not query or not query.strip():
                return self._fail("Consulta vazia. Diga o que você quer saber sobre a folha.")

            params = self.parse(query)
            if context:
                params = params.follow_up_of(QueryParams(**context))
            result = self._answer(params)
            result["params"] = asdict(params)
            return result
        except Exception:
            logger.exception("Erro ao processar consulta RAG")
            return self._fail("Erro ao consultar a folha de pagamento.")

    def _answer(self, p: QueryParams) -> dict[str, Any]:
        if p.candidates:
            return self._fail(
                f"Encontrei mais de um funcionário na consulta: {_join_pt(p.candidates)}. "
                "Qual deles?"
            )
        if p.period_error:
            return self._fail(p.period_error)
        if p.extreme:
            scope = p.period or ([p.competency] if p.competency else None)
            return self._answer_extreme(p.name, scope, p.metric, is_max=p.extreme == "max")
        if p.aggregate and not p.competency:
            if p.name:
                return self._answer_employee_aggregate(p.name, p.period, p.metric)
            return self._answer_global_aggregate(p.period, p.metric)
        if p.name and p.competency:
            return self._answer_single_record(p.name, p.competency, p.metric)
        if p.name:
            return self._answer_employee_listing(p.name, p.metric)
        if p.competency:
            return self._answer_competency(p.competency, p.metric)
        return self._fail(
            "Funcionário não encontrado e competência não identificada na consulta. "
            'Tente, por exemplo: "líquido de Ana Souza em maio/2025".'
        )

    def _answer_single_record(self, name: str, competency: str,
                              metric: str | None) -> dict[str, Any]:
        rows = self._rows_for(name)
        rows = rows[rows["competency"] == competency]
        if rows.empty:
            return self._fail(
                f"Nenhum registro encontrado para {name} em {format_competency(competency)}."
            )
        r = rows.iloc[0]
        lines = [f"{name} — {format_competency(competency)} ({competency}):"]
        for label, column in _RECORD_FIELDS.get(metric or "", []):
            lines.append(f"• {label}: {format_currency(r[column])}")
        lines.append(f"• Salário líquido: {format_currency(r['net_pay'])}")
        lines.append(f"• Data de pagamento: {format_date(str(r['payment_date']))}")
        return self._ok("\n".join(lines), rows, "single_record")

    def _answer_employee_aggregate(self, name: str, period: list[str] | None,
                                   metric: str | None) -> dict[str, Any]:
        m = self._metric(metric)
        label = self._period_label(period)
        rows = self._rows_for(name)
        if period:
            rows = rows[rows["competency"].isin(period)]
        if rows.empty:
            return self._fail(f"Nenhum registro encontrado para {name} em {label}.")
        comps = sorted(rows["competency"].tolist())
        data = (
            f"{name} — {label}:\n"
            f"• {m.total}: {format_currency(rows[m.column].sum())}\n"
            f"• Média mensal: {format_currency(rows[m.column].mean())}\n"
            f"• Meses considerados: {len(comps)} ({', '.join(comps)})"
        )
        return self._ok(data, rows, "employee_aggregate")

    def _answer_global_aggregate(self, period: list[str] | None,
                                 metric: str | None) -> dict[str, Any]:
        m = self._metric(metric)
        label = self._period_label(period)
        rows = self.df
        if period:
            rows = rows[rows["competency"].isin(period)]
        if rows.empty:
            return self._fail(f"Nenhum dado encontrado para {label}.")
        data = (
            f"{label[0].upper()}{label[1:]}:\n"
            f"• {m.total} (todos os funcionários): {format_currency(rows[m.column].sum())}\n"
            f"• Média por registro: {format_currency(rows[m.column].mean())}\n"
            f"• Registros: {len(rows)}"
        )
        return self._ok(data, rows, "global_aggregate")

    def _answer_employee_listing(self, name: str, metric: str | None) -> dict[str, Any]:
        m = self._metric(metric)
        rows = self._rows_for(name).sort_values("competency")
        if rows.empty:
            return self._fail(f"Nenhum registro encontrado para {name}.")
        lines = [f"Registros de {name}:"]
        for _, r in rows.iterrows():
            lines.append(
                f"• {format_competency(str(r['competency']))}: "
                f"{m.short} {format_currency(r[m.column])}"
            )
        return self._ok("\n".join(lines), rows, "employee_listing")

    def _answer_extreme(self, name: str | None, scope: list[str] | None,
                        metric: str | None, is_max: bool) -> dict[str, Any]:
        m = self._metric(metric)
        rows = self._rows_for(name) if name else self.df
        if scope:
            rows = rows[rows["competency"].isin(scope)]
        if rows.empty:
            who = f" para {name}" if name else ""
            return self._fail(f"Nenhum registro encontrado{who} em {self._period_label(scope)}.")

        values = rows[m.column]
        target = float(values.max() if is_max else values.min())
        hits = rows.loc[values == target].sort_values(["competency", "name"])
        comps = [f"{format_competency(str(c))} ({c})" for c in hits["competency"]]
        if name:
            where = (f"na competência {comps[0]}" if len(comps) == 1
                     else f"nas competências {_join_pt(comps)}")
        else:
            where = "para " + _join_pt([f"{n} em {c}" for n, c in zip(hits["name"], comps)])

        subject = f"O {'maior' if is_max else 'menor'} {m.noun}"
        if name:
            subject += f" de {name}"
        if scope:
            subject += f" em {self._period_label(scope)}"
        data = f"{subject} foi de {format_currency(target)}, {where}."
        return self._ok(data, hits, "extreme")

    def _answer_competency(self, competency: str, metric: str | None) -> dict[str, Any]:
        m = self._metric(metric)
        rows = self.df[self.df["competency"] == competency].sort_values("name")
        if rows.empty:
            return self._fail(
                f"Nenhum registro encontrado para {format_competency(competency)} ({competency})."
            )
        lines = [f"Folha de {format_competency(competency)}:"]
        for _, r in rows.iterrows():
            lines.append(f"• {r['name']}: {m.short} {format_currency(r[m.column])}")
        lines.append(f"• Total ({m.short}): {format_currency(rows[m.column].sum())}")
        return self._ok("\n".join(lines), rows, "competency")
