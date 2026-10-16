# Auditoria documental e gate científico

Corte de coleta: 15–16/10/2026 (horários UTC nos manifests). Auditoria pelo orquestrador, após encerramento do único worker.

## Resultado verificado

Os 12 nomes solicitados constam do resultado oficial do primeiro turno. Os arquivos cadastrais também contêm Marçal (indeferido/substituído) e Leonardo Avalanche (renunciante); não integram a lista de 12 com votos válidos. Não se contou registro de segundo turno como nova pessoa. O campo cadastral `#NE` não foi interpretado como indeferimento: consultou-se o arquivo complementar.

Os votos individuais somam 119.300.788, exatamente o total válido do JSON TSE. As 12 percentagens foram recalculadas com Decimal e arredondamento decimal. Flávio Bolsonaro e Lula constam como classificados ao segundo turno; não se presume resultado desse turno.

`audit_checks.json` registra 199 trechos programáticos conferidos contra a página correspondente do PDF, após normalização de espaços e hifenização editorial. Referências cadastrais são seleções de campos, não citações de linhas integrais. Os hashes dos PDFs e dos ZIPs constam dos manifests.

## Tratamento e assimetrias

Todos os nomes têm dez eixos documentais, a mesma exigência de evidência primária e nenhum coeficiente político. Um worker pesquisou quatro nomes. O roteador bloqueou as três tentativas subsequentes de delegação (lote e candidatura individual); o orquestrador concluiu as oito coletas restantes. Nenhum worker implementou, modelou ou auditou. Isso é uma limitação operacional registrada, não uma pesquisa paralela fictícia.

Há diferenças reais de extensão e estrutura dos documentos (7 a 200 páginas). A seleção é temática e não exaustiva: quatro dossiers têm maior número de excertos, oito têm seleção mais compacta. Não se igualou artificialmente o número de promessas. Quantidade de texto/evidências não gera nota ou vantagem. A profundidade não é suficiente para afirmar que todos os impactos de todas as propostas foram identificados; o gate quantitativo mantém efeitos políticos desconhecidos em todos os perfis.

Histórico administrativo não foi validado de modo independente para nenhum dos 12. Autodescrições nos planos são alegações da candidatura, não comprovação de resultado administrativo. Nenhuma delas é usada no motor.

## Correções e limites factuais

1. Siglas partidárias dos quatro JSONs do worker foram padronizadas em campo separado do nome completo do partido, sem alterar o original.
2. Não se publicou o cadastro bruto: CPF, e-mail, título eleitoral e nascimento não são necessários ao experimento. Snapshots brutos ficam fora da distribuição pública.
3. No plano de Wilson Grassi, página 13, a comparação de R$ 266 bi com a soma de R$ 271,3 bi e R$ 233,7 bi é aritmeticamente inconsistente: a soma é R$ 505 bi. A citação permanece identificada como alegação do programa; a comparação não é insumo numérico. Essa verificação não avalia a proposta tributária como um todo.
4. Não se transformaram metas declaradas de crescimento, filas, moradias, emissões ou alfabetização em resultados prováveis. Custos declarados (incluindo investimento privado e fundos de crédito) não foram confundidos com despesa federal líquida anual.
5. Estimativas históricas de programas e estudos de 2004/2000–2011 não foram transplantadas como coeficientes do Brasil de 2027–2030.
6. HTTP 200 sem JSON válido (uma consulta BCB) não valida indicador. Nenhuma série BCB tentada foi usada para calibrar hipóteses do benchmark.

## Impactos sobre a população: critério acrescentado

Cada proposta selecionada recebe em `impacts.json` o compromisso e sua referência, canal de impacto condicional, grupos/indicadores de interesse, custo disponível ou lacuna, dependências fiscais/legais/institucionais, evidência empírica pertinente ou ausência, horizonte de quatro anos e efeitos colaterais. Esses canais são análise conceitual, não estimativas causais.

O estudo Ipea sobre jornada distingue custo contábil de hora trabalhada de emprego líquido e limita a análise da escala por falta de dados. A avaliação histórica do Bolsa Família mostra a importância da seleção de beneficiários; não é coeficiente universal. A avaliação de UPAs encontra efeito não significativo na mortalidade geral, apesar de mudanças no local dos óbitos. Esse resultado desfavorável à inferência simplista é preservado. A tabela RFB é referência normativa, não evidência de crescimento.

## Decisão

Fidelidade documental e aritmética eleitoral: aprovadas no escopo descrito; sem inconsistência factual grave aberta nos insumos usados.

Comparação quantitativa de governos: NÃO autorizada. Não há identificação de efeitos diferenciais, probabilidades de execução ou custos líquidos comparáveis para os 12. Não há vencedor, ranking ou empate de desempenho. `null` não significa efeito zero.

Autoriza-se somente o benchmark exploratório pré-especificado de dinâmica contábil da dívida e cálculos mecânicos explicitamente condicionais. Distribuições são consequências de hipóteses artificiais publicadas, não previsões para governos nem probabilidades calibradas. Indicadores de saúde, segurança, inflação, emprego e educação continuam não identificados. Pesos sociais não podem preencher essas lacunas.
