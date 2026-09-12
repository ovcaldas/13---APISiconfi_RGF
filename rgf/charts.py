from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

from .config import CHART_DIR


COLORS = {"good": "#167D5A", "mid": "#E7A425", "bad": "#B83A3A", "navy": "#19324D"}


def _save(fig: plt.Figure, name: str) -> None:
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(CHART_DIR / name, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def generate_charts(base: pd.DataFrame, indicators: pd.DataFrame) -> None:
    plt.style.use("seaborn-v0_8-whitegrid")
    available_year = int(base.dropna(subset=["DTP_RCL"])["ano"].max())
    latest = base[(base["ano"] == available_year) & base["DTP_RCL"].notna()].sort_values("DTP_RCL")

    fig, ax = plt.subplots(figsize=(10, 9))
    status_colors = {
        "confortável": COLORS["good"], "atenção": COLORS["mid"], "alerta": "#E47B25",
        "acima do limite prudencial": COLORS["bad"], "acima do limite máximo": "#761B18",
    }
    bars = ax.barh(latest["UF"], latest["DTP_RCL"], color=latest["situacao_fiscal"].map(status_colors).fillna(COLORS["navy"]))
    ax.bar_label(bars, fmt="%.2f", padding=3, fontsize=7)
    ax.invert_yaxis(); ax.set_xlabel("DTP / RCL ajustada (%)"); ax.set_title(f"Ranking dos estados — {available_year} (menor é melhor)")
    ax.set_xlim(0, latest["DTP_RCL"].max() * 1.08)
    _save(fig, "01_ranking_ultimo_ano.png")

    fig, ax = plt.subplots(figsize=(13, 8))
    for uf, group in base.dropna(subset=["DTP_RCL"]).groupby("UF"):
        group = group.sort_values("ano"); ax.plot(group["ano"], group["DTP_RCL"], alpha=.65, linewidth=1.2)
        if group["ano"].max() == available_year:
            ax.text(group.iloc[-1]["ano"] + .06, group.iloc[-1]["DTP_RCL"], uf, fontsize=7)
    ax.set_xlim(base["ano"].min(), base["ano"].max() + .8); ax.set_ylabel("DTP / RCL ajustada (%)"); ax.set_title("Evolução do comprometimento da RCL — todos os estados")
    _save(fig, "02_evolucao_todos_estados.png")

    best_ufs = indicators.nsmallest(5, "ranking_historico")["UF"].tolist()
    worst_ufs = indicators.nlargest(5, "ranking_historico")["UF"].tolist()
    selected = best_ufs + worst_ufs
    palette = list(plt.cm.Greens(np.linspace(.45, .9, 5))) + list(plt.cm.Reds(np.linspace(.45, .9, 5)))
    fig, ax = plt.subplots(figsize=(12, 7))
    for uf, color in zip(selected, palette):
        group = base[(base["UF"] == uf) & base["DTP_RCL"].notna()].sort_values("ano")
        ax.plot(group["ano"], group["DTP_RCL"], marker="o", markersize=3, label=uf, color=color, linewidth=1.8)
    ax.set_ylabel("DTP / RCL ajustada (%)"); ax.set_title("Evolução dos 5 melhores e 5 piores no score fiscal"); ax.legend(ncol=5)
    _save(fig, "03_evolucao_5_melhores_5_piores.png")

    pivot = base.pivot(index="UF", columns="ano", values="DTP_RCL").sort_index()
    fig, ax = plt.subplots(figsize=(13, 9))
    cmap = LinearSegmentedColormap.from_list("fiscal", ["#D7F0E7", "#F7D67B", "#BD3D3A"])
    im = ax.imshow(pivot, aspect="auto", cmap=cmap)
    ax.set_xticks(range(len(pivot.columns)), pivot.columns, rotation=45); ax.set_yticks(range(len(pivot.index)), pivot.index); ax.set_title("Heatmap Estado × Ano — DTP/RCL (%)")
    fig.colorbar(im, ax=ax, label="%")
    _save(fig, "04_heatmap_estado_ano.png")

    for metric, title, filename in [
        ("Margem_Limite_Prudencial", "Distância para o limite prudencial", "05_distancia_limite_prudencial.png"),
        ("Margem_Limite_Maximo", "Distância para o limite máximo", "06_distancia_limite_maximo.png"),
    ]:
        ordered = latest.sort_values(metric)
        fig, ax = plt.subplots(figsize=(10, 9)); colors = np.where(ordered[metric] >= 0, COLORS["good"], COLORS["bad"])
        ax.barh(ordered["UF"], ordered[metric], color=colors); ax.axvline(0, color="black", linewidth=.9); ax.set_xlabel("Margem (pontos percentuais)"); ax.set_title(f"{title} — {available_year}")
        _save(fig, filename)

    ordered = indicators.sort_values("score_fiscal")
    fig, ax = plt.subplots(figsize=(10, 9)); ax.barh(ordered["UF"], ordered["score_fiscal"], color=COLORS["navy"]); ax.set_xlim(0, 100); ax.set_xlabel("Score fiscal (0–100; maior é melhor)"); ax.set_title("Ranking do score fiscal — 2015–2025")
    _save(fig, "07_ranking_score_fiscal.png")

    comparison = base.assign(periodo_analise=np.where(base["ano"] <= 2019, "2015–2019", "2020–2025")).pivot_table(index="UF", columns="periodo_analise", values="DTP_RCL", aggfunc="mean").dropna()
    comparison = comparison.sort_values("2020–2025")
    y = np.arange(len(comparison)); fig, ax = plt.subplots(figsize=(11, 10))
    ax.scatter(comparison["2015–2019"], y, label="2015–2019", color="#7A8EA3"); ax.scatter(comparison["2020–2025"], y, label="2020–2025", color=COLORS["navy"])
    for i, row in enumerate(comparison.itertuples()): ax.plot([getattr(row, "_1"), getattr(row, "_2")], [i, i], color="#C7CDD3", zorder=0)
    ax.set_yticks(y, comparison.index); ax.set_xlabel("Média DTP/RCL (%)"); ax.set_title("Comparação das médias: 2015–2019 × 2020–2025"); ax.legend()
    _save(fig, "08_comparacao_periodos.png")
