import math

import pandas as pd

from rgf.treatment import build_treated, parse_number


def test_parse_number_pt_br():
    assert parse_number("1.234,56") == 1234.56
    assert parse_number(12.3) == 12.3
    assert math.isnan(parse_number("-"))


def test_mapping_uses_declared_percentage():
    common = {"exercicio": 2025, "uf": "SP", "populacao": 10, "periodo": 3}
    raw = pd.DataFrame([
        {**common, "cod_conta": "ReceitaCorrenteLiquidaAjustada", "conta": "RCL ajustada", "coluna": "Valor", "valor": "200,00"},
        {**common, "cod_conta": "DespesaComPessoalTotal", "conta": "DESPESA TOTAL COM PESSOAL", "coluna": "Valor", "valor": "80,00"},
        {**common, "cod_conta": "DespesaComPessoalTotal", "conta": "DESPESA TOTAL COM PESSOAL", "coluna": "% sobre a RCL Ajustada", "valor": "39,50"},
        {**common, "cod_conta": "LimiteDeAlertaDespesaComPessoalTotal", "conta": "LIMITE DE ALERTA", "coluna": "% sobre a RCL Ajustada", "valor": "44,10"},
        {**common, "cod_conta": "LimitePrudencialDespesaComPessoalTotal", "conta": "LIMITE PRUDENCIAL", "coluna": "% sobre a RCL Ajustada", "valor": "46,55"},
        {**common, "cod_conta": "LimiteMaximoDespesaComPessoalTotal", "conta": "LIMITE MÁXIMO", "coluna": "% sobre a RCL Ajustada", "valor": "49,00"},
    ])
    base, _ = build_treated(raw, save=False)
    row = base.query("ano == 2025 and UF == 'SP'").iloc[0]
    assert row["DTP_RCL"] == 39.5
    assert row["DTP_RCL_Calculado"] == 40.0
    assert row["situacao_fiscal"] == "confortável"
