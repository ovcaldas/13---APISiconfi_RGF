from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import BASE_URL, DATA_DIR, LOG_DIR, PERIODS, STATES, YEARS

LOGGER = logging.getLogger(__name__)


def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.FileHandler(LOG_DIR / "coleta_rgf.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=handlers,
        force=True,
    )


def make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=1.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.headers.update({"User-Agent": "rgf-estados-analise/1.0"})
    return session


def request_page(
    session: requests.Session,
    params: dict[str, Any],
    url: str = BASE_URL,
    timeout: tuple[int, int] = (10, 90),
) -> dict[str, Any]:
    response = session.get(url, params=params if url == BASE_URL else None, timeout=timeout)
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, dict) or "items" not in payload:
        raise ValueError("Resposta inesperada: objeto JSON sem a chave 'items'.")
    return payload


def fetch_rgf(
    session: requests.Session,
    year: int,
    ibge_code: int,
    period: int,
    pause: float = 1.05,
) -> list[dict[str, Any]]:
    """Busca todas as páginas do Anexo 01 do RGF do Executivo estadual."""
    params = {
        "an_exercicio": year,
        "in_periodicidade": "Q",
        "nr_periodo": period,
        "co_tipo_demonstrativo": "RGF",
        "no_anexo": "RGF-Anexo 01",
        "co_esfera": "E",
        "co_poder": "E",
        "id_ente": ibge_code,
    }
    payload = request_page(session, params)
    items = list(payload.get("items", []))
    while payload.get("hasMore"):
        next_url = next(
            (link.get("href") for link in payload.get("links", []) if link.get("rel") == "next"),
            None,
        )
        if not next_url:
            offset = int(payload.get("offset", 0)) + int(payload.get("limit", 5000))
            next_params = dict(params, offset=offset)
            time.sleep(pause)
            payload = request_page(session, next_params)
        else:
            time.sleep(pause)
            payload = request_page(session, {}, url=next_url)
        items.extend(payload.get("items", []))
    return items


def exploratory_call(
    state: str = "SP", year: int = 2025, period: int = 3
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Executa e registra a chamada exploratória exigida antes da coleta total."""
    configure_logging()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ibge_code = STATES[state][0]
    session = make_session()
    rows = fetch_rgf(session, year, ibge_code, period, pause=0)
    frame = pd.DataFrame(rows)
    structure = {
        "endpoint": BASE_URL,
        "filtros": {
            "UF": state,
            "ano": year,
            "periodo": period,
            "periodicidade": "Q",
            "anexo": "RGF-Anexo 01",
            "esfera": "E",
            "poder": "E (Executivo)",
        },
        "quantidade_registros": len(frame),
        "campos": frame.columns.tolist(),
        "cod_conta": sorted(frame.get("cod_conta", pd.Series(dtype=str)).dropna().unique().tolist()),
        "coluna": sorted(frame.get("coluna", pd.Series(dtype=str)).dropna().unique().tolist()),
    }
    (DATA_DIR / "estrutura_chamada_teste.json").write_text(
        json.dumps(structure, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    frame.to_csv(DATA_DIR / "amostra_chamada_teste.csv", index=False, encoding="utf-8-sig")
    LOGGER.info("Chamada teste: %s/%s Q%s, %s registros, campos=%s", state, year, period, len(frame), list(frame.columns))
    return frame, structure


def collect_all(
    years: Iterable[int] = YEARS,
    states: dict[str, tuple[int, str, str]] = STATES,
    pause: float = 1.05,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Coleta o último quadrimestre disponível de cada UF/ano e registra falhas."""
    configure_logging()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    session = make_session()
    all_rows: list[dict[str, Any]] = []
    audit: list[dict[str, Any]] = []
    total = len(states) * len(list(years))
    completed = 0
    for uf, (ibge_code, state_name, region) in states.items():
        for year in years:
            selected: list[dict[str, Any]] = []
            selected_period: int | None = None
            errors: list[str] = []
            for period in PERIODS:
                try:
                    selected = fetch_rgf(session, year, ibge_code, period, pause=pause)
                    time.sleep(pause)
                except (requests.RequestException, ValueError) as exc:
                    errors.append(f"Q{period}: {type(exc).__name__}: {exc}")
                    LOGGER.warning("Falha %s/%s Q%s: %s", uf, year, period, exc)
                    continue
                if selected:
                    selected_period = period
                    break
            for row in selected:
                row["uf_solicitada"] = uf
                row["nome_estado"] = state_name
                row["regiao"] = region
                row["periodo_selecionado"] = selected_period
            all_rows.extend(selected)
            completed += 1
            status = "ok" if selected else "ausente"
            audit.append(
                {
                    "ano": year,
                    "UF": uf,
                    "nome_estado": state_name,
                    "periodo_selecionado": selected_period,
                    "registros": len(selected),
                    "status": status,
                    "erros": " | ".join(errors),
                }
            )
            LOGGER.info("[%s/%s] %s/%s: %s, Q%s, %s registros", completed, total, uf, year, status, selected_period, len(selected))

    raw = pd.DataFrame(all_rows)
    audit_frame = pd.DataFrame(audit)
    raw.to_csv(DATA_DIR / "rgf_estados_2015_2025_raw.csv", index=False, encoding="utf-8-sig")
    audit_frame.to_csv(DATA_DIR / "auditoria_coleta.csv", index=False, encoding="utf-8-sig")
    return raw, audit_frame

