# Reauditoria e aprofundamento analítico — entrega V2

## Entrega vigente

- Compilação integrada: results-integrated-v4/.
- Relatório legível e tabelas: results-integrated-v4/analysis/RELATORIO.md.
- Análise completa: results-integrated-v4/analysis/analysis.json.
- Base com proveniência: results-integrated-v4/evidence.sqlite e JSONL.
- Evidência da reauditoria: research/REAUDITORIA-FINAL-V2.json.
- Simulação versionada: results-1m-v2/.

Não houve redesign, commit ou publicação. Diretórios anteriores, inclusive compilações intermediárias v2/v3, foram preservados; não usar suas contagens/diagnósticos como os da versão final v4. O relatório AUDITORIA-CODIGO.md é histórico de problemas antes das correções, não o estado do código atual.

## Correções verificadas

| Achado | Correção | Demonstração |
|---|---|---|
| A01: falsa unicidade | Esquema 2 usa sampled_paths, distinct_block_sequences e repeated_block_sequences. Não elimina repetições legítimas do bootstrap. | 1.000.000 sorteios, 999.267 sequências distintas, 733 repetições; verificador mede, não presume. |
| A02: normalização não conferida | src/public_validation.py reconstrói e compara resposta normalizada, itens fiscais, metadados, unidade, indicador e território; confere completude/paginação e tipos JSON. Aplicado aos datasets e relatórios embutidos. | Valor alterado, truncamento, booleano em lugar de número, unidade/rótulo/território adulterados são rejeitados nos testes. Os 68 datasets atuais passam. |
| A03: IPCA aceito como dívida | Identidade SGS, rótulo, produtor, unidade, frequência, URL, duplicatas e estatísticas são validados; histórico empírico também confere origem dos chunks. | Fixture com troca de IDs rejeitada; URL de outra série rejeitada; resumo adulterado rejeitado. |
| A04: ranking obsoleto ao reutilizar saída | CLI recusa destinos não vazios antes de simulate/analyze/empirical/integrate. | Segunda análise rejeitada; bytes dos arquivos anteriores permanecem iguais. |
| A05: verificador exige ranking desativado | tools/verify_analysis.py valida explicitamente ambos os modos e recusa ranking obsoleto quando ausente do resultado ativo. | Análises pequenas completas com/sem modo legado verificadas em fixtures independentes. |
| A06: publicação sem candidaturas | Gate de publicação exige conjunto de IDs dos 12 perfis configurados e fontes obrigatórias. | Fixture vazia falha antes da criação do destino. Build parcial interno continua possível, explicitamente fora do gate. |

Na revisão do novo diagnóstico de duplicatas, também foi corrigida uma colisão entre IDs de indicadores do Banco Mundial iniciados por N. A normalização de sufixo territorial agora é exclusiva do IBGE. Há regressão específica. A compilação final detecta 374 células repetidas por chaves explícitas, sem conflitos de valores; isso não significa que todos os produtores ou dados sejam independentes.

## Ampliação efetivamente executada

A lista de indicadores adicionais foi fixada antes da coleta, com mesma regra BRA/2000:2025, sem selecionar por candidatura ou substituir indicadores que falharam. Metadados e respostas foram baixados, preservados e validados. O catálogo anterior foi mantido intacto.

- 13 novos datasets aceitos; 68 datasets públicos ao todo, com 15.005 observações no catálogo ampliado (inclui ausências, não somente valores numéricos válidos).
- 308 grupos de séries/territórios/classificações; 9.660 comparações com o mesmo código de período do ano anterior. Valores faltantes não viram zero; diferenças de taxas percentuais usam pontos percentuais, com variação relativa explicitada separadamente; unidade ausente não é preenchida por suposição.
- 48 distribuições simuladas derivadas, correspondentes a 12 medidas em quatro horizontes anuais, com média, mediana, dispersão, quantis, caudas e frequências condicionais.
- Backtests de 12, 24 e 48 meses, com 9, 4 e 2 cortes não sobrepostos dentro de cada horizonte. Baselines sem mudança e drift treinado só com passado. MAE, RMSE, viés, erro mediano/máximo, CRPS, cobertura 50/80/95%, interval score e faixa de Wilson. Origens e alvos estão preservados, sem escolher retrospectivamente um modelo vencedor.
- 199 citações conferidas nas páginas indicadas dos PDFs. Documento comprova o registro da declaração, não a verdade, o custo ou a entrega da promessa.
- 864 páginas extraídas de 14 documentos do arquivo oficial: 788 dos 12 perfis configurados e 76 de dois documentos adicionais fora do modelo. Os adicionais entram como contexto, sem perfis ou efeitos políticos inventados.
- 29.467 registros classificados no bundle, com 119 fontes/snapshots locais. Esses totais não são quantidade de estudos nem de indicadores independentes.

Os dados históricos antigos que não preservaram respostas brutas ficam como contexto, sem o rótulo de observação recém-autenticada. As declarações, menções automáticas, observações, cálculos derivados e simulações continuam separados, inclusive no SQLite. O vínculo de observado/derivado/simulado a candidato é bloqueado.

## Verificações reais

- 99 testes aprovados; git diff --check aprovado.
- Milhão de trajetórias reproduzido exatamente em lotes diferentes; hashes e backtest anterior conferidos.
- Oráculo independente em 1.000 trajetórias, quatro anos por trajetória, aprovado com erro de arredondamento máximo de 3,126388037344441e-13.
- Regressões de não-vazamento: alterar observações futuras não muda a primeira previsão ou drift nos horizontes de 12, 24 e 48 meses.
- Transformações dos 68 datasets e dos relatórios embutidos revalidadas contra respostas brutas.
- Novo relatório, métricas, backtests e CSVs regenerados em pasta temporária e comparados à compilação final.
- Integridade SQLite/foreign keys, hashes de fontes/artefatos e equivalência JSONL/SQLite aprovadas.
- Consulta offline testada: 9.660 registros derivados no filtro; zero quando se tenta atribuí-los a uma candidatura; sem erro JavaScript ou overflow no viewport móvel testado.

## Limites que não foram escondidos

O bootstrap continua pior que baselines em vários indicadores e horizontes. Em quatro anos, há apenas dois cortes históricos: não há base para declarar previsão governamental confiável. Dados revisados atuais não são vintages em tempo real. A melhoria é de integridade, cobertura e capacidade de avaliar erros, não uma promessa de maior acurácia.

As falhas de coleta wb-EN.ATM.CO2E.PC e wb-SH.UHC.SRVS.CV.XD estão registradas. Nenhum valor foi fabricado ou substituído por indicador de nome parecido. Unidades não estruturadas continuam desconhecidas. Entrevistas/debates externos não foram integralmente transcritos e checados.

Mais métricas não identificam impactos causais e não garantem imparcialidade da seleção ou interpretação. Nenhum ranking de melhor governo foi criado, e as evidências novas não foram convertidas em coeficientes por candidato.

## Reprodução

    .venv/bin/python -m pytest -q
    .venv/bin/python tools/audit_analysis.py
    .venv/bin/python tools/verify_sources.py
    .venv/bin/python tools/verify_empirical.py results-1m-v2
    .venv/bin/python tools/verify_knowledge.py results-integrated-v4

Para reconstruir, usar destinos novos. README.md contém os comandos de coleta, simulação e integração versionada. Os JSONs/CSVs contêm URLs, hashes e ponteiros de origem para inspecionar as derivações, sem depender deste texto.
