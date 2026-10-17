# Presidente IA — Brasil 2026

Experimento educacional do Tour Cyber: pesquisa documental das 12 candidaturas com votos válidos no primeiro turno de 2026 e benchmark numérico reproduzível. Não é previsão eleitoral, avaliação causal de governos ou recomendação de voto.

## Comparação política v1 (17/10/2026): ranking bloqueado

Protocolo e plano de mensuração explícitos (`research/comparison_protocol_v1.json`,
`research/measurement_plan_v1.json`, hashes em `research/comparison_v1_freeze.json`) aplicados às 12 candidaturas
deferidas. Resultado computado por `python -m src.comparison` (`results-comparison-v1/`): **nenhum vencedor**.
9 dos 12 nunca foram eleitos prefeito, governador ou presidente nos arquivos oficiais do TSE de 1994 a 2024
(`tools/collect_mandate_history.py`, `research/mandate_history_v1.json`), e os indicadores dos planos exigem dupla
codificação humana que ainda não existe; 0 de 72 células têm nota. Detalhes, limites e como contestar os critérios:
`research/RELATORIO-COMPARACAO-V1.md`. O bilhão de cenários macro (`results-1b-streaming-v2/`) é comum a todos e não
entra na comparação.

As pastas `results-100k/`, `results-1m*/` e `results-integrated*/` (100–300 MB cada) não são versionadas; são
regeneráveis pelos comandos abaixo.

## Resultado científico

A pesquisa documenta propostas, mas não identifica efeitos causais comparáveis para os 12 programas. Portanto não há vencedor, ranking de desempenho governamental nem empate político. O ranking documental anterior foi descontinuado e desativado por padrão: seleção desigual de excertos e pesos editoriais não sustentam superioridade política. Permanece apenas para auditoria histórica. Ausência de efeito identificado não é efeito zero.

O padrão atual é 100.000 trajetórias hipotéticas comuns de dinâmica de dívida em quatro anos, em oito famílias balanceadas. Os 12 perfis são avaliados frente às mesmas condições; isso corresponde a 1.200.000 avaliações perfil/cenário, NÃO a 1.200.000 mundos independentes nem a governos previstos. A publicação original de 1.000 trajetórias foi preservada em `results/`. Os resultados políticos de renda, emprego, inflação, segurança, saúde e educação permanecem desconhecidos.

## Versão auditada: análise, métricas e evidências ampliadas

Entrega atual: `results-integrated-v4/analysis/RELATORIO.md` e
`results-integrated-v4/dashboard.html`. Sem redesign; o trabalho é nos dados,
contratos de validação, métricas e verificabilidade. Pastas anteriores são
histórico, não versões intercambiáveis da compilação atual.

- 29.467 registros classificados; não são 29.467 indicadores independentes.
- 68 datasets públicos validados contra respostas e definições arquivadas;
  13 novos datasets foram coletados em `research/public-extension-v2/`.
- 308 grupos de séries/territórios/classificações, com faltantes e zeros separados.
- 9.660 comparações descritivas com o mesmo período do ano anterior, sem
  imputação de unidade, sem trocar trimestre por mês ou variação por causalidade.
- 48 distribuições de métricas derivadas da simulação: 12 medidas nos quatro
  horizontes anuais (inflação acumulada/anualizada, IBC-Br acumulado/anualizado,
  dívida/desocupação em pontos percentuais, picos e drawdown nos pontos anuais,
  poder de compra de uma quantia nominal fixa — não renda real das famílias).
- Backtests prespecificados de 12/24/48 meses, respectivamente 9/4/2 cortes,
  com baseline sem mudança e drift treinado só no passado; MAE, RMSE, viés,
  CRPS, cobertura 50/80/95%, interval score e faixa de Wilson para cobertura.
- 199 citações conferidas nas páginas dos PDFs; 864 páginas de 14 documentos
  do arquivo oficial, incluindo dois fora dos 12 perfis configurados, mantidos
  como contexto e sem inventar novas identidades/perfis ou previsões políticas.

As cinco falhas da auditoria foram corrigidas: valor normalizado divergente é
rejeitado; identidades SGS/metadados/resumos são validados; destinos ocupados
são recusados antes de nova análise; o verificador aceita modos com/sem ranking;
bootstrap informa sorteios e sequências distintas separadamente. O gate de
publicação exige os 12 perfis configurados e as fontes obrigatórias.

```sh
# Exemplos de reprodução: use destinos novos em cada rodada.
python tools/extend_public_catalog.py --out research/public-extension-novo
python -m src.cli empirical --runs 1000000 --batch-size 10000 --seed 20261015 --out results-1m-novo
python -m src.cli integrate --simulation-dir results-1m-novo --public-catalog research/public-extension-novo/public_catalog.json --out results-integrated-novo
python tools/verify_empirical.py results-1m-novo
python tools/verify_knowledge.py results-integrated-novo
python -m pytest -q
# Sondas adversariais da versão entregue, só em cópias temporárias:
python tools/audit_analysis.py
```

`verify_knowledge.py` revalida as transformações contra os bytes originais e
reproduz os novos cálculos/backtests/CSVs. Não apenas compara hashes entre
artefatos que poderiam compartilhar o mesmo erro. Os hashes também não são
assinaturas criptográficas dos produtores externos.

Os datasets `wb-EN.ATM.CO2E.PC` e `wb-SH.UHC.SRVS.CV.XD` têm lacunas de
coleta registradas; não foram substituídos por indicadores parecidos. As séries
históricas antigas sem resposta bruta preservada ficam como contexto, não como
novas observações autenticadas. Nenhum score agregado de candidatos foi criado.

A melhoria não significa validação preditiva: o bootstrap perde para baselines
em vários indicadores, especialmente em quatro anos, onde há só dois cortes.
Os dados novos não viraram coeficientes causais por candidatura. Resultados ruins
e limitações ficam expostos; mais registros não tornam o modelo imparcial ou preciso.

## Base integrada anterior — histórico sem efeitos inventados

Abra `results-integrated/dashboard.html`: navegador offline com pesquisa,
filtros por candidatura/tipo, paginação, conteúdo original e proveniência.
A compilação atual contém 19.021 registros classificados, 102 snapshots/fontes
locais e as 788 páginas dos 12 planos. Registros não são indicadores distintos
nem observações independentes: fontes e períodos podem se repetir.

O catálogo ampliado inclui IBGE (Brasil e UFs), RREO/Siconfi (União e todas
as 27 UFs) e indicadores do Banco Mundial. Uma consulta ambiental
`EN.ATM.CO2E.PC` falhou; a lacuna aparece no manifesto. Unidades ausentes,
supressões e campos desconhecidos não são completados artificialmente.
Declarações oficiais comprovam o registro da fala, não sua veracidade ou entrega.
Entrevistas, debates e discursos externos ainda não foram checados integralmente.
Não se alega ter reunido todo o conhecimento disponível nem eliminado todo viés.

```sh
python tools/collect_public_catalog.py  # opcional; consulta rede
python -m src.cli integrate --out results-integrated-novo
python tools/verify_knowledge.py results-integrated-novo
python tools/query_evidence.py results-integrated-novo/evidence.sqlite --text saúde --limit 25
```

Use destino novo para preservar versões: a integração recusa sobrescrever uma
base existente. SQLite/FTS5, `records.jsonl`, `sources.jsonl` e `manifest.json`
permitem inspecionar hashes, ponteiros e classificações. A integração referencia
o milhão de trajetórias de `results-1m`, sem alterá-lo. Só as quatro séries
históricas explicitadas no modo empírico calibram suas equações; o restante é
evidência contextual, não coeficiente causal. O registro bloqueia vínculo de
indicador observado/simulado com candidatura. Isso é uma proteção de modelo
de dados, não uma demonstração de imparcialidade ou veracidade de cada texto.

## Instalação e execução

Requer Python 3.14 e NumPy fixado. Sem APIs de IA durante as simulações.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m src.cli research
python -m src.cli validate
python -m src.cli analyze --runs 100000 --seed 20261015 --use-observed-debt --out results-100k
python -m src.cli sensitivity --runs 1000 --seed 20261015
python -m src.cli simulate --scenario fiscal --out results-fiscal
python -m src.cli report
python -m src.cli export
python -m pytest -q
```

Exportação: `results/results.json`, `trajectories.csv`, `profiles.csv`, `report.md`, `report.txt` e `sensitivity.json`. CSV de perfis deixa efeitos vazios e identifica a ausência; não grava zero.

## Indicadores oficiais e painel de cenários

A extensão de métricas acrescenta 12 séries oficiais do BCB/SGS: IPCA mensal,
IPCA em 12 meses, meta Selic, dólar de venda, dívida bruta em % PIB e em reais,
desocupação PNADC, IBC-Br ajustado, estimativa BCB de PIB mensal, Selic mensal,
juros de crédito e inadimplência acima de 90 dias. Os metadados SGS identificam
o produtor original (incluindo IBGE). Cada série traz referência, unidade,
frequência, até 20 observações, valor anterior, variação absoluta na unidade
original, média, mínimo e máximo da janela. Janelas diárias não são mensais;
períodos correntes podem estar incompletos. Não comparar índices de bases distintas.

```sh
python -m src.cli refresh-data
python -m src.cli simulate --runs 1000 --seed 20261015 --use-observed-debt --out results-metrics
```

Abra `results-metrics/dashboard.html` no navegador. O painel local inclui
gráficos, 90 métricas contábeis de cenário (38 do horizonte e 52 anuais), tabela anual e famílias de stress.
Também são exportados `metrics.csv` e `observed.csv`. Não requer servidor,
bibliotecas de gráficos, chaves de API ou novas dependências de execução.
Os resultados publicados originalmente em `results/` não são sobrescritos
pelo comando acima.

`refresh-data` consulta a rede explicitamente e grava `data/observed.json`,
com resposta original, URL, hash SHA256 e horário de coleta. A simulação usa
esse snapshot offline; não o atualiza silenciosamente. Fontes indisponíveis
são listadas como erros, nunca preenchidas com números artificiais; falha
total preserva o snapshot anterior. A coleta Selic exclui datas futuras.

`--use-observed-debt` usa apenas a última dívida bruta oficial como estoque
inicial (percentual convertido em fração). Sem a opção, o benchmark original
continua com dívida inicial hipotética. Juros efetivos, crescimento nominal,
primário e choques continuam hipóteses em ambos os casos: **isto não é uma
previsão calibrada**. Selic não substitui juros efetivos, IPCA não substitui
crescimento nominal e IBC-Br não substitui PIB. As frequências de dívida
acima de 80/90/100/120% são frequências no laboratório, não probabilidades
reais nem limites legais. O primário estabilizador e o custo dos juros são
identidades condicionais; não são custos estimados de programas políticos.

## Ranking documental descontinuado — histórico de 100 mil análises

Esta seção descreve a execução histórica, não o padrão atual. `analyze` agora
não gera ranking documental. Apenas reprodução explicitamente solicitada com
`--legacy-documentary-ranking` o habilita, com aviso de descontinuação.
Os artefatos anteriores não foram apagados nem suas notas ajustadas.

```sh
# Recoleta de histórico institucional e séries IBGE (opcional; requer rede):
python tools/research_governments.py
# Análise completa com snapshots locais, sem IA ou rede durante as simulações:
python -m src.cli analyze --runs 100000 --seed 20261015 --use-observed-debt --out results-100k
```

Abra `results-100k/dashboard.html`. Contagens separadas:

- 100.000 trajetórias macroeconômicas comuns, 1.200.000 avaliações perfil/cenário.
- 100.000 análises de pesos documentais, 1.200.000 avaliações candidato/pesos.
- 60 indicadores documentais por candidatura: seis critérios em dez eixos.
- Nove séries históricas IBGE: desocupação trimestral, renda real do trabalho
  e PIB nominal para Brasil, Minas Gerais e Goiás. Somadas às 12 séries SGS,
  são 21 séries observadas, não 21 efeitos de governo.

O ranking mede **especificação detectada na seleção auditada**, não qualidade,
viabilidade, impacto, preferência eleitoral ou desempenho futuro de governo.
Os critérios são compromisso quantificado, prazo, envelope de recursos declarado,
instrumento, monitoramento e base de comparação. Não pontua tamanho da promessa,
número de citações, tamanho do PDF, partido, votos ou histórico pessoal.
As detecções de instrumento/monitoramento/base são heurísticas textuais, não
uma avaliação jurídica ou confirmação de implementação. Cada detecção mostra
excertos, IDs e páginas para inspeção.

Nota exibida: pesos iguais nos eixos comuns revisados e critérios. Sensibilidade:
pesos independentes Dirichlet(1), PCG64, seed publicada e lotes fixos. Empates
compartilham posição e crédito de primeiro lugar. As faixas são posições
observadas nas análises de pesos, não intervalos de confiança. Frequência de
primeiro lugar **não é chance de eleição nem sucesso de governo**.

Critério não detectado = nenhuma detecção nesta seleção, não ausência no
plano integral ou efeito zero. Eixo não revisado = `null`, excluído da nota de
todos os candidatos para manter o denominador comum. A seleção desigual dos
excertos pode mudar posições; a normalização não resolve esse viés. Por isso
o ranking é exploratório e não sustenta conclusão de “melhor presidente”.

Protocolo: `research/ranking_protocol.json`. Pesquisa e limitações:
`research/ANALISE-AMPLIADA.md`. Histórico e proveniência:
`research/government_history.json`. TCU, TCE-GO, TCE-MG, Senado, Inep e
metadados IBGE contextualizam a análise; pareceres de exercícios diferentes
não viram uma nota comum. Histórico territorial não entra no ranking, pois
competências, períodos, choques, sucessores e escalas são diferentes.

Novos arquivos: `ranking.csv`, `ranking.json`, `ranking_indicators.csv` e
`history.csv`. `analysis_id` cobre ranking, protocolo, histórico e snapshot
observado; `run_id` continua identificando o benchmark macro. O comando
`simulate` mantém somente o benchmark, sem incluir ranking documental.

## Modo empírico em lotes — execução de um milhão

```sh
python tools/collect_empirical.py
python tools/collect_expanded_evidence.py
python -m src.cli empirical --runs 1000000 --batch-size 10000 --seed 20261015 --out results-1m
python tools/verify_empirical.py results-1m
```

Abra `results-1m/dashboard.html`. Este modo é **distinto** do benchmark fiscal
artificial e do ranking documental: não reutiliza suas notas como coeficientes.
O comando mantém os resultados antigos intactos e recusa sobrescrever um
destino que já contenha `paths.npy`. Para repetir, use outra pasta de saída.

Calibração: histórico oficial mensal SGS/BCB de dívida bruta (% PIB),
desocupação PNADC (trimestre móvel), IBC-Br dessazonalizado e IPCA mensal.
`data/empirical_monthly.json` conserva respostas originais, URLs e SHA256.
O recorte comum observado desta coleta tem 174 meses, de 2012-03 a 2026-08,
gerando 162 blocos móveis sobrepostos de 12 meses. Não interpola meses ausentes.

Sorteiam-se quatro blocos anuais por trajetória, conjuntamente nas quatro
variáveis, com reposição. Isso preserva a associação dentro de cada bloco,
mas não dependência entre blocos ou regimes estruturais. Dívida e atividade
usam variações logarítmicas, desocupação usa logit e inflação mensal compõe
um índice de preços com início em 100. Não há corte arbitrário de limites de
desemprego nem substituição de Selic por juros efetivos. A dívida neste modo
é reamostrada historicamente, **não** calculada pela identidade fiscal.

As trajetórias anuais completas são gravadas em `paths.npy` (float64,
formato `[trajetória, ano 0..4, indicador]`); `block_indices.npy` guarda os
blocos sorteados. Há progresso por lote em `progress.json` e resumo leve em
`empirical_results.json`/`summary.csv`. O snapshot calibrador é arquivado em
`calibration_snapshot.json`. A verificação reproduz TODAS as trajetórias
em lotes de tamanho diferente, confere hashes, contagens e estatísticas.

O backtest por origem móvel usa somente blocos anteriores ao alvo, com
treino inicial de 60 meses, alvos anuais não sobrepostos de 12 meses e 2.000
trajetórias por origem. Compara MAE/RMSE/viés/cobertura a repetir o nível
inicial (para preços, isso corresponde a inflação futura zero). Usa a edição
atual revisada dos dados: é pseudo-fora-da-amostra, não teste em tempo real.
Nesta coleta, foram nove origens. O modelo ficou pior que esse baseline para
dívida e desemprego; não se escondeu esse resultado ou ajustaram parâmetros
após observar o teste. Um teste de 12 meses não valida previsão de quatro anos.

Pesquisa adicional: `research/expanded_evidence.json` inclui busca automatizada
uniforme nas 788 páginas dos 12 planos, nove RREO-Anexo 14 (União, MG e GO;
2018/2022/2025), três indicadores sociais do Banco Mundial e registro de acesso
a IFI, Inep, DATASUS, Câmara e Senado. Consultar um portal não equivale a auditar
microdados, toda a atuação parlamentar ou a execução de cada promessa.
Os trechos recuperados dos planos são **menções para revisão**, podendo conter
negações e diagnósticos; não são promessas automaticamente validadas. As contas
Siconfi são nominais e dependem de esfera/competência; não constituem notas
comparáveis de governantes. Indicadores sociais adicionais e fontes jurídicas
entram como contexto auditável, não coeficientes nas quatro variáveis.

Esta entrega alimenta o simulador com histórico observado e amplia o corpus de
evidências, mas não fabrica efeitos diferenciais dos programas. Não há ranking
de desempenho governamental neste modo. Um milhão de trajetórias reduz ruído
numérico do bootstrap, não corrige hipótese de estacionariedade, viés das
fontes ou falha no backtest.

## Diagnósticos de fragilidade e erro numérico

`simulate` e `analyze` incluem diagnósticos automaticamente. Para acrescentá-los
a uma execução já salva, sem executar novas trajetórias nem alterar o ranking:

```sh
python -m src.cli diagnose --out results-100k
python tools/verify_analysis.py results-100k
```

O painel ganha a seção “Fragilidade e erro numérico”; arquivos completos em
`diagnostics.json` e `diagnostics.csv`.

- Erro-padrão Monte Carlo da **média do laboratório**, respeitando as famílias
  de stress como estratos: `sqrt(sum(w_h² * s_h² / n_h))`.
- Meia largura normal aproximada de 95% (`1,96 × SE`), estritamente sobre esse
  erro numérico, não sobre futuros governos. Famílias com menos de duas
  trajetórias deixam o erro como desconhecido; famílias pequenas recebem aviso.
- Convergência com prefixos de 100, 1.000, 10.000, 50.000 e total de trajetórias,
  quando disponíveis. Prefixos da mesma execução não são réplicas independentes.
- Retirada de um eixo ou critério documental por vez: posições, deslocamentos
  e mudanças do conjunto líder. Empates continuam compartilhados.
- Dominância entre detecções documentais, sem atribuir superioridade política.
- Idade do snapshot, datas originais das séries, erros de coleta, valores
  inválidos e contagem dos resultados políticos que continuam desconhecidos.

O diagnóstico informa explicitamente que não há backtest preditivo disponível
nem calibração causal identificada nesta pipeline. Não calcula “chance de erro
real” nem um percentual de confiança em candidatos. Uma hipótese artificial
determinística pode ter erro Monte Carlo zero e continuar errada sobre o mundo.
Dias desde a referência não são atraso de publicação: séries mensais podem
usar o primeiro dia do mês e cada fonte tem seu calendário.

Os diagnósticos registram a data de avaliação, `source_run_id` e
`source_analysis_id`. Recalcular idades noutra data não muda os resultados da
simulação original. Para reduzir erro de previsão, seria necessário adicionar
backtests temporais contra dados observados, baselines, calibração e validação
fora da amostra — não apenas mais indicadores ou mais execuções.

## Pesquisa e fontes

O TSE fornece cadastro, situação complementar, planos depositados e resultado eleitoral. Os identificadores foram cruzados; registros substituídos/renunciantes e turnos duplicados não viraram candidaturas adicionais. Os votos foram somados e os percentuais recalculados com aritmética decimal. Dados pessoais não necessários foram excluídos.

- `research/candidates/`: doze dossiers com citações e referências a páginas dos PDFs.
- `research/program_manifest.json`: membro ZIP, páginas e SHA256 de cada plano.
- `research/electoral_register.json`: somente campos eleitorais necessários.
- `research/first_round.json`: votos reais, exclusivamente eleitorais.
- `research/electoral_sources.json`: URLs, horários e hashes da coleta.
- `research/impacts.json`: compromissos, canais condicionais, custos/lacunas, viabilidade, efeitos colaterais e evidência contextual para quatro anos.
- `research/audit.md` e `audit_checks.json`: critérios, correções e decisão do gate.

Fontes originais:

- https://dadosabertos.tse.jus.br/dataset/candidatos-2026
- https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2026.zip
- https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand_complementar/consulta_cand_complementar_2026.zip
- https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip
- https://resultados.tse.jus.br/oficial/ele2026/6257/dados/br/br-c0001-e006257-u.json
- https://www.imf.org/external/pubs/ft/tnm/2010/tnm1002.pdf

Estudos Ipea e a tabela Receita Federal de 2026 constam de `research/empirical_sources.json`. Estudo histórico não é coeficiente transportável automaticamente. Tentativas de consulta BCB e fontes indisponíveis não calibram o modelo.

## Hipóteses e interpretação

`data/model.json` fixa hipóteses artificiais de stress antes das execuções. Não são valores observados do Brasil nem probabilidades calibradas. A identidade contábil usa juros nominais efetivos sobre estoque, crescimento NOMINAL do PIB e superávit primário positivo. Dívida e primário são frações do PIB; saída de dívida é % do PIB. Não substituir crescimento nominal por real, nem juros efetivos por Selic sem justificativa.

Há independência artificial entre variáveis/anos; faltam câmbio, ajustes patrimoniais e feedback macroeconômico. Os quantis descrevem a distribuição simulada, não intervalos de confiança sobre governos futuros.

`data/strategies.json` usa o mesmo esquema para os 12 nomes. Propostas qualitativas e metas declaradas não viram coeficientes. O motor rejeita efeitos políticos preenchidos sem modelo identificado. Pesos alternativos não fabricam resultados sociais ausentes; por isso não há índice composto de resultados de governo. O ranking documental separado compara detecções no corpus, não altera efeitos políticos e pode mudar sob pesos editoriais.

Os compromissos também estão preservados nos snapshots documentais de `data/strategies.json` e `research/impacts.json`. Esses snapshots correspondem à versão usada na execução publicada. Campos numéricos documentais complementares (unidades, metas e horizontes) foram posteriormente explicitados nos dossiers `research/candidates/`, que são a referência atual para essa catalogação. Isso não preenche efeitos causais nem altera as trajetórias; uma meta de dez anos não foi dividida para fabricar entrega em quatro anos.

## Reprodutibilidade e testes

Verifique novamente os 199 excertos nos PDFs oficiais com `python tools/verify_sources.py` (requer rede). A ferramenta confere hashes e páginas; mudanças posteriores da fonte são reportadas. `evidence/terminal.png` é uma renderização literal de stdout real, não uma foto de emulador GUI. O log e o hash acompanham a imagem. Para regenerar, instale Pillow e execute `python tools/capture_terminal.py`.

Seed padrão 20261015; gerador PCG64. Mesmo ambiente, configuração e seed reproduzem os mesmos resultados. `run_id` inclui hashes dos insumos. Alterar nomes/partidos/ordem não altera trajetória numérica, embora o hash documental mude. Testes verificam fórmula analítica, sinal, unidades, seed, simetria, lacunas, pesos, sensibilidade, votos, exportação e contagens. Resultados de robustez ficam separados da execução principal.

## Limitações documentais

A seleção temática não é inventário exaustivo de todas as propostas. Os documentos têm 7–200 páginas e os dossiers diferem em quantidade de excertos. O benchmark não atribui efeitos por tamanho de programa ou orientação política. O ranking experimental mede detecções documentais sob limitações explícitas, sem avaliar mérito das políticas. Custos dos próprios programas não são estimativas independentes; histórico administrativo não foi validado uniformemente. Essas lacunas bloqueiam a comparação causal, não justificam penalidades de desempenho.

## Licença e audiovisual

Código sob MIT. Citações e dados de terceiros mantêm sua autoria/licença original; MIT não relicencia os planos. Este repositório não contém vídeo, projeto Remotion, narração, retratos, assets privados ou credenciais. A produção audiovisual é separada.
