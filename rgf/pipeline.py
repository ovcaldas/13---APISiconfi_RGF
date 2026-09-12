from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from .analysis import annual_ranking, build_indicators
from .api import collect_all, exploratory_call
from .charts import generate_charts
from .config import DATA_DIR
from .export import executive_summary, export_excel
from .treatment import build_treated


def run(download: bool = True) -> None:
    exploratory_call()
    raw_path = DATA_DIR / "rgf_estados_2015_2025_raw.csv"
    if download:
        raw, audit = collect_all()
    elif raw_path.exists():
        raw = pd.read_csv(raw_path, low_memory=False)
    else:
        raise FileNotFoundError(f"Use a coleta completa: arquivo não encontrado em {raw_path}")
    treated, mapping = build_treated(raw)
    indicators = build_indicators(treated)
    ranking = annual_ranking(treated)
    indicators.to_csv(DATA_DIR / "indicadores_estados.csv", index=False, encoding="utf-8-sig")
    ranking.to_csv(DATA_DIR / "ranking_anual.csv", index=False, encoding="utf-8-sig")
    generate_charts(treated, indicators)
    export_excel(treated, indicators, ranking)
    (DATA_DIR / "panorama_executivo.txt").write_text(executive_summary(treated, indicators), encoding="utf-8")
    print(f"Concluído: {len(raw):,} registros brutos; {treated['DTP_RCL'].notna().sum()} observações anuais válidas.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline do RGF dos Executivos estaduais, 2015–2025")
    parser.add_argument("--sem-download", action="store_true", help="Reprocessa o CSV bruto já existente")
    args = parser.parse_args()
    run(download=not args.sem_download)

