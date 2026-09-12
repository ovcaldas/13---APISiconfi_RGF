# Panorama da Despesa com Pessoal — RGF 2015–2025

Projeto Python para coletar, tratar e analisar o Anexo 01 do Relatório de Gestão Fiscal (RGF) das 27 unidades da Federação por meio da API oficial do SICONFI.

## Escopo metodológico

- Poder analisado: **Executivo estadual** (`co_esfera=E`, `co_poder=E`). A API exige um poder; somar os poderes duplicaria a RCL e misturaria limites legais distintos.
- Período: 2015 a 2025, usando o 3º quadrimestre ou o último quadrimestre anterior disponível.
- Demonstrativo: `RGF-Anexo 01`, RGF quadrimestral.
- Denominador: RCL ajustada para cálculo dos limites da despesa com pessoal; a RCL sem ajustes também é preservada.
- Ausências permanecem nulas. Nenhuma observação é fabricada ou substituída por zero.
- Os percentuais e limites declarados no RGF têm prioridade. O cálculo `100 × DTP / RCL ajustada` é usado apenas quando o percentual não estiver disponível.

## Score fiscal (0–100)

Cada componente é transformado em posição percentílica entre as 27 UFs (maior sempre significa melhor):

`100 × [30% nível médio do DTP/RCL + 20% margem prudencial + 15% margem máxima + 15% baixa recorrência de alerta + 10% tendência recente favorável + 10% baixa volatilidade]`.

Para nível, recorrência, tendência e volatilidade, valores menores recebem percentil maior. Para as margens, valores maiores recebem percentil maior. Um componente ausente recebe posição neutra (0,5). Os grupos são os terços do score: Grupo 1 (superior), Grupo 2 (central), Grupo 3 (inferior). O score é comparativo e não substitui o enquadramento legal do RGF.

## Execução

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run_pipeline.py
```

Para reprocessar os dados já baixados sem consultar novamente a API:

```powershell
python -m rgf.pipeline --sem-download
```

No VS Code, selecione o kernel `.venv` e abra os notebooks em `notebooks/`.

## Saídas

- `dados/rgf_estados_2015_2025_raw.csv`: resposta bruta concatenada da API.
- `dados/rgf_estados_2015_2025_tratado.csv`: uma linha por UF/ano, incluindo combinações ausentes.
- `dados/rgf_estados_2015_2025.xlsx`: abas analíticas solicitadas.
- `dados/estrutura_chamada_teste.json` e `dados/amostra_chamada_teste.csv`: evidência da chamada exploratória.
- `dados/auditoria_coleta.csv` e `dados/auditoria_mapeamento.csv`: falhas, ausências e rastreabilidade semântica.
- `dados/panorama_executivo.txt`: síntese executiva automática.
- `graficos/`: oito visualizações em PNG.
- `logs/coleta_rgf.log`: log detalhado de coleta.

Fonte: [API SICONFI — Tesouro Nacional](https://apidatalake.tesouro.gov.br/docs/siconfi#/RGF/get_rgf).

