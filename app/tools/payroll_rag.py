"""RAG de folha de pagamento.

Consultas determinísticas sobre o CSV da folha. A camada de LLM (no agente)
não altera os números produzidos aqui: valores, datas e fontes saem prontos.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from ..utils.formatting import format_competency, format_currency, format_date

logger = logging.getLogger(__name__)

_DEFAULT_CSV = Path(__file__).resolve().parents[2] / "data" / "payroll.csv"

_MONTHS = {
    "janeiro": 1, "fevereiro": 2, "marco": 3, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8, "setembro": 9,
    "outubro": 10, "novembro": 11, "dezembro": 12,
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}
_MONTH_RE = re.compile(
    r"\b(jan(?:eiro)?|fev(?:ereiro)?|mar(?:ço|co)?|abr(?:il)?|mai(?:o)?|"
    r"jun(?:ho)?|jul(?:ho)?|ago(?:sto)?|set(?:embro)?|out(?:ubro)?|"
    r"nov(?:embro)?|dez(?:embro)?)\b\.?",
    re.IGNORECASE,
)
_ORDINALS = {
    "primeiro": 1, "segundo": 2, "terceiro": 3, "quarto": 4,
    "1": 1, "2": 2, "3": 3, "4": 4,
}
_AGGREGATE_WORDS = ("total", "soma", "somar", "média", "media", "médio", "medio")


class PayrollRAG:
    """Consultas sobre a folha de pagamento a partir de um CSV."""

    def __init__(self, csv_path: "str | Path | None" = None) -> None:
        self.csv_path = Path(csv_path) if csv_path else _DEFAULT_CSV
        self.df = pd.DataFrame()
        self._name_lookup: Dict[str, str] = {}
        self._ensure_loaded()

    # ----------------------------------------------------------------- loading
    def _ensure_loaded(self) -> None:
        if not self.df.empty:
            return
        try:
            df = pd.read_csv(self.csv_path)
            df["competency"] = df["competency"].astype(str)
            df["payment_date"] = df["payment_date"].astype(str)
            self.df = df
            self._build_name_lookup()
            logger.info("Folha carregada: %d registros de %s", len(df), self.csv_path)
        except Exception as exc:  # pragma: no cover - depende de I/O
            logger.error("Falha ao carregar %s: %s", self.csv_path, exc)
            self.df = pd.DataFrame()

    def _build_name_lookup(self) -> None:
        lookup: Dict[str, str] = {}
        for full in self.df["name"].dropna().unique():
            full = str(full)
            parts = full.split()
            lookup[full.lower()] = full
            if parts:
                lookup.setdefault(parts[0].lower(), full)
                lookup.setdefault(parts[-1].lower(), full)
        self._name_lookup = lookup

    def known_names(self) -> List[str]:
        self._ensure_loaded()
        if self.df.empty:
            return []
        return sorted(self.df["name"].dropna().unique().tolist())

    def _default_year(self) -> int:
        if self.df.empty:
            return 2025
        return int(self.df["competency"].str.slice(0, 4).astype(int).max())

    # -------------------------------------------------------------- extraction
    def _extract_employee_name(self, query: str) -> Optional[str]:
        q = query.lower()
        for key, full in self._name_lookup.items():
            if " " in key and key in q:
                return full
        for key, full in self._name_lookup.items():
            if " " not in key and re.search(rf"\b{re.escape(key)}\b", q):
                return full
        return None

    def _extract_competency(self, query: str) -> Optional[str]:
        q = query.lower().strip()
        m = re.search(r"\b(\d{4})-(\d{2})\b", q)
        if m:
            return f"{m.group(1)}-{m.group(2)}"
        m = re.search(r"\b(\d{1,2})/(\d{4})\b", q)
        if m:
            return f"{m.group(2)}-{int(m.group(1)):02d}"
        month_match = _MONTH_RE.search(q)
        if month_match:
            token = month_match.group(1).lower().rstrip(".")
            month = _MONTHS.get(token) or _MONTHS.get(token[:3])
            year_match = re.search(r"\b(20\d{2})\b", q)
            if month and year_match:
                return f"{year_match.group(1)}-{month:02d}"
        return None

    def _extract_period(self, query: str) -> Optional[List[str]]:
        q = query.lower()
        match = re.search(
            r"(primeiro|segundo|terceiro|quarto|[1-4])\s*[ºo°.]*\s*(trimestre|semestre)", q
        )
        if match:
            n = _ORDINALS.get(match.group(1), 1)
            kind = match.group(2)
        elif "trimestre" in q:
            n, kind = 1, "trimestre"
        elif "semestre" in q:
            n, kind = 1, "semestre"
        else:
            return None

        year_match = re.search(r"\b(20\d{2})\b", q)
        year = int(year_match.group(1)) if year_match else self._default_year()
        if kind == "trimestre":
            start = (n - 1) * 3 + 1
            months = range(start, start + 3)
        else:
            months = range(1, 7) if n == 1 else range(7, 13)
        return [f"{year}-{month:02d}" for month in months]

    @staticmethod
    def _detect_metric(query: str) -> str:
        q = query.lower()
        if "inss" in q:
            return "inss"
        if "irrf" in q or "imposto de renda" in q:
            return "irrf"
        if "bônus" in q or "bonus" in q:
            return "bonus"
        if "quando" in q or "foi pago" in q or "data de pagamento" in q or "data do pagamento" in q:
            return "payment_date"
        if "salário base" in q or "salario base" in q:
            return "base_salary"
        return "net_pay"

    @staticmethod
    def _period_label(competencies: Optional[List[str]]) -> str:
        if not competencies:
            return "todo o período disponível"
        months = sorted(competencies)
        year = months[0][:4]
        idx = {m[5:7] for m in months}
        quarters = {
            frozenset({"01", "02", "03"}): "1º trimestre",
            frozenset({"04", "05", "06"}): "2º trimestre",
            frozenset({"07", "08", "09"}): "3º trimestre",
            frozenset({"10", "11", "12"}): "4º trimestre",
            frozenset({"01", "02", "03", "04", "05", "06"}): "1º semestre",
            frozenset({"07", "08", "09", "10", "11", "12"}): "2º semestre",
        }
        label = quarters.get(frozenset(idx))
        if label:
            return f"{label} de {year}"
        return f"{months[0]} a {months[-1]}"

    # ------------------------------------------------------------------ output
    def _build_evidence(self, rows: pd.DataFrame, query_type: str) -> Dict[str, Any]:
        sources = []
        for _, r in rows.iterrows():
            sources.append({
                "employee_id": str(r["employee_id"]),
                "name": str(r["name"]),
                "competency": str(r["competency"]),
                "payment_date": str(r["payment_date"]),
                "base_salary": float(r["base_salary"]),
                "bonus": float(r["bonus"]),
                "deductions_inss": float(r["deductions_inss"]),
                "deductions_irrf": float(r["deductions_irrf"]),
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
    def _fail(message: str) -> Dict[str, Any]:
        return {"success": False, "data": message, "evidence": None}

    def _rows_for(self, name: str) -> pd.DataFrame:
        return self.df[self.df["name"].str.lower() == name.lower()]

    # ------------------------------------------------------------------- query
    async def query(self, query: str) -> Dict[str, Any]:
        try:
            self._ensure_loaded()
            if self.df.empty:
                return self._fail("Não consegui carregar os dados da folha de pagamento.")
            if not query or not query.strip():
                return self._fail("Consulta vazia. Diga o que você quer saber sobre a folha.")

            name = self._extract_employee_name(query)
            period = self._extract_period(query)
            competency = self._extract_competency(query)
            metric = self._detect_metric(query)
            q = query.lower()
            wants_total = any(w in q for w in _AGGREGATE_WORDS) or period is not None
            wants_extreme = "maior" in q or "menor" in q

            if name and wants_extreme and metric == "bonus":
                return self._answer_extreme_bonus(name, is_max="maior" in q)
            if name and wants_total:
                return self._answer_employee_aggregate(name, period)
            if name and competency:
                return self._answer_single_record(name, competency, metric)
            if name:
                return self._answer_employee_listing(name)
            if wants_total:
                return self._answer_global_aggregate(period)
            if competency:
                return self._answer_competency(competency)
            return self._fail(
                "Funcionário não encontrado e competência não identificada na consulta. "
                'Tente, por exemplo: "líquido de Ana Souza em maio/2025".'
            )
        except Exception as exc:
            logger.error("Erro ao processar consulta RAG: %s", exc)
            return self._fail(f"Erro ao consultar a folha: {exc}")

    def _answer_single_record(self, name: str, competency: str, metric: str) -> Dict[str, Any]:
        rows = self._rows_for(name)
        rows = rows[rows["competency"] == competency]
        if rows.empty:
            return self._fail(
                f"Nenhum registro encontrado para {name} em {format_competency(competency)}."
            )
        r = rows.iloc[0]
        lines = [f"{name} — {format_competency(competency)} ({competency}):"]
        if metric == "inss":
            lines.append(f"• Desconto de INSS: {format_currency(r['deductions_inss'])}")
        elif metric == "irrf":
            lines.append(f"• Desconto de IRRF: {format_currency(r['deductions_irrf'])}")
        elif metric == "bonus":
            lines.append(f"• Bônus: {format_currency(r['bonus'])}")
        elif metric == "base_salary":
            lines.append(f"• Salário base: {format_currency(r['base_salary'])}")
        lines.append(f"• Salário líquido: {format_currency(r['net_pay'])}")
        lines.append(f"• Data de pagamento: {format_date(str(r['payment_date']))}")
        return {"success": True, "data": "\n".join(lines),
                "evidence": self._build_evidence(rows, "single_record")}

    def _answer_employee_aggregate(self, name: str, period: Optional[List[str]]) -> Dict[str, Any]:
        rows = self._rows_for(name)
        if period:
            rows = rows[rows["competency"].isin(period)]
        if rows.empty:
            return self._fail(f"Nenhum registro encontrado para {name} no período solicitado.")
        comps = sorted(rows["competency"].tolist())
        data = (
            f"{name} — {self._period_label(comps)}:\n"
            f"• Total líquido: {format_currency(rows['net_pay'].sum())}\n"
            f"• Média mensal: {format_currency(rows['net_pay'].mean())}\n"
            f"• Meses considerados: {len(comps)} ({', '.join(comps)})"
        )
        return {"success": True, "data": data,
                "evidence": self._build_evidence(rows, "employee_aggregate")}

    def _answer_employee_listing(self, name: str) -> Dict[str, Any]:
        rows = self._rows_for(name).sort_values("competency")
        if rows.empty:
            return self._fail(f"Nenhum registro encontrado para {name}.")
        lines = [f"Registros de {name}:"]
        for _, r in rows.iterrows():
            lines.append(
                f"• {format_competency(str(r['competency']))}: "
                f"líquido {format_currency(r['net_pay'])}"
            )
        return {"success": True, "data": "\n".join(lines),
                "evidence": self._build_evidence(rows, "employee_listing")}

    def _answer_extreme_bonus(self, name: str, is_max: bool) -> Dict[str, Any]:
        rows = self._rows_for(name)
        if rows.empty:
            return self._fail(f"Nenhum registro encontrado para {name}.")
        idx = rows["bonus"].idxmax() if is_max else rows["bonus"].idxmin()
        row = rows.loc[[idx]]
        rec = row.iloc[0]
        comp = str(rec["competency"])
        palavra = "maior" if is_max else "menor"
        data = (
            f"O {palavra} bônus de {name} foi de {format_currency(rec['bonus'])}, "
            f"na competência {format_competency(comp)} ({comp})."
        )
        return {"success": True, "data": data,
                "evidence": self._build_evidence(row, "extreme_bonus")}

    def _answer_global_aggregate(self, period: Optional[List[str]]) -> Dict[str, Any]:
        rows = self.df
        if period:
            rows = rows[rows["competency"].isin(period)]
        if rows.empty:
            return self._fail("Nenhum dado encontrado para o período solicitado.")
        label = self._period_label(sorted(rows["competency"].unique().tolist()) if period else None)
        data = (
            f"{label.capitalize()}:\n"
            f"• Total líquido (todos os funcionários): {format_currency(rows['net_pay'].sum())}\n"
            f"• Média por registro: {format_currency(rows['net_pay'].mean())}\n"
            f"• Registros: {len(rows)}"
        )
        return {"success": True, "data": data,
                "evidence": self._build_evidence(rows, "global_aggregate")}

    def _answer_competency(self, competency: str) -> Dict[str, Any]:
        rows = self.df[self.df["competency"] == competency].sort_values("name")
        if rows.empty:
            return self._fail(
                f"Nenhum registro encontrado para {format_competency(competency)} ({competency})."
            )
        lines = [f"Folha de {format_competency(competency)}:"]
        for _, r in rows.iterrows():
            lines.append(f"• {r['name']}: líquido {format_currency(r['net_pay'])}")
        return {"success": True, "data": "\n".join(lines),
                "evidence": self._build_evidence(rows, "competency")}
