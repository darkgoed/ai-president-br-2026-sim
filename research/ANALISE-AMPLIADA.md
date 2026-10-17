# Pesquisa ampliada — histórico e programas

Coleta: 2026-10-16T17:55:54.502870+00:00

## Escopo e limite de inferência

Coleta descritiva reproduzível de fontes primárias. Não é revisão exaustiva dos governos, avaliação causal ou recomendação de voto. Não se transportam taxas de estados para resultados nacionais.
A página HTML das Contas Regionais bloqueou acesso (403); a definição de PIB foi consultada diretamente na API oficial de metadados IBGE. O serviço de extração web não estava operacional; as fontes abaixo foram obtidas por HTTP direto.
Os 199 excertos já catalogados foram reconferidos com tools/verify_sources.py; o resultado da verificação desta rodada deve acompanhar a entrega.

## Séries comparáveis dentro de cada definição

As diferenças abaixo são territoriais e descritivas, não efeitos de presidentes/governadores. O período inclui choques e eventuais sucessores. Renda real depende da base de preços da edição; PIB aqui é nominal. Não somar mudanças de unidades diferentes.

| Território | Variável | Período final | Valor | Base 2018 | Diferença na unidade original |
|---|---|---|---:|---:|---:|
| Brasil | Taxa de desocupação, na semana de referência, das pessoas de 14 anos ou mais de idade (%) | 202602 | 5.40 | 11.70 (201804) | -6.30 |
| Minas Gerais | Taxa de desocupação, na semana de referência, das pessoas de 14 anos ou mais de idade (%) | 202602 | 3.80 | 9.70 (201804) | -5.90 |
| Goiás | Taxa de desocupação, na semana de referência, das pessoas de 14 anos ou mais de idade (%) | 202602 | 4.00 | 8.40 (201804) | -4.40 |
| Brasil | Rendimento médio mensal real das pessoas de 14 anos ou mais de idade ocupadas na semana de referência com rendimento de trabalho, habitualmente recebido em todos os trabalhos (Reais) | 202602 | 3738.00 | 3343.00 (201804) | 395.00 |
| Minas Gerais | Rendimento médio mensal real das pessoas de 14 anos ou mais de idade ocupadas na semana de referência com rendimento de trabalho, habitualmente recebido em todos os trabalhos (Reais) | 202602 | 3463.00 | 2874.00 (201804) | 589.00 |
| Goiás | Rendimento médio mensal real das pessoas de 14 anos ou mais de idade ocupadas na semana de referência com rendimento de trabalho, habitualmente recebido em todos os trabalhos (Reais) | 202602 | 3946.00 | 3114.00 (201804) | 832.00 |
| Brasil | Produto Interno Bruto a preços correntes (Mil Reais) | 2023 | 10943345439.00 | 7004141000.00 (2018) | 3939204439.00 |
| Minas Gerais | Produto Interno Bruto a preços correntes (Mil Reais) | 2023 | 971977551.00 | 614875820.00 (2018) | 357101731.00 |
| Goiás | Produto Interno Bruto a preços correntes (Mil Reais) | 2023 | 336746975.00 | 195681724.00 (2018) | 141065251.00 |

Fontes das séries (mesmos agregados e variáveis para Brasil, MG e GO):
- Brasil — Taxa de desocupação, na semana de referência, das pessoas de 14 anos ou mais de idade: https://servicodados.ibge.gov.br/api/v3/agregados/6468/periodos/-40/variaveis/4099?localidades=N1[1] (SHA256 2df6844ee57ecfdfa4e6a470f0eaf67904ec89afb09824b05f0674c9df78f5d8)
- Minas Gerais — Taxa de desocupação, na semana de referência, das pessoas de 14 anos ou mais de idade: https://servicodados.ibge.gov.br/api/v3/agregados/6468/periodos/-40/variaveis/4099?localidades=N3[31,52] (SHA256 5995c2a8aa1197a7e6871dc5c04f2d45ef1b38b10f7bcfd4baf1122b24b8515a)
- Goiás — Taxa de desocupação, na semana de referência, das pessoas de 14 anos ou mais de idade: https://servicodados.ibge.gov.br/api/v3/agregados/6468/periodos/-40/variaveis/4099?localidades=N3[31,52] (SHA256 5995c2a8aa1197a7e6871dc5c04f2d45ef1b38b10f7bcfd4baf1122b24b8515a)
- Brasil — Rendimento médio mensal real das pessoas de 14 anos ou mais de idade ocupadas na semana de referência com rendimento de trabalho, habitualmente recebido em todos os trabalhos: https://servicodados.ibge.gov.br/api/v3/agregados/6472/periodos/-40/variaveis/5933?localidades=N1[1] (SHA256 300ccf6ebdcfa78d11c9cb5ca3abcac851fc8fbdc114f8616e5930df9b832d66)
- Minas Gerais — Rendimento médio mensal real das pessoas de 14 anos ou mais de idade ocupadas na semana de referência com rendimento de trabalho, habitualmente recebido em todos os trabalhos: https://servicodados.ibge.gov.br/api/v3/agregados/6472/periodos/-40/variaveis/5933?localidades=N3[31,52] (SHA256 479edbbb3f7f96fce3db7d77eadde569c0388c8d1e94a567664a816aeebbf230)
- Goiás — Rendimento médio mensal real das pessoas de 14 anos ou mais de idade ocupadas na semana de referência com rendimento de trabalho, habitualmente recebido em todos os trabalhos: https://servicodados.ibge.gov.br/api/v3/agregados/6472/periodos/-40/variaveis/5933?localidades=N3[31,52] (SHA256 479edbbb3f7f96fce3db7d77eadde569c0388c8d1e94a567664a816aeebbf230)
- Brasil — Produto Interno Bruto a preços correntes: https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/-40/variaveis/37?localidades=N1[1] (SHA256 548603d804391d1a60152ab7a3a16a56fc898f2e2990ca465c383bdc78d6661f)
- Minas Gerais — Produto Interno Bruto a preços correntes: https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/-40/variaveis/37?localidades=N3[31,52] (SHA256 ed3b1ed164800aa4a3d7bb47a12de584fe4138ef4f9f14f56f040eca2c4262d0)
- Goiás — Produto Interno Bruto a preços correntes: https://servicodados.ibge.gov.br/api/v3/agregados/5938/periodos/-40/variaveis/37?localidades=N3[31,52] (SHA256 ed3b1ed164800aa4a3d7bb47a12de584fe4138ef4f9f14f56f040eca2c4262d0)

## Histórico institucional: o que as fontes permitem afirmar

Parecer prévio propõe ao Legislativo uma conclusão sobre contas de um exercício. Não é julgamento definitivo das contas pelo Legislativo, sentença penal, índice de honestidade ou prova de impacto social.
TCU 2024, TCE-GO 2025 e TCE-MG 2020 têm exercícios e contextos diferentes; NÃO foram convertidos em notas comparáveis. O caso de MG inclui pandemia. Mandato legislativo de Flávio Bolsonaro não equivale a gestão executiva; não se atribuem a ele resultados do governo de Jair Bolsonaro.

### PIB a preços correntes — metadados oficiais (API alternativa à página HTML bloqueada)

https://servicodados.ibge.gov.br/api/v3/agregados/5938/metadados
Coleta 2026-10-16T17:55:55.182962+00:00; SHA256 095d618c940e99bf0bae617cb1e5b081da2394fa1dbd16c00cd44f805cdb35a4; status retrieved.

> {"id":5938,"nome":"Produto interno bruto a preços correntes, impostos, líquidos de subsídios, sobre produtos a preços correntes e valor adicionado bruto a preços correntes total e por atividade econômica, e respectivas participações - Referência 2010","URL":"https://sidra.ibge.gov.br/tabela/5938","pesquisa":"Produto Interno Bruto dos Municípios","assunto":"Contas Nacionais e Regionais","periodicidade":{"frequencia":"anual","inicio":2002,"fim":2023},"nivelTerritoria
> l":[],"IBGE":[]},"variaveis":[{"id":37,"nome":"Produto Interno Bruto a preços correntes","unidade":"Mil Reais","sumarizacao":["periodo","nivelTerritorial"]},{"id":553,"nome":"Participação do produto interno bruto a preços correntes no produto interno bruto a preços correntes da microrregião geográfica","unidade":"%","sumarizacao":["nivelTerritorial"]},{"id":552,"nome":"Participação do produto interno bruto a preços correntes no produto interno bruto a preços correntes da mesorregião geográfica","unidade":"%","sumarizacao":["nivelTerritorial"]},

### Ideb — metodologia, não nota de governante

https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb
Coleta 2026-10-16T17:55:56.492661+00:00; SHA256 b3d4d618bcb169c769b57ae245442603e1ddb8bea894a584665b579161051236; status retrieved.

> tas de qualidade educacional para os sistemas. O índice varia de 0 a 10. A combinação entre fluxo e aprendizagem tem o mérito de equilibrar as duas dimensões: se um sistema de ensino retiver seus alunos para obter resultados de melhor qualidade no Saeb, o fator fluxo será alterado, indicando a necessidade de melhoria do sistema. Se, ao contrário, o sistema apressar a aprovação do aluno sem qualidade, o resultado das avaliações indicará igualmente a necessidade de melhoria do sistema. O índice também é importante condutor de política pública em 
> ó indicador, os resultados de dois conceitos igualmente importantes para a qualidade da educação: o fluxo escolar e as médias de desempenho nas avaliações. O Ideb é calculado a partir dos dados sobre aprovação escolar, obtidos no Censo Escolar , e das médias de desempenho no Sistema de Avaliação da Educação Básica (Saeb). O Ideb agrega ao enfoque pedagógico das avaliações em larga escala a possibilidade de resultados sintéticos, facilmente assimiláveis, e que permitem traçar metas de qualidade educacional para os sistemas. O índice varia de 0 a
> ão Cívica e Cidadania (ICCS) Programa Internacional de Avaliação de Estudantes (Pisa) Dados Abertos Indicadores Educacionais Inep Data Microdados Plano de Dados Abertos Serviço de Acesso a Dados Protegidos (Sedap) Sinopses Estatísticas Listagem de pagamentos por ordem cronológica Sanções Administrativas Ferramentas e aspectos tecnológicos Agenda de Autoridades Transparência e Prestação de Contas Tratamento de Dados Pessoais Sobre Aviso de privacidade Dados do encarregado Previsão legal Finalidade Implementação da LGPD Áreas de Atuação Avaliaçõe

### Contas de Goiás de 2025 — parecer prévio

https://portal.tce.go.gov.br/-/sumario-disponibilizado-pelo-tce-go-trata-das-contas-do-governador-de-2025
Coleta 2026-10-16T17:55:57.189467+00:00; SHA256 412cdeecd94a165f1ec6e3da756dc440b8abef04cf16bd250e72f5f9e5e6f672; status retrieved.

> cer Prévio e o submete à apreciação do Pleno. A sessão foi realizada no último dia 16 de junho, com parecer favorável à aprovação das contas e, na sequência, encaminhado à Assembleia Legislativa (Alego), a quem cabe o julgamento definitivo.. O Sumário Executivo trata dos seguintes temas: Conjuntura Econômica e Social, Ação Setorial do Governo, Gestão Orçamentária e Financeira, Gestão Fiscal, Vinculações Constitucionais, Gestão Patrimonial, Demais Aspectos da Gestão, Monitoramento das Decisões do TCE-GO, Consolidação dos Achados e Deliberações d
> à aprovação das contas e, na sequência, encaminhado à Assembleia Legislativa (Alego), a quem cabe o julgamento definitivo.. O Sumário Executivo trata dos seguintes temas: Conjuntura Econômica e Social, Ação Setorial do Governo, Gestão Orçamentária e Financeira, Gestão Fiscal, Vinculações Constitucionais, Gestão Patrimonial, Demais Aspectos da Gestão, Monitoramento das Decisões do TCE-GO, Consolidação dos Achados e Deliberações do TCE-GO. As deliberações compreendem 11 determinações ao Governo de Goiás, quatro recomendações aos Poderes e órgãos 
> onibilizado pelo TCE-GO trata das Contas do Governador de 2025 Documento sistematiza informações de relatório técnico submetido ao relator person Leonardo Rocha Miranda schedule 31/07/2026 --> --> --> --> O Tribunal de Contas do Estado de Goiás (TCE-GO) disponibilizou o Sumário Executivo do Relatório Técnico sobre as Contas do Governador, exercício de 2025. O documento apresenta ao público, de forma sintética e didática, os principais dados sobre a arrecadação e os gastos anuais da administração pública estadual, aí compreendidos, além do Execu

### Contas de Minas de 2020 — ressalvas e pandemia

https://www.tce.mg.gov.br/TCEMG-emite-parecer-previo-pela-aprovacao-com-ressalvas-das-contas-de-2020-do-governador.html/Noticia/1111626070
Coleta 2026-10-16T17:55:57.604041+00:00; SHA256 ba54bab4f9569b3d30f25adc1ba245e0592c3af4ebf463a50bc656045dc460c2; status retrieved.

> TCEMG emite parecer prévio pela aprovação com ressalvas das contas de 2020 do governador - Tribunal de Contas do Estado de Minas Gerais / TCE-MG D.O.C. Diário Oficial de Contas ACESSE O SITE COMPLETO Cancel OK --> Diário Oficial de Contas Boletins do TCE --> Siga-nos nas redes sociais: Pesquisar --> Acessibilidade AUMENTAR CONTRASTE DIMINUIR CONTRASTE Toggle navigation Página Inicial Sobre o TCEMG Conheça o TCE Histórico Histórico de Autoridades Jurisdição e Competência Prêmios Recebidos Esp
> s contas do governador. O relator e revisor do processo ressaltaram que 2020 foi o ano de início da pandemia da Covid-19, que representou queda nas receitas do Estado e aumento nas despesas na área da saúde. O TCEMG fez dezenas de determinações e recomendações ao governo estadual, como observância dos limites de gastos com pessoal, cumprimentos dos mínimos constitucionais em saúde e educação, monitoramento de renúncia de receitas e aprimoramento dos controles internos do estado. O parecer prévio do TCEMG será enviado para a Assembleia Legislati
> mendações ao governo estadual, como observância dos limites de gastos com pessoal, cumprimentos dos mínimos constitucionais em saúde e educação, monitoramento de renúncia de receitas e aprimoramento dos controles internos do estado. O parecer prévio do TCEMG será enviado para a Assembleia Legislativa de Minas Gerais, órgão responsável pelo julgamento das contas do chefe do Poder Executivo mineiro. Assista, abaixo, às sessões de 29/06 e 07/12. As fotos estão no Flickr do TCEMG Lucas Borges / Coordenadoria de Jornalismo e Redação Razão Social: TR

### Contas federais de 2024 — relatório técnico

https://sites.tcu.gov.br/recursos/contas-do-presidente-2024/1%20Relat%C3%B3rio%20CG2024.pdf
Coleta 2026-10-16T17:55:59.473515+00:00; SHA256 c115504f703b402c7634793e8e772265d5c352c1fa64cac783d10d84f8689f8e; status retrieved.

>  compreendido entre 1º de janeiro e 31 de dezembro de 2024, período no qual o Excelentíssimo Senhor Luiz Inácio Lula da Silva exerceu o cargo de Presidente da República. O exame das contas presidenciais representa uma das atribuições mais relevantes, complexas e abrangentes conferidas ao TCU e possibilita à sociedade conhecer os resultados das ações governamentais, reunindo ampla gama de temas, tratados com máxima profundidade técnica. Esta Corte emite parecer prévio exclusivamente sobre as contas do Presidente da República; as relativas aos Po (p. 2)
> r 200/2023) e enfrentou desafios significativos para alinhar a trajetória de receitas e despesas às metas fiscais estabelecidas. A arrecadação ficou abaixo do previsto, especialmente em razão da frustração de receitas oriundas da reintrodução do voto de qualidade no Conselho Administrativo de Recursos Fiscais (CARF) e de concessões; no lado das despesas, houve alta acima do esperado nos gastos primários, sobretudo em benefícios previdenciários e assistenciais, pressionando o orçamento. A meta de resultado primário foi cumprida, com superávit de (p. 20)
> s. Essa exigência busca qualificar o debate público e parlamentar sobre a alocação de recursos e as renúncias fiscais no processo orçamentário. (p. 35)

### Histórico de mandato legislativo

https://www25.senado.leg.br/web/senadores/senador/-/perfil/5894
Coleta 2026-10-16T17:55:59.653680+00:00; SHA256 401aab5f93ef220549f2f2d9598ad79aaf3822b64f5b674c4cdb1dc2d2cd6aaa; status retrieved.

> Washington DC (ESTADOS UNIDOS) 09/07/2026 REQ 294/2026 - CDIR Biografia Mandatos Mandato Início Fim Senador - RJ 2019 2027 Produção Bibliográfica Publicações do Senador na Biblioteca Digital do Senado Federal Fonte: Secretaria-Geral da Mesa, Coordenação de Arquivo e Coordenação de Biblioteca. ENGLISH ESPAÑOL FRANÇAIS Intranet Servidor efetivo Servidor comissionado Servidor aposentado Pensionista Proteção de dados (LGPD) Fale com o Senado Senado Federal - Praça dos Três Poderes - Brasília DF - CEP 70165-900 | Telefone: 0800 0 61 2211
> nadores › Senador › Flávio Bolsonaro Flávio Bolsonaro - RJ Bloco Parlamentar Vanguarda - PL Período 2019-2027 Dados Pessoais Nome civil: Flávio Nantes Bolsonaro Data de Nascimento: 30/04/1981 Naturalidade: Resende (RJ) Gabinete: Senado Federal Anexo 1 17º Pavimento Telefones: (61) 3303-1717 / 1718 E-mail: sen.flaviobolsonaro@senado.leg.br Escritório de apoio: AVENIDA AFONSO ARINOS DE MELO FRANCO, 222. - BLOCO 2A - SALA 308. BARRA DA TIJUCA, RIO DE JANEIRO, RJ. CEP:22631-455 Telefone:(21) 3627-3800 Proposições Pronunciamentos Relatorias Votações
> es › Senador › Flávio Bolsonaro Flávio Bolsonaro - RJ Bloco Parlamentar Vanguarda - PL Período 2019-2027 Dados Pessoais Nome civil: Flávio Nantes Bolsonaro Data de Nascimento: 30/04/1981 Naturalidade: Resende (RJ) Gabinete: Senado Federal Anexo 1 17º Pavimento Telefones: (61) 3303-1717 / 1718 E-mail: sen.flaviobolsonaro@senado.leg.br Escritório de apoio: AVENIDA AFONSO ARINOS DE MELO FRANCO, 222. - BLOCO 2A - SALA 308. BARRA DA TIJUCA, RIO DE JANEIRO, RJ. CEP:22631-455 Telefone:(21) 3627-3800 Proposições Pronunciamentos Relatorias Votações Tran

## Revisão dos compromissos por candidatura

Quantidades abaixo descrevem o corpus auditado, não qualidade ou completude do programa integral. Falta de histórico executivo uniformemente verificado permanece desconhecida; não vira nota zero. Custos declarados por candidatura não foram validados de modo independente.

### ESCRITOR AUGUSTO CURY

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002551547_01.pdf; SHA256 fc0872d2b68aad863c8d62575323cf413a616b23d0f7ca4fd7f4558112c07b38.
Compromissos quantitativos catalogados: 2. Metas são declarações, não entregas previstas.
- Meta habitacional declarada.; prazo catalogado: 10; augusto-cury-E11 p.106.
- Estimativa preliminar do programa; inclui crédito retornável, não apenas gasto orçamentário.; prazo catalogado: 10; augusto-cury-E12 p.111.

### CLARIANA BARAO

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002552484_01.pdf; SHA256 6390152c66285558ecd5459f4f73f3f65650beb77022b14e7750190b1b536d68.
Compromissos quantitativos catalogados: 0. Metas são declarações, não entregas previstas.

### EDMILSON COSTA

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002551975_01.pdf; SHA256 52f765533f93409a595d780e9ad8634de72db8f05794a2e70e808913c2ed4dff.
Compromissos quantitativos catalogados: 2. Metas são declarações, não entregas previstas.
- Jornada proposta, não efeito de emprego.; prazo catalogado: não identificado no trecho; edmilson-costa-E11 p.14.
- Percentuais de cotas propostos no documento.; prazo catalogado: não identificado no trecho; edmilson-costa-E12 p.7.

### Flávio Bolsonaro

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002551544_01.pdf; SHA256 7d1d95075e11e3c4113e8dcd502438049a34f5147a84cb0f746bf59046e477a4.
Compromissos quantitativos catalogados: 8. Metas são declarações, não entregas previstas.
- crescimento sustentado de 4% ao ano; prazo catalogado: próxima década; flavio-bolsonaro-E25 p.49.
- 500 mil novas vagas prisionais e déficit carcerário zero; prazo catalogado: 4 anos; flavio-bolsonaro-E26 p.14.
- mais de 1 milhão de novas câmeras; prazo catalogado: não identificado no trecho; flavio-bolsonaro-E27 p.15.
- R$ 900 bilhões em infraestrutura de transporte; prazo catalogado: 4 anos; flavio-bolsonaro-E28 p.51.
- 2,5 milhões de residências; prazo catalogado: não identificado no trecho; flavio-bolsonaro-E29 p.47.
- desmatamento ilegal zero; prazo catalogado: 2029; flavio-bolsonaro-E30 p.58.
- 100% dos serviços federais digitalizáveis digitalizados; prazo catalogado: não identificado no trecho; flavio-bolsonaro-E31 p.25.
- nenhuma escola sem água; prazo catalogado: 2030; flavio-bolsonaro-E32 p.47.

### HERTZ DIAS

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002541457_01.pdf; SHA256 1868565fb0d5de77d40a982a1be07dc7f44f7af7565ee3b40d93b31407d31468.
Compromissos quantitativos catalogados: 1. Metas são declarações, não entregas previstas.
- Limite proposto de isenção; sem estimativa independente de arrecadação.; prazo catalogado: não identificado no trecho; hertz-dias-E11 p.27.

### Lula

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002542548_01.pdf; SHA256 e1c162c20c81dafadf69b10bab230b5a6dc48f6b6c27c2cfce853b131a8bcc36.
Compromissos quantitativos catalogados: 4. Metas são declarações, não entregas previstas.
- 80% das crianças alfabetizadas na idade certa; prazo catalogado: não identificado no trecho; lula-E25 p.31.
- desmatamento líquido zero; prazo catalogado: 2030; lula-E26 p.70.
- jornada de 40 horas sem redução salarial (fim da escala 6x1); prazo catalogado: não identificado no trecho; lula-E27 p.75.
- redução de 59% a 67% das emissões líquidas vs 2005 (NDC já entregue; plano promete cumpri-la); prazo catalogado: 2035; lula-E28 p.69, lula-E22 p.71.

### RENAN SANTOS

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002540694_01.pdf; SHA256 cdece60b71117c7820dbf90a7d795f76f3b1d1aaa5ebb8ce11f47e9ca6227b5a.
Compromissos quantitativos catalogados: 2. Metas são declarações, não entregas previstas.
- Projeção fiscal do próprio programa, não estimativa validada.; prazo catalogado: 2031; renan-santos-E11 p.10.
- Meta de resolução na atenção primária; horizonte não definido no trecho.; prazo catalogado: não identificado no trecho; renan-santos-E12 p.26.

### Romeu Zema

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002539826_01.pdf; SHA256 5a5804622017a8e9c123fb64540a5ee3d06009de681026b505bc2a152d5e646e.
Compromissos quantitativos catalogados: 2. Metas são declarações, não entregas previstas.
- R$ 1.000 por brasileiro ao nascer (Sócios do Brasil); prazo catalogado: não identificado no trecho; romeu-zema-E25 p.18.
- privatização de todas as estatais; prazo catalogado: não identificado no trecho; romeu-zema-E26 p.15.

### Ronaldo Caiado

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002551932_01.pdf; SHA256 b0ba46eb58d1827c99167a0df60e539b6bfa8a70fa247e4653ba2fcca8ade415.
Compromissos quantitativos catalogados: 7. Metas são declarações, não entregas previstas.
- ≥50% de redução no tempo mediano das filas prioritárias (base 2027); prazo catalogado: 2030; ronaldo-caiado-E23 p.77.
- -20% internações sensíveis à APS; 100% das equipes de Saúde da Família com teleconsultoria; prazo catalogado: 2030; ronaldo-caiado-E24 p.78.
- -30% mortalidade cardiovascular prematura (meta indicativa); prazo catalogado: 2030; ronaldo-caiado-E25 p.79.
- -30% razão de mortalidade materna (meta indicativa); prazo catalogado: 2030; ronaldo-caiado-E26 p.81.
- ≥95% cobertura nas vacinas prioritárias; prazo catalogado: 2030; ronaldo-caiado-E27 p.88.
- 100% cobertura do SAMU; prazo catalogado: 2030; ronaldo-caiado-E28 p.87.
- preço do gás industrial próximo de US$ 8/MMBtu (referência); prazo catalogado: não identificado no trecho; ronaldo-caiado-E29 p.37.

### RUI COSTA PIMENTA

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002552487_01.pdf; SHA256 ed380b23d6e033e8616ce71efcf66eb42d2baee2b58f1c9ae80690009c20dfe9.
Compromissos quantitativos catalogados: 2. Metas são declarações, não entregas previstas.
- Jornada semanal proposta; não efeito estimado no emprego.; prazo catalogado: não identificado no trecho; rui-costa-pimenta-E11 p.2.
- Piso proposto, sem custo agregado identificado.; prazo catalogado: não identificado no trecho; rui-costa-pimenta-E12 p.5.

### SAMARA

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002538811_01.pdf; SHA256 23c510d5b06bb149bb9390bbc144dcda9cfd2b6a677a854b3d993b16ed7a94e6.
Compromissos quantitativos catalogados: 2. Metas são declarações, não entregas previstas.
- Compromisso de elevação do mínimo, não efeito de renda real.; prazo catalogado: não identificado no trecho; samara-martins-E11 p.7.
- Meta de recursos educacionais em proporção do PIB.; prazo catalogado: não identificado no trecho; samara-martins-E12 p.22.

### VETERINÁRIO WILSON GRASSI

Plano: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip — membro BR/2026BR280002548139_01.pdf; SHA256 df2acdb7a6d8b080d6d8a235b8fe8f0d987bf0f24be4f4aa9abc80e4ebb24904.
Compromissos quantitativos catalogados: 1. Metas são declarações, não entregas previstas.
- Estimativa do próprio plano; não validada causalmente. O mesmo parágrafo contém comparação aritmética inconsistente, auditada separadamente.; prazo catalogado: não identificado no trecho; wilson-grassi-E11 p.13.

## Evidência empírica contextual e transportabilidade

Os estudos já revisados não fornecem coeficientes universais transferíveis para os doze programas. Foram relidos os limites catalogados; não se fabricaram coeficientes para gerar um vencedor.

- ipea-hours: https://repositorio.ipea.gov.br/server/api/core/bitstreams/7083c3f2-81ee-48e6-a525-c9fe4b56d5e7/content — Nota técnica: evidência descritiva e cálculos de custos, não identificação causal de emprego futuro. Não extrapolar jornadas ou escalas sem microdados.
- ipea-transfers: https://repositorio.ipea.gov.br/bitstreams/3ce619b8-9b5b-4b4f-ad16-1a02c0d0e2b7/download — PNAD 2004 e simulações de focalização; contexto histórico e desenho específico, não coeficiente causal universal para 2027–2030.
- ipea-upa: https://repositorio.ipea.gov.br/bitstreams/feb1fb1f-e439-44f8-b0e1-55492227a28a/download — Municípios do RJ, 2000–2011; modelo em painel. Não extrapolar para APS, todo SUS ou qualquer expansão federal; resultado geral não significativo é preservado.

## Ranking permitido por estes insumos

Implementado separadamente: ranking experimental de especificação DETECTADA na seleção auditada, com seis critérios saturados por eixo, dez eixos e pesos editoriais transparentes. Zero significa ausência de detecção nesta seleção, não inexistência no plano completo ou efeito zero de governo.
100.000 análises variam pesos Dirichlet(1), não reamostram governos reais. A simulação macro de 100.000 trajetórias é outro experimento e não fornece efeitos diferenciais das candidaturas.
O protocolo e os mapeamentos dos compromissos estão em research/ranking_protocol.json. A seleção desigual de excertos é uma limitação relevante que os pesos não resolvem.

## O que falta para ranking de desempenho governamental

Custos líquidos independentes por medida, cronogramas, restrições legislativas e federativas, modelos causais validados, contrafactuais e séries de exposição comparáveis para todas as candidaturas. Sem isso, não se apresenta ranking documental como previsão de melhor presidente.
