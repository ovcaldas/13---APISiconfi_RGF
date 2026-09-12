from pathlib import Path

BASE_URL = "https://apidatalake.tesouro.gov.br/ords/cdwhprd/siconfi/tt/rgf"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "dados"
CHART_DIR = ROOT / "graficos"
LOG_DIR = ROOT / "logs"
NOTEBOOK_DIR = ROOT / "notebooks"

YEARS = list(range(2015, 2026))
PERIODS = (3, 2, 1)

# Código IBGE de dois dígitos aceito pelo endpoint para estados e DF.
STATES = {
    "AC": (12, "Acre", "Norte"),
    "AL": (27, "Alagoas", "Nordeste"),
    "AP": (16, "Amapá", "Norte"),
    "AM": (13, "Amazonas", "Norte"),
    "BA": (29, "Bahia", "Nordeste"),
    "CE": (23, "Ceará", "Nordeste"),
    "DF": (53, "Distrito Federal", "Centro-Oeste"),
    "ES": (32, "Espírito Santo", "Sudeste"),
    "GO": (52, "Goiás", "Centro-Oeste"),
    "MA": (21, "Maranhão", "Nordeste"),
    "MT": (51, "Mato Grosso", "Centro-Oeste"),
    "MS": (50, "Mato Grosso do Sul", "Centro-Oeste"),
    "MG": (31, "Minas Gerais", "Sudeste"),
    "PA": (15, "Pará", "Norte"),
    "PB": (25, "Paraíba", "Nordeste"),
    "PR": (41, "Paraná", "Sul"),
    "PE": (26, "Pernambuco", "Nordeste"),
    "PI": (22, "Piauí", "Nordeste"),
    "RJ": (33, "Rio de Janeiro", "Sudeste"),
    "RN": (24, "Rio Grande do Norte", "Nordeste"),
    "RS": (43, "Rio Grande do Sul", "Sul"),
    "RO": (11, "Rondônia", "Norte"),
    "RR": (14, "Roraima", "Norte"),
    "SC": (42, "Santa Catarina", "Sul"),
    "SP": (35, "São Paulo", "Sudeste"),
    "SE": (28, "Sergipe", "Nordeste"),
    "TO": (17, "Tocantins", "Norte"),
}

