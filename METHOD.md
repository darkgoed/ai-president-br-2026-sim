# Pré-especificação do gate e do benchmark exploratório

Escrita antes de executar qualquer simulação. O modelo só será implementado após auditoria das pesquisas.

## Identificabilidade

Um plano documenta compromissos, não efeitos causais. Para estimar efeitos diferenciais seriam necessários custos, cronograma, execução provável, restrições de aprovação, resposta de receita e modelos causais identificados. Nem metas de PIB nem percentuais eleitorais são coeficientes causais. Onde faltarem esses elementos, o efeito de política fica `null`, nunca zero. Não haverá ranking nem um empate artificial.

Se o gate não autorizar comparação, executar exclusivamente um benchmark contábil exploratório comum: dinâmica de dívida sob condições hipotéticas, sem atribuí-la ao governo de qualquer candidatura. Cada perfil passa pelas mesmas 1.000 condições, com resultado político não identificado. Contar separadamente trajetórias únicas, avaliações de perfis e efeitos de governo identificados. Repetir uma referência 12 vezes não produz 12.000 mundos independentes.

## Equação e unidades propostas

Escolano, IMF TNM/10/02, 27/01/2010, seção II, equação (5):

`d[t+1] = ((1+i[t]) / (1+gamma[t])) * d[t] - p[t]`

`d` e `p`: frações do PIB corrente; `i`: juros nominais efetivos sobre estoque, não Selic; `gamma`: crescimento nominal do PIB, não crescimento real. Superávit primário positivo reduz dívida. Sem câmbio, stock-flow adjustments, privatizações, feedbacks endógenos ou modelagem política. A identidade é fundamentada; as distribuições não são estimadas e serão classificadas como hipóteses exploratórias, não probabilidades calibradas do Brasil.

Condições hipotéticas a pré-fixar em JSON: horizonte quatro anos; dívida inicial 0,80; juros uniformes [0,06;0,12]; crescimento nominal uniforme [0,02;0,08]; primário uniforme [-0,02;0,02]. Valores são escolhas de stress, NÃO dados oficiais ou previsões. Choques independentes entre variáveis e anos são simplificação explícita.

Oito famílias balanceadas: estável, fiscal, recessão internacional, inflacionário, desemprego, energia, pressão de gasto e combinado. Rótulos descrevem stress, não modelos macroeconométricos das crises. Choques de juros, crescimento e primário serão deslocamentos publicados em JSON, sem ajustar após observar nomes ou resultados. Inflação não será tratada como IPCA ou convertida em efeito político.

## Resultados e robustez

Estatísticas da referência: média, mediana, desvio amostral, quantis 2,5 e 97,5%, mínimo/máximo, histograma e trajetórias. Quantis são intervalos da distribuição artificial, não intervalos de confiança de governo. Separar variabilidade do benchmark e desconhecimento estrutural dos efeitos políticos.

Sensibilidade pareada: primário ±0,005; juros ±0,005; crescimento nominal ±0,005; dívida inicial ±0,01; amplitudes de incerteza 0,9x e 1,1x; sementes alternativas. Não otimizar nenhuma distribuição. Pesos alternativos para objetivos sociais: não aplicável quando faltam resultados de saúde, educação etc.; testes devem garantir que alterar pesos nunca cria dados nem ranking. Não produzir índice composto.

Verificar seed, nomes, partidos, IDs e ordem, neutralidade numérica, fórmula manual/analítica, sinal/unidades, contagens, validação de parâmetros, exportação e snapshots. O próprio resultado negativo do gate é publicável, mas não prova equivalência dos programas.
