from __future__ import annotations

import numpy as np
import pandas as pd


def _slope(group: pd.DataFrame, last_n: int | None = None) -> float:
    valid = group.dropna(subset=["DTP_RCL"]).sort_values("ano")
    if last_n:
        valid = valid.tail(last_n)
    if len(valid) < 2:
        return np.nan
    return float(np.polyfit(valid["ano"].astype(float), valid["DTP_RCL"].astype(float), 1)[0])


def _percentile(series: pd.Series, higher_is_better: bool) -> pd.Series:
    result = series.rank(pct=True, ascending=higher_is_better)
    return result.fillna(0.5)


def build_indicators(base: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for uf, group in base.groupby("UF"):
        valid = group.dropna(subset=["DTP_RCL"]).sort_values("ano")
        last3 = valid.tail(3)
        first = valid.iloc[0] if not valid.empty else None
        last = valid.iloc[-1] if not valid.empty else None
        rows.append(
            {
                "UF": uf,
                "nome_estado": group["nome_estado"].iloc[0],
                "regiao": group["regiao"].iloc[0],
                "anos_disponiveis": len(valid),
                "primeiro_ano": first["ano"] if first is not None else np.nan,
                "ultimo_ano": last["ano"] if last is not None else np.nan,
                "media_2015_2025": valid["DTP_RCL"].mean(),
                "media_ultimos_3_anos": last3["DTP_RCL"].mean(),
                "maior_valor": valid["DTP_RCL"].max(),
                "menor_valor": valid["DTP_RCL"].min(),
                "volatilidade_desvio_padrao": valid["DTP_RCL"].std(),
                "tendencia_historica_pp_ano": _slope(valid),
                "tendencia_recente_pp_ano": _slope(valid, 3),
                "variacao_primeiro_ultimo_pp": (last["DTP_RCL"] - first["DTP_RCL"]) if first is not None else np.nan,
                "media_margem_prudencial": valid["Margem_Limite_Prudencial"].mean(),
                "media_margem_maximo": valid["Margem_Limite_Maximo"].mean(),
                "anos_acima_alerta": ((valid["DTP_RCL"] > valid["Limite_Alerta"]) & valid["Limite_Alerta"].notna()).sum(),
                "anos_acima_prudencial": ((valid["DTP_RCL"] > valid["Limite_Prudencial"]) & valid["Limite_Prudencial"].notna()).sum(),
                "anos_acima_maximo": ((valid["DTP_RCL"] > valid["Limite_Maximo"]) & valid["Limite_Maximo"].notna()).sum(),
            }
        )
    indicators = pd.DataFrame(rows)
    indicators["taxa_alerta"] = indicators["anos_acima_alerta"] / indicators["anos_disponiveis"].replace(0, np.nan)

    components = {
        "score_nivel": _percentile(indicators["media_2015_2025"], False),
        "score_margem_prudencial": _percentile(indicators["media_margem_prudencial"], True),
        "score_margem_maximo": _percentile(indicators["media_margem_maximo"], True),
        "score_recorrencia": _percentile(indicators["taxa_alerta"], False),
        "score_tendencia": _percentile(indicators["tendencia_recente_pp_ano"], False),
        "score_volatilidade": _percentile(indicators["volatilidade_desvio_padrao"], False),
    }
    for name, values in components.items():
        indicators[name] = values
    indicators["score_fiscal"] = 100 * (
        0.30 * indicators["score_nivel"]
        + 0.20 * indicators["score_margem_prudencial"]
        + 0.15 * indicators["score_margem_maximo"]
        + 0.15 * indicators["score_recorrencia"]
        + 0.10 * indicators["score_tendencia"]
        + 0.10 * indicators["score_volatilidade"]
    )
    indicators["ranking_historico"] = indicators["score_fiscal"].rank(method="min", ascending=False).astype("Int64")
    rank_pct = indicators["score_fiscal"].rank(pct=True, ascending=True)
    indicators["grupo"] = np.select(
        [rank_pct > 2 / 3, rank_pct <= 1 / 3],
        ["GRUPO 1 – Melhor situação fiscal", "GRUPO 3 – Pior situação fiscal"],
        default="GRUPO 2 – Situação intermediária",
    )
    indicators["tendencia_recente"] = np.select(
        [indicators["tendencia_recente_pp_ano"] <= -0.15, indicators["tendencia_recente_pp_ano"] >= 0.15],
        ["melhora", "deterioração"],
        default="estável",
    )
    return indicators.sort_values("ranking_historico").reset_index(drop=True)


def annual_ranking(base: pd.DataFrame) -> pd.DataFrame:
    return base.dropna(subset=["DTP_RCL"]).sort_values(["ano", "DTP_RCL", "UF"])[
        ["ano", "ranking_ano", "UF", "nome_estado", "DTP_RCL", "Limite_Alerta", "Limite_Prudencial", "Limite_Maximo", "situacao_fiscal"]
    ]

