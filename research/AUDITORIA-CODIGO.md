# Auditoria técnica do caminho dados → integração → simulação

## Conclusão

Auditoria concluída com ressalvas: cinco falhas de código/contrato reproduzidas e uma observação operacional adicional. Não recomendar publicação como sistema livre de falhas antes das correções e testes de regressão. Não foi encontrada divergência nos 55 datasets públicos atuais comparados às respostas arquivadas. As falhas de validação foram demonstradas exclusivamente em fixtures isoladas, não na base real.

Esta rodada é de diagnóstico, não de correção: não modifica equações, notas, séries, parâmetros ou resultados históricos. Foram acrescentados o script de sondas e este relatório com suas evidências. A execução dos verificadores existentes regravou seus relatórios de verificação, não as trajetórias ou dados de entrada.

## Escopo e método

Revisão focal dos módulos de coleta, normalização, identificação das séries, integração SQLite, simulação empírica, backtest, métricas, exportação e verificadores. Leitura do código e testes, testes adversariais locais, comparação de dados normalizados às respostas originais e oráculo numérico independente. Não é auditoria exaustiva de cada frase política nem garantia de ausência de viés.

Comandos reproduzíveis a partir da raiz do projeto:

    .venv/bin/python -m pytest -q
    .venv/bin/python tools/audit_analysis.py
    .venv/bin/python tools/verify_empirical.py results-1m
    .venv/bin/python tools/verify_knowledge.py results-integrated
    .venv/bin/python -m src.cli validate
    git diff --check

Sondas usam TemporaryDirectory dentro de TMPDIR, removida ao final. Valores alterados nas fixtures não são evidências políticas e não são incorporados ao catálogo real. Saída da rodada: AUDITORIA-CODIGO-EVIDENCIAS.json. Comando retorna sucesso quando as sondas concluem; isso NÃO significa que os bugs estejam corrigidos.

## Achados confirmados

### A02 — Alta: a validação do hash não valida a transformação dos valores

Referência: src/knowledge_build.py:129–153; tools/verify_knowledge.py.

O integrador confere os bytes da resposta arquivada, mas grava `dataset['observations']` e `report['items']` sem exigir que correspondam à resposta conferida. O hash do catálogo identifica sua versão, não prova a equivalência da transformação ao original.

Reprodução: mantidos a resposta original e seu hash, a fixture muda um valor normalizado de 11,9 para 1010,9 e elimina os demais registros daquele dataset. O build termina e publica 1010,9 como `observed`.

Impacto: erro de transformação, alteração acidental ou truncamento pode entrar como estatística reportada apesar do selo de hash verificado. Não se constatou isso nos datasets públicos atuais: os 55 foram comparados e coincidem com suas respostas arquivadas.

Correção necessária: reconstruir/validar a normalização por provedor contra os bytes originais; comparar valores, unidades, chaves, classificações e completude. Para Siconfi, exigir igualdade dos itens com o raw e verificar paginação/contagem. Aplicar a mesma regra aos relatórios expandidos. Adicionar teste que rejeite a fixture acima.

### A03 — Alta: identidade de série oficial não é validada contra o catálogo

Referência: src/observed.py:88–99; src/cli.py:229–240.

O carregador valida hash e observações, mas não vincula estritamente `id`, SGS, unidade e definição ao catálogo. O CLI seleciona dívida inicial pelo `id` fornecido no JSON.

Reprodução: na cópia de teste, o ID do IPCA (SGS 433) é trocado para `gross_debt_gdp`, e o ID da dívida original é renomeado. A carga passa e `analyze --use-observed-debt` usa fração 0,0082 como dívida inicial, em vez do dado de dívida de 82,87% do PIB. A série continua com seu raw original intacto.

Impacto: troca de metadados pode alterar radicalmente o benchmark. Isso não demonstrou erro no snapshot atual: as 12 identidades/unidades atuais correspondem ao catálogo.

Correção necessária: exigir exatamente as identidades esperadas, ausência de duplicatas, SGS/unidade/frequência coerentes e regra explícita para coleta parcial. No CLI, exigir dívida SGS 13762 em % PIB, não apenas coincidência de `id`. Rejeitar antes de produzir arquivos.

### A04 — Média: exportação deixa ranking obsoleto junto de resultados novos

Referência: src/cli.py:66–112.

Uma execução com ranking legado cria ranking.json, ranking.csv e ranking_indicators.csv. Nova execução sem ranking no mesmo destino sobrescreve results.json, mas não remove, arquiva ou invalida os três arquivos antigos.

Reprodução: duas execuções de 8 trajetórias em pasta isolada, primeiro com `--legacy-documentary-ranking`, depois sem a flag. O resultado ativo não contém ranking, porém os três arquivos permanecem.

Impacto: auditor/leitor pode associar ranking anterior à análise nova. Há também risco geral de perda de histórico por sobrescrita no modo analyze; o bloqueio de sobrescrita do modo empirical não resolve o outro caminho.

Correção necessária: destinos imutáveis/novo diretório por análise, ou exportação transacional com manifesto completo e arquivamento explícito do legado. Não apagar resultados históricos reais como remendo. Testar reexecução em destino já ocupado.

### A05 — Média: verificador anterior falha com o padrão atual sem ranking

Referência: tools/verify_analysis.py:23–46.

`verify_analysis.py` pressupõe `experimental_ranking` e os CSVs do ranking. O CLI passou a desativá-lo por padrão.

Reprodução: verificar uma análise padrão de 8 trajetórias gera KeyError: 'experimental_ranking'.

Impacto: o caminho de auditoria anunciado deixa de funcionar nas análises novas. Isso não é erro aritmético nem prova de corrupção; é quebra do contrato entre produtor e verificador, podendo incentivar ignorar uma verificação que falhou.

Correção necessária: validar ambos os modos explicitamente e rejeitar mistura de artefatos de execuções diferentes. Testar análise sem ranking e reprodução histórica com ranking.

### A01 — Baixa: contagem afirma unicidade que não mede

Referência: src/empirical.py:105; tools/verify_empirical.py:40; tests/test_empirical.py:54.

O campo `unique_paths` recebe simplesmente o número de sorteios. O verificador e o teste repetem a mesma suposição.

Medição no milhão executado: 999.267 sequências distintas de quatro blocos; 733 repetições de sequência. Logo, o número de trajetórias numericamente distintas não pode ser superior a 999.267; esta rodada não contou as trajetórias numéricas distintas, que podem coincidir mesmo com sequências diferentes.

Impacto: apresentação incorreta da diversidade. Repetições são esperadas em bootstrap com reposição e não devem ser removidas para maquiar a contagem: isso mudaria o experimento. Não invalidam, por si, médias/quantis amostrais.

Correção necessária: renomear para `sampled_paths`/trajetórias sorteadas, versionar o esquema e, se desejado, medir separadamente sequências e trajetórias efetivamente distintas. Atualizar testes e verificadores para não certificar unicidade por definição.

## Observação operacional adicional (A06)

src/knowledge_build.py:45–46, 217–241 permite build com zero candidaturas. A fixture mínima obteve manifesto/dashboard válidos com `candidates=0`. Isso pode ser útil para bases parciais, portanto não é classificado como sexto bug confirmado. Para publicação que prometa as doze candidaturas, é necessário um perfil de validação que exija o conjunto de IDs esperado; marcar lacunas não equivale a verificar essa promessa de completude.

## Verificações que passaram

- Suíte atual: 76 testes aprovados, incluindo invariância numérica a nomes/partidos/ordem, ausência de efeitos políticos suportados e teste de valores futuros não alterarem a predição passada no backtest.
- 55 datasets públicos: observações normalizadas comparadas às respostas arquivadas, sem divergência. Teste verifica fidelidade ao snapshot, não a correção do produtor externo.
- 12 séries do snapshot observado: IDs/SGS/unidades atuais compatíveis com o catálogo interno.
- 1.000.000 trajetórias: reexecução exata por seed/índices em lotes diferentes, hashes e backtest reproduzidos pelo verificador existente. Ele compartilha funções com o simulador, por isso não basta sozinho como oráculo independente.
- Oráculo adicional independente em amostra determinística de 1.000 trajetórias e quatro anos por trajetória, calculando razões de níveis, razões de odds e produto mensal de IPCA diretamente no histórico, sem chamar project/annual_blocks: aprovado; maior diferença absoluta 3,126388037344441e-13 (arredondamento numérico).
- Base integrada: 19.021 registros, integridade SQLite/referências, hashes e igualdade JSONL/SQLite aprovadas; nenhum registro observed/simulated vinculado diretamente a candidatura.
- Validação atual de perfis: 12 perfis, comparação política não identificada; git diff --check aprovado.

## Limitações metodológicas — distintas dos bugs

O modelo segue sem identificar efeitos causais por candidato. Alterar nomes não alterar números é proteção útil, mas não prova neutralidade da seleção de fontes, interpretação dos textos ou critérios históricos.

O backtest tem nove cortes de 12 meses, enquanto a simulação publicada alcança quatro anos. Usa séries revisadas atuais, não as vintages disponíveis em cada data. Não apareceu vazamento do futuro para o treino nos cortes inspecionados/testados, mas isso não o transforma em validação em tempo real ou em validação de quatro anos.

Na execução existente, dívida e desocupação têm MAE pior que manter o nível inicial. Isso é falha de desempenho preditivo, não evidência de bug por si só. Não esconder esse resultado nem transformar erro numérico pequeno em confiança no modelo.

PNADC em trimestre móvel e blocos históricos sobrepostos geram dependência no histórico; o número de registros/blocos não é número de observações independentes. Estacionariedade, transformação log/logit e blocos de 12 meses são escolhas de modelo, não impactos politicamente neutros demonstrados pela natureza.

O ranking documental legado segue inadequado para inferir melhor governo por assimetria do corpus e pesos editoriais. Sua desativação por padrão é coerente com esse limite, mas os arquivos históricos e exportações obsoletas ainda podem confundir leitores (A04).

## Ordem recomendada de correção

1. A02 e A03 com regressões adversariais que falhem antes do reparo.
2. A04 e A05, preservando explicitamente os artefatos históricos e testando ambos os modos.
3. A01 com versão nova de contrato de contagem, sem eliminar sorteios repetidos.
4. Gate de publicação com as doze candidaturas, fonte/unidade/território/período e completude explícitos.
5. Nova auditoria focal e nova execução versionada, sem sobrescrever a análise anterior.

Nenhuma dessas correções foi aplicada nesta rodada. A auditoria diagnostica problemas; 76 testes verdes não certificam ausência deles.
