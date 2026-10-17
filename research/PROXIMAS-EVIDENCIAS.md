# Evidências necessárias e limite do ranking atual

## Constatação da auditoria do corpus

Inspeção direta de `research/candidates/*.json` e `results-100k/ranking.json` nesta rodada:

- Flávio Bolsonaro: 29 excertos oficiais; oito compromissos quantitativos catalogados.
- Lula: 25 excertos oficiais; quatro compromissos quantitativos catalogados.
- Romeu Zema: 23 excertos oficiais; dois compromissos quantitativos catalogados.
- Ronaldo Caiado: 26 excertos oficiais; sete compromissos quantitativos catalogados.
- Os demais dossiers contêm de dez a doze excertos oficiais nesta seleção.

Os números descrevem a coleta, não a completude dos programas integrais. Saturar detecções e normalizar por eixo não elimina a oportunidade adicional de detectar características quando há mais trechos examinados. Isso é risco de viés de seleção; não demonstra que qualquer candidatura necessariamente deva ocupar outra posição.

O ranking atual mede detecções documentais em uma seleção desigual. Não demonstra que Flávio escreva melhor, possua o melhor programa ou governaria melhor. As simulações macro são comuns e não justificam a ordem das candidaturas.

## Onde buscar evidências adicionais

1. **Propostas completas e anexos oficiais**: reexaminar integralmente os planos depositados no TSE, usando o mesmo protocolo de busca para todos. O ZIP e os hashes do corte pesquisado estão em `research/program_manifest.json` e nos dossiers; fonte: https://cdn.tse.jus.br/estatistica/sead/odsele/proposta_governo/proposta_governo_2026_BR.zip . A fonte deve ser validada novamente antes de atualizar o corpus; não presumir que o arquivo remoto permanece igual.
2. **Execução fiscal e entregas administrativas**: Siconfi/Tesouro, relatórios RREO/RGF/DCA, orçamento autorizado e executado, além de PPA/LDO/LOA e auditorias TCU/TCE. Portal oficial localizado: https://www.gov.br/tesouronacional/pt-br/estados-e-municipios/siconfi . Contas de exercícios diferentes e parecer prévio não constituem uma escala comum de desempenho ou honestidade.
3. **Histórico legislativo**: proposições, tramitação e votações na Câmara e no Senado. Portal oficial consultado: https://dadosabertos.camara.leg.br/ . Aprovação de uma lei não prova autoria exclusiva nem efeito causal; quantidade de projetos não é produtividade social. Atuação legislativa não equivale a gestão executiva.
4. **Resultados sociais observados**: IBGE para renda e emprego; Inep para Ideb/Saeb/fluxo escolar; DATASUS para mortalidade, morbidade e assistência. Fontes localizadas: https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/indicadores-educacionais e https://datasus.saude.gov.br/informacoes-de-saude-tabnet/ . Não atribuir toda mudança a um governante nem comparar diretamente estados e União.
5. **Custos e plausibilidade das propostas**: estudos e estimativas técnicas da IFI, Ipea e consultorias orçamentárias, quando cobrirem a medida em questão. Fonte primária localizada: https://www12.senado.leg.br/ifi/relatorio-de-acompanhamento-fiscal . A existência de projeções fiscais agregadas não significa que haja custeio independente de cada programa eleitoral.

As buscas desta rodada localizaram os recursos acima; isso NÃO significa que todos esses bancos tenham sido incorporados, todas as medidas custeadas ou todos os governos auditados.

## Procedimento recomendado antes de uma nova classificação

- Definir critérios antes da nova coleta e aplicá-los a todos os documentos integrais; conservar páginas, citações e logs de busca, inclusive buscas negativas.
- Separar declaração, detalhamento, custo independente, execução comprovada e resultado observado. Não converter essas categorias automaticamente em efeito causal.
- Para avaliar resultados, usar períodos, competências, deflatores, contexto herdado e grupos comparáveis; testar sensibilidade e contrafactuais quando os dados permitirem.
- Onde não houver experiência executiva comparável, registrar desconhecido; não penalizar com zero nem transferir resultados de familiares, partidos ou outros governantes.
- Revisar anotações de forma independente, idealmente com identidade da candidatura ocultada quando possível, registrando discordâncias.
- Não ajustar critérios para produzir um vencedor esperado. Até haver comparabilidade, manter o ranking documental como exploração limitada ou preferir um quadro de evidências sem vencedor de governo.

Nesta rodada foram auditadas a cobertura do corpus e fontes adicionais. Nenhuma nota, peso ou posição foi alterada.
