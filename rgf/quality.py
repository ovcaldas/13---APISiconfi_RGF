from __future__ import annotations

from pathlib import Path

import pandas as pd

from .config import DATA_DIR


def build_quality_report(raw: pd.DataFrame, base: pd.DataFrame, mapping: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Materializa verificações de completude, duplicidade e mudança estrutural."""
    business_key = [c for c in ["exercicio", "uf", "periodo", "co_poder", "anexo", "rotulo", "cod_conta", "coluna"] if c in raw]
    structure = (
        raw.groupby("exercicio")
        .agg(
            registros=("valor", "size"),
            UFs=("uf", "nunique"),
            contas_distintas=("cod_conta", "nunique"),
            nomenclaturas_distintas=("conta", "nunique"),
            colunas_distintas=("coluna", "nunique"),
        )
        .reset_index()
        .rename(columns={"exercicio": "ano"})
    )
    nomenclature = (
        raw.groupby(["exercicio", "cod_conta"], dropna=False)["conta"]
        .agg(lambda values: " | ".join(sorted(set(map(str, values.dropna())))))
        .reset_index()
        .rename(columns={"exercicio": "ano", "conta": "nomenclaturas_observadas"})
    )
    missing_by_year = base.groupby("ano").agg(
        observacoes=("UF", "size"),
        DTP_RCL_ausente=("DTP_RCL", lambda s: int(s.isna().sum())),
        RCL_ausente=("Receita_Corrente_Liquida", lambda s: int(s.isna().sum())),
        RCL_ajustada_ausente=("RCL_Ajustada", lambda s: int(s.isna().sum())),
        limite_alerta_ausente=("Limite_Alerta", lambda s: int(s.isna().sum())),
        limite_prudencial_ausente=("Limite_Prudencial", lambda s: int(s.isna().sum())),
        limite_maximo_ausente=("Limite_Maximo", lambda s: int(s.isna().sum())),
    ).reset_index()
    summary = pd.DataFrame(
        [
            ("registros_brutos", len(raw)),
            ("duplicatas_exatas", int(raw.duplicated().sum())),
            ("duplicatas_chave_negocio", int(raw.duplicated(business_key).sum()) if business_key else 0),
            ("observacoes_UF_ano_esperadas", 297),
            ("observacoes_UF_ano_com_DTP_RCL", int(base["DTP_RCL"].notna().sum())),
            ("observacoes_UF_ano_sem_DTP_RCL", int(base["DTP_RCL"].isna().sum())),
            ("mapeamentos_ok", int((mapping["status"] == "ok").sum())),
            ("mapeamentos_ausentes", int((mapping["status"] == "ausente").sum())),
            ("mapeamentos_com_conflito", int(mapping["status"].str.startswith("conflito", na=False).sum())),
        ],
        columns=["verificacao", "valor"],
    )
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(DATA_DIR / "qualidade_resumo.csv", index=False, encoding="utf-8-sig")
    structure.to_csv(DATA_DIR / "estrutura_por_ano.csv", index=False, encoding="utf-8-sig")
    nomenclature.to_csv(DATA_DIR / "nomenclaturas_por_ano.csv", index=False, encoding="utf-8-sig")
    missing_by_year.to_csv(DATA_DIR / "ausencias_por_ano.csv", index=False, encoding="utf-8-sig")

    old = structure[structure["ano"] <= 2017]["contas_distintas"].median()
    new = structure[structure["ano"] >= 2018]["contas_distintas"].median()
    report = f"""RELATÓRIO DE QUALIDADE — RGF ESTADOS 2015–2025

Cobertura: {base['DTP_RCL'].notna().sum()} de 297 combinações UF/ano com DTP/RCL válido.
Duplicatas exatas: {raw.duplicated().sum()}.
Duplicatas pela chave de negócio: {raw.duplicated(business_key).sum() if business_key else 0}.
Mapeamentos ausentes: {(mapping['status'] == 'ausente').sum()}; conflitos: {mapping['status'].str.startswith('conflito', na=False).sum()}.

Mudança estrutural: a mediana de códigos de conta distintos foi {old:.0f} em 2015–2017 e {new:.0f} em 2018–2025. Isso evidencia ampliação relevante do detalhamento a partir de 2018. O mapeamento usa conjuntamente código e descrição normalizados, e a fonte exata de cada indicador consta em auditoria_mapeamento.csv.

Tratamento de ausências: nenhum nulo foi convertido em zero. A RCL ajustada ausente nos modelos antigos não invalida o percentual DTP/RCL quando ele é declarado pelo próprio RGF. Consulte ausencias_por_ano.csv para o detalhamento.
"""
    (DATA_DIR / "relatorio_qualidade.txt").write_text(report, encoding="utf-8")
    return {"resumo": summary, "estrutura": structure, "nomenclaturas": nomenclature, "ausencias": missing_by_year}

