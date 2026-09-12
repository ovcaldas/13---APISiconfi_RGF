from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import DATA_DIR, STATES, YEARS


def normalize(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9%]+", " ", text.lower()).strip()


def parse_number(value: object) -> float:
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return np.nan
    if isinstance(value, (int, float, np.number)):
        return float(value)
    text = str(value).strip().replace("\u00a0", "")
    if not text or text in {"-", "--"}:
        return np.nan
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return np.nan


@dataclass(frozen=True)
class Metric:
    output: str
    account_patterns: tuple[str, ...]
    percent: bool = False
    exclude_patterns: tuple[str, ...] = ()


METRICS = (
    Metric("Receita_Corrente_Liquida", ("receitacorrenteliquidalimitelegal", "receita corrente liquida rcl")),
    Metric("RCL_Ajustada", ("receitacorrenteliquidaajustada", "receita corrente liquida ajustada")),
    Metric("Despesa_Total_Pessoal", ("despesacompessoaltotal", "despesa total com pessoal"), exclude_patterns=("limite",)),
    Metric("DTP_RCL", ("despesacompessoaltotal", "despesa total com pessoal"), percent=True, exclude_patterns=("limite",)),
    Metric("Limite_Alerta", ("limitedealertadespesacompessoaltotal", "limite de alerta"), percent=True),
    Metric("Limite_Prudencial", ("limiteprudencialdespesacompessoaltotal", "limite prudencial"), percent=True),
    Metric("Limite_Maximo", ("limitemaximodespesacompessoaltotal", "limite maximo"), percent=True),
)


def _choose_metric(group: pd.DataFrame, metric: Metric) -> tuple[float, str, str]:
    combined = group["_account"].fillna("") + " " + group["_name"].fillna("")
    mask = pd.Series(False, index=group.index)
    for pattern in metric.account_patterns:
        mask |= combined.str.contains(normalize(pattern), regex=False)
    for pattern in metric.exclude_patterns:
        mask &= ~combined.str.contains(normalize(pattern), regex=False)
    column = group["_column"]
    if metric.percent:
        mask &= column.str.contains("%", regex=False)
    else:
        mask &= ~column.str.contains("%", regex=False)
        preferred = mask & column.isin(("valor", "valor ajustado"))
        if preferred.any():
            mask = preferred
    candidates = group.loc[mask].copy()
    if candidates.empty:
        return np.nan, "", "ausente"
    candidates["_numeric"] = candidates["valor"].map(parse_number)
    candidates = candidates.dropna(subset=["_numeric"])
    if candidates.empty:
        return np.nan, "", "não numérico"
    unique_values = candidates["_numeric"].round(8).unique()
    status = "ok" if len(unique_values) == 1 else f"conflito ({len(unique_values)} valores); primeiro usado"
    row = candidates.iloc[0]
    source = f"{row.get('cod_conta', '')} | {row.get('conta', '')} | {row.get('coluna', '')}"
    return float(row["_numeric"]), source, status


def classify(row: pd.Series) -> str:
    value = row.get("DTP_RCL")
    alert = row.get("Limite_Alerta")
    prudent = row.get("Limite_Prudencial")
    maximum = row.get("Limite_Maximo")
    if pd.isna(value):
        return "sem dado"
    if pd.notna(maximum) and value > maximum:
        return "acima do limite máximo"
    if pd.notna(prudent) and value > prudent:
        return "acima do limite prudencial"
    if pd.notna(alert) and value > alert:
        return "alerta"
    # "Atenção" é a metade superior do intervalo entre alerta e prudencial.
    if pd.notna(alert) and pd.notna(prudent) and value >= alert - (prudent - alert) / 2:
        return "atenção"
    return "confortável"


def build_treated(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    expected = {"exercicio", "uf", "cod_conta", "conta", "coluna", "valor"}
    missing = expected - set(raw.columns)
    if missing:
        raise ValueError(f"CSV bruto não contém campos obrigatórios: {sorted(missing)}")
    work = raw.copy()
    work["_account"] = work["cod_conta"].map(normalize)
    work["_name"] = work["conta"].map(normalize)
    work["_column"] = work["coluna"].map(normalize)
    keys = ["exercicio", "uf"]
    records: list[dict[str, object]] = []
    mapping_audit: list[dict[str, object]] = []
    for (year, uf), group in work.groupby(keys, dropna=False):
        state_info = STATES.get(str(uf), (np.nan, group.get("nome_estado", pd.Series([uf])).iloc[0], ""))
        record: dict[str, object] = {
            "ano": int(year),
            "UF": uf,
            "nome_estado": state_info[1],
            "regiao": state_info[2],
            "populacao": pd.to_numeric(group.get("populacao"), errors="coerce").dropna().max(),
            "periodo": pd.to_numeric(group.get("periodo"), errors="coerce").dropna().max(),
            "poder": "Executivo",
        }
        for metric in METRICS:
            value, source, status = _choose_metric(group, metric)
            record[metric.output] = value
            mapping_audit.append({"ano": year, "UF": uf, "metrica": metric.output, "fonte": source, "status": status})
        denominator = record["RCL_Ajustada"]
        if pd.isna(denominator):
            denominator = record["Receita_Corrente_Liquida"]
        calculated = (
            100 * record["Despesa_Total_Pessoal"] / denominator
            if pd.notna(record["Despesa_Total_Pessoal"]) and pd.notna(denominator) and denominator != 0
            else np.nan
        )
        record["DTP_RCL_Calculado"] = calculated
        record["fonte_DTP_RCL"] = "percentual declarado no RGF" if pd.notna(record["DTP_RCL"]) else "calculado (DTP/RCL ajustada)"
        if pd.isna(record["DTP_RCL"]):
            record["DTP_RCL"] = calculated
        records.append(record)

    treated = pd.DataFrame(records)
    # Explicita combinações ausentes, sem preencher os indicadores com zero.
    grid = pd.MultiIndex.from_product([YEARS, STATES.keys()], names=["ano", "UF"]).to_frame(index=False)
    treated = grid.merge(treated, on=["ano", "UF"], how="left")
    treated["nome_estado"] = treated["UF"].map(lambda uf: STATES[uf][1])
    treated["regiao"] = treated["UF"].map(lambda uf: STATES[uf][2])
    treated["Margem_Limite_Prudencial"] = treated["Limite_Prudencial"] - treated["DTP_RCL"]
    treated["Margem_Limite_Maximo"] = treated["Limite_Maximo"] - treated["DTP_RCL"]
    treated["Variacao_Anual_DTP_RCL_pp"] = treated.sort_values("ano").groupby("UF")["DTP_RCL"].diff()
    treated["situacao_fiscal"] = treated.apply(classify, axis=1)
    treated = treated.sort_values(["ano", "DTP_RCL", "UF"], na_position="last").reset_index(drop=True)
    treated["ranking_ano"] = treated.groupby("ano")["DTP_RCL"].rank(method="min", ascending=True)

    quality = pd.DataFrame(mapping_audit)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    treated.to_csv(DATA_DIR / "rgf_estados_2015_2025_tratado.csv", index=False, encoding="utf-8-sig")
    quality.to_csv(DATA_DIR / "auditoria_mapeamento.csv", index=False, encoding="utf-8-sig")
    return treated, quality

