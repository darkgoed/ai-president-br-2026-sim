# Comparação política v1 — relatório (17/10/2026)

Resultado: **ranking geral BLOQUEADO. Nenhum vencedor.** Isso é resultado computado (`python -m src.comparison`),
não escolha editorial: o protocolo exige o mesmo conjunto de indicadores aplicável a todos, e o conjunto atual falha
em dois pontos independentes.

## O que foi fixado antes de pontuar

- Protocolo: `research/comparison_protocol_v1.json` (cinco dimensões, 20% cada — escolha editorial, não neutralidade).
- Plano de mensuração: `research/measurement_plan_v1.json` — 6 indicadores com medida, unidade, direção, população,
  horizonte, denominador, fonte, transformação, incerteza, justificativa e risco de viés.
- Hashes congelados: `research/comparison_v1_freeze.json` (protocolo + plano + `src/comparison.py`; teste
  `test_frozen_hashes_match`). Fixado antes **desta** rodada de pontuação; o corpus de planos e as séries
  já tinham sido vistos em rodadas anteriores — não é pré-registro independente.
- Universo: as 12 candidaturas **DEFERIDAS** no registro do TSE gerado em 15/10/2026 (`research/electoral_register.json`).
  O arquivo de planos tem mais dois documentos: Leonardo Avalanche (RENÚNCIA) e Pablo Marçal (substituído, situação
  #NULO). Ficam preservados em `research/program_manifest.json` como contexto, sem nota — a regra de universo foi
  aplicada, não escolhida depois de ver resultado.
- Unidade: candidatura — partido verificado na data de corte. Não é ranking de partidos.

## Coleta uniforme: histórico eleitoral oficial (mesma regra para os 12)

`tools/collect_mandate_history.py` varre TODOS os arquivos `consulta_cand_<ano>.zip` do TSE de 1994 a 2024 (16 eleições,
3.682.286 linhas). Chave: título eleitoral do registro 2026 (usado só em memória,
nunca gravado); só quando a linha histórica não divulga o título, nome civil sem acento + data de nascimento. Linhas APTO sem
situação de totalização (#NULO no TSE) são resolvidas pela mesma regra para todos: vice herda o titular da chapa;
titular majoritário pelos votos nominais do arquivo oficial `votacao_candidato_munzona` (caso único: Lula 2006,
2º turno, 58.295.042 de 95.838.220 votos nominais). O valor original fica em `consulta_cand_status`.
Nenhum erro HTTP; nenhuma colisão nome+nascimento com outro título.

| Candidatura — partido (corte) | SQ_CANDIDATO | registros | eleito p/ executivo titular | outros cargos eleitos |
|---|---|---|---|---|
| SAMARA — UP | 280002538811 | 2 | — | — |
| ZEMA — NOVO | 280002539826 | 3 | 2018 Governador MG, 2022 Governador MG | — |
| RENAN SANTOS — MISSÃO | 280002540694 | 0 | — | — |
| HERTZ DIAS — PSTU | 280002541457 | 4 | — | — |
| LULA — PT | 280002542548 | 8 | 2002 Presidente BR, 2006 Presidente BR, 2022 Presidente BR | — |
| VETERINÁRIO WILSON GRASSI — DEMOCRATA | 280002548139 | 3 | — | — |
| FLAVIO BOLSONARO — PL | 280002551544 | 6 | — | 2002 Deputado Estadual RJ, 2006 Deputado Estadual RJ, 2010 Deputado Estadual RJ, 2014 Deputado Estadual RJ, 2018 Senador RJ |
| ESCRITOR AUGUSTO CURY — AVANTE | 280002551547 | 0 | — | — |
| RONALDO CAIADO — PSD | 280002551932 | 8 | 2018 Governador GO, 2022 Governador GO | 1998 Deputado Federal GO, 2002 Deputado Federal GO, 2006 Deputado Federal GO, 2010 Deputado Federal GO, 2014 Senador GO |
| EDMILSON COSTA — PCB | 280002551975 | 4 | — | — |
| CLARIANA BARAO — DC | 280002552484 | 0 | — | — |
| RUI COSTA PIMENTA — PCO | 280002552487 | 7 | — | — |

| ano | linhas lidas | sem título (usa nome+nascimento) | sem título e sem nascimento | sha256 do zip |
|---|---|---|---|---|
| 1994 | 12.035 | 12.035 | 21 | `98d72c20fa4ad666…` |
| 1996 | 321.790 | 321.790 | 118.551 | `77ef54dd5d1c20d4…` |
| 1998 | 15.092 | 87 | 0 | `1101b90cf23dbbd6…` |
| 2000 | 399.455 | 766 | 0 | `f1b29fa847acd74c…` |
| 2002 | 18.109 | 318 | 0 | `33876c4d988c17f7…` |
| 2004 | 402.157 | 302 | 0 | `917c224c0c5de85b…` |
| 2006 | 19.303 | 0 | 0 | `6f5c0cf7ae808778…` |
| 2008 | 382.079 | 1 | 0 | `5bb3f77e70495acb…` |
| 2010 | 22.577 | 0 | 0 | `761c8eb2683b0ccd…` |
| 2012 | 483.741 | 1.122 | 1.122 | `bf205075f34b7f04…` |
| 2014 | 26.263 | 0 | 0 | `ad31cc36d9a6c89e…` |
| 2016 | 498.391 | 109 | 109 | `9fd0066979b45172…` |
| 2018 | 29.287 | 108 | 108 | `57f6881f1aa03614…` |
| 2020 | 558.804 | 284 | 284 | `8079b01adfa406eb…` |
| 2022 | 29.322 | 29 | 29 | `7dcefc266347ce0f…` |
| 2024 | 463.881 | 47 | 46 | `aa6b3cf9dbbc9158…` |

Lacuna de cobertura: 120.270 linhas (quase todas de 1996, municipal) não têm título nem nascimento e não podem ser
atribuídas com segurança. Nelas, nenhuma linha tem nome civil igual ao de qualquer dos 12 (`name_only_unverifiable`
vazio): não há sinal de mandato desses perfis na lacuna — mas é checagem por nome, não identificação, e não pega
mudança de nome.

"Eleito" é totalização do TSE: não prova exercício integral, renúncia, licença nem desempenho. O CDN do TSE responde 404 para
`consulta_cand_1988/1989/1990/1992.zip` (conferido em 17/10/2026); um cargo eleito antes de 1994 não aparece aqui.

## Por que o ranking trava

1. **Resultados históricos e execução verificada (40% do peso) não são comparáveis para o conjunto.** O plano exige o
   mesmo cargo executivo titular para todos. 9 dos 12 nunca foram eleitos prefeito, governador ou presidente
   (1994–2024); os 3 que foram ocuparam cargos diferentes (Presidência × dois governos estaduais). Ausência de
   mandato não vira zero nem desvantagem; ela torna a dimensão não comparável e o protocolo bloqueia o ranking.
   Uma subcomparação Zema × Caiado (governadores 2019–2026) seria possível pelo plano, mas não foi coletada nem
   publicada — e não diria nada sobre os outros dez.
2. **Viabilidade fiscal, evidência das propostas e prestação de contas (60%) não têm nenhuma célula revisada.**
   Os três indicadores exigem dupla codificação humana dos 12 planos integrais com manual versionado. Ela não existe.
   Contagem de termos, páginas, citações ou números é só triagem e não vira nota; o ranking documental legado
   (`research/ranking_protocol.json`) e o catálogo de excertos (`research/candidates/`) não são insumos.

Matriz: `results-comparison-v1/matrix.csv` (72 células = 12 × 6, **0 com nota**, todas `null` com status
`not_comparable_for_set` ou `missing_evidence`). Sensibilidade à grade de pesos (126 vetores, passo 0,1, mínimo 0,1) e
leave-one-out estão implementados e testados com dados sintéticos, mas não rodam sobre dados reais porque a matriz
não é elegível — nenhum "primeiro em X% das combinações" é publicado.

## O que falta para poder existir um ranking

- Mudar o desenho (nova versão do protocolo, com motivo) para dimensões aplicáveis a quem nunca governou, OU aceitar
  que histórico/execução fiquem fora e declarar isso como ranking de outra coisa (planos, não gestão).
- Manual de codificação + dupla codificação humana independente dos 12 planos integrais, com kappa.
- Para cada célula: URL, hash, página/ponteiro, valor bruto, fórmula e revisão registrada (`score_record_required_fields`).

## O bilhão macroeconômico é separado

`results-1b-streaming-v2/` (verificado: replay com outro tamanho de lote, contagens e hashes idênticos): em 4 anos,
dívida/PIB subiu em 811.043.175 de 1.000.000.000 cenários (81,10%); desocupação caiu em 59,60%; IBC-Br subiu em
68,01%; os dois últimos juntos em 50,82%. Eventos sobrepostos, não somam. São frequências de cenários comuns a todos,
não chance real e não diferenciam candidaturas; não entram na comparação (teste
`test_billion_and_legacy_rankings_are_not_inputs`). O backtest perdeu para previsões simples em vários indicadores.

## Testes (115 passando)

`tests/test_comparison.py`: dados atuais recusam vencedor; nenhuma célula vira zero; evidências idênticas empatam
os 12; uma célula faltante bloqueia; registro não revisado (ex.: sugestão de LLM) é ignorado; trocar nome/partido/ordem
não muda nota por ID; grade de pesos = 126 vetores válidos; o bilhão e rankings legados não são insumo; histórico
sem título/CPF/e-mail/nascimento; universo = registro DEFERIDO; hashes congelados conferem.

## Uso de modelo

Planejamento, código e redação feitos com Claude Opus 5.5 (Anthropic) via Hermes. Nenhuma nota foi preenchida por
modelo; todos os números deste relatório saem dos scripts acima e dos arquivos oficiais citados. Nada disto certifica
ausência de viés: pesos, regra de mesmo cargo e escolha de indicadores são decisões editoriais contestáveis, descritas
com seus riscos no plano de mensuração.

## Reproduzir

```
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python tools/collect_mandate_history.py   # baixa ~1,6 GB do CDN do TSE para .cache/ (não versionado)
.venv/bin/python -m src.comparison                  # gera results-comparison-v1/
.venv/bin/python -m pytest -q
```
Para testar outros pesos: editar `weights` em `research/measurement_plan_v1.json` (nova versão + novo freeze).
