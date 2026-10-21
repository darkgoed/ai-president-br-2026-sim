# Ranking exploratório dos planos — avaliação assistida por IA (v2, 17/10/2026)

RANKING EXPLORATÓRIO DOS PLANOS — AVALIAÇÃO ASSISTIDA POR IA · não é previsão, não é recomendação de voto.

## O que mede (e o que não mede)

Mede características verificáveis do TEXTO dos 12 planos entregues ao TSE: especificidade das medidas, diagnóstico e
evidência, reconhecimento de riscos/contrapartidas (5 temas), custos, financiamento e regra fiscal, metas, prazos,
instrumentos e monitoramento. Não mede se a proposta é boa no mérito, se funcionaria, a superioridade do partido nem a
chance de bom governo. O partido identifica a candidatura (registro TSE na data de corte); não é nota do partido.

Fora da nota, por protocolo: histórico de gestão, mandatos, experiência, popularidade, votos e as frequências do bilhão de
cenários (`results-1b-streaming-v2`, contexto macro comum a todos: em 81,10% dos cenários a dívida/PIB sobe — isso é o
desafio fiscal de quem governar, não nota de ninguém).

O protocolo v1 (`research/comparison_protocol_v1.json`) continua bloqueado e não foi satisfeito: ele exige histórico
comparável e dupla revisão humana. A v2 tem outro propósito, com regras novas, congeladas antes de pontuar.

## Método

- Protocolo e rubrica: `research/plan_comparison_protocol_v2.json`, sha256 f907ac41… congelado em
  `research/plan_comparison_v2_freeze.json` antes da primeira nota. 7 dimensões (economia, saúde, educação, segurança,
  ambiente; fiscal e execução como transversais do plano inteiro), 22 critérios com âncoras 0–3.
- Pesos iguais 1/7 por dimensão (escolha editorial; dimensão com mais critérios não pesa mais). Dimensão = média dos
  critérios ÷ 3 × 100. Empate: 1 casa decimal, posição compartilhada.
- Avaliador: claude-opus-5-5 (Anthropic), passagem única, sem revisão humana (`ai_single_pass_unreviewed`). Uma segunda
  passagem do mesmo modelo não seria dupla codificação independente; nenhuma foi feita. O avaliador conhece candidatos e
  partidos pelo treinamento: nome e partido não entram no cálculo, mas o julgamento não é cego.
- Navegação uniforme: `tools/navigate_plans_v2.py` aplica o mesmo léxico a todas as páginas de todos os planos. Leitura
  integral dos planos curtos (PCO 7 págs, DC 15, PCB 16); nos longos, páginas inteiras de maior densidade por dimensão,
  índices/cabeçalhos de projeto e varredura do texto integral por custos (R$), regras fiscais, anos-meta e instrumentos.
  Contagem de termos só navega, nunca pontua.
- Regras de desempate de âncora criadas durante a avaliação, antes de qualquer agregado: `research/plan_assessment_v2/CALIBRATION.json`
  (C1–C8; C7 foi reaplicada aos planos já avaliados). Ex.: C8 — resultado de mandato citado no plano só conta como
  diagnóstico, não como meta/custo/medida.
- Cada célula: candidatura, dimensão, critério, nota, status, faixa se incerta, página, trecho literal, justificativa,
  limitação, status de revisão. 220 trechos verificados por máquina no PDF (sha256 do manifesto): 0 falhas.
- Status: `assessed`, `absent_after_review` (o atributo não está no plano; vale 0 só porque a âncora define 0 como
  ausência de especificação — não é impacto negativo), `uncertain` (nota com faixa), `unavailable`/`not_applicable`
  (null; tiraria a dimensão de TODAS as candidaturas). Nenhuma célula ficou null, então as 7 dimensões valem para todos.

## Tabela calculada

Faixa = notas com todas as células incertas no mínimo e no máximo. Grade = pior e melhor posição nos 8.008 vetores de
pesos (passo 0,1 nas 7 dimensões, pesos zero permitidos). 1º = vetores em que lidera (empate conta para todos).

| Pos | Candidatura — partido | Geral | Econ | Saúde | Educ | Seg | Amb | Fiscal | Exec | Faixa | Grade | 1º em | Cobertura (aval./incerta/ausente; págs inteiras) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | VETERINÁRIO WILSON GRASSI — DEMOCRATA | 84,1 | 100,0 | 66,7 | 66,7 | 100,0 | 55,6 | 100,0 | 100,0 | 76,6–87,3 | 1–6 | 7.183 | 15/7/0; 17 |
| 2 | RENAN SANTOS — MISSÃO | 70,6 | 66,7 | 77,8 | 77,8 | 77,8 | 22,2 | 88,9 | 83,3 | 59,9–77,0 | 1–10 | 221 | 10/11/1; 13 |
| 3 | RONALDO CAIADO — PSD | 67,9 | 55,6 | 77,8 | 88,9 | 66,7 | 55,6 | 55,6 | 75,0 | 57,1–75,4 | 1–7 | 666 | 9/12/1; 18 |
| 4 | ESCRITOR AUGUSTO CURY — AVANTE | 59,5 | 77,8 | 55,6 | 44,4 | 55,6 | 66,7 | 66,7 | 50,0 | 48,4–67,5 | 1–7 | 31 | 9/12/1; 15 |
| 5 | LULA — PT | 56,0 | 55,6 | 66,7 | 44,4 | 66,7 | 66,7 | 33,3 | 58,3 | 45,2–62,3 | 1–9 | 34 | 9/11/2; 10 |
| 6 | FLAVIO BOLSONARO — PL | 55,6 | 55,6 | 66,7 | 66,7 | 44,4 | 55,6 | 33,3 | 66,7 | 48,4–66,7 | 2–9 | 0 | 8/12/2; 10 |
| 7 | SAMARA — UP | 50,8 | 55,6 | 44,4 | 55,6 | 55,6 | 66,7 | 44,4 | 33,3 | 39,7–57,1 | 1–11 | 7 | 8/10/4; 11 |
| 8 | ZEMA — NOVO | 49,2 | 55,6 | 44,4 | 44,4 | 44,4 | 66,7 | 55,6 | 33,3 | 47,6–63,1 | 1–11 | 1 | 8/10/4; 12 |
| 9 | HERTZ DIAS — PSTU | 43,7 | 55,6 | 33,3 | 33,3 | 44,4 | 55,6 | 33,3 | 50,0 | 32,1–46,8 | 4–11 | 0 | 7/9/6; 12 |
| 10 | EDMILSON COSTA — PCB | 38,9 | 33,3 | 33,3 | 44,4 | 33,3 | 33,3 | 44,4 | 50,0 | 36,1–45,2 | 5–11 | 0 | 11/6/5; 16 (integral) |
| 11 | RUI COSTA PIMENTA — PCO | 30,2 | 33,3 | 33,3 | 33,3 | 33,3 | 11,1 | 33,3 | 33,3 | 23,0–31,7 | 8–12 | 0 | 9/5/8; 7 (integral) |
| 12 | CLARIANA BARAO — DC | 22,6 | 11,1 | 33,3 | 11,1 | 22,2 | 0,0 | 22,2 | 58,3 | 18,7–22,6 | 5–12 | 0 | 8/3/11; 15 (integral) |

## Sensibilidade — o que é estável e o que depende dos pesos

- Estável: o 1º lugar (DEMOCRATA) se mantém com qualquer dimensão retirada, nos blocos só temas e só transversais e nos
  extremos das células incertas; lidera em 7.183 de 8.008 vetores de pesos (89,7%). Os dois últimos (PCO, DC) também se
  mantêm nos testes de retirada e de incerteza.
- Depende de pesos: 2º e 3º trocam (sem a dimensão fiscal ou só com temas, PSD passa MISSÃO). MISSÃO cai até 10º quando o
  peso vai quase todo para ambiente (sua pior dimensão, 22,2).
- Praticamente empatados: 4º a 8º. LULA (56,0) e FLAVIO BOLSONARO (55,6) estão a 0,4 ponto, e as faixas de incerteza se
  sobrepõem. No extremo mínimo, FLAVIO BOLSONARO e CURY empatam em 4º e LULA vai a 7º; ZEMA vai a 6º nos dois extremos.
  Essa ordem intermediária não deve ser lida como diferença real.
- Frequência de liderança mede robustez da ordenação a pesos, não probabilidade de bom governo.

## Melhor argumento contra o 1º e a favor do último

- DEMOCRATA: o fiscal 100 vem de uma proposta central (tributo único) com conta própria e gatilho de suspensão; o plano
  declara que não orça medida a medida. A rubrica premia mostrar a conta, não a conta estar certa — a viabilidade do
  tributo único não é avaliada. Ambiente (55,6) e saúde/educação (66,7) são medianos.
- DC: é declaradamente uma "versão estruturada para debate técnico", com metas numéricas adiadas para depois do
  diagnóstico oficial. Tem a 4ª melhor nota de execução (58,3: faseamento de 100 dias a ano 4, indicadores por item,
  painel e avaliação independente). A nota baixa vem da ausência de detalhamento das medidas e de capítulo ambiental,
  não de proposta ruim.

## Limitações

- Passagem única de IA, sem revisão humana; 108 de 264 células (41%) estão marcadas como incertas. Mantenha o rótulo.
- A rubrica favorece por construção planos técnicos e detalhados sobre manifestos programáticos (PCO declara não fazer
  promessas). Isso é escolha editorial, registrada no protocolo.
- Nos planos longos não li todas as páginas inteiras; a ausência de um atributo foi afirmada só após busca no texto
  integral, mas pode haver omissão. As páginas lidas inteiras estão em cada `research/plan_assessment_v2/<id>.json`.
- Um PDF (UP) tem texto em duas colunas duplicado na extração; os trechos foram conferidos no texto extraído.
- A nota não avalia a viabilidade jurídica ou econômica das propostas, nem se as fontes de financiamento existem.

## Reprodução

    python3 -m venv .venv
    .venv/bin/python -m pip install -r requirements-dev.txt
    .venv/bin/python tools/verify_sources.py         # baixa e verifica os PDFs do TSE
    .venv/bin/python -m src.plan_comparison_v2 --out results-plan-comparison-reproduced
    .venv/bin/python -m pytest -q tests/test_plan_comparison_v2.py

Insumos: `.cache/programs.zip` (TSE, sha256 por PDF em `research/program_manifest.json`), avaliações em
`research/plan_assessment_v2/`. Para mudar pesos, edite um protocolo v2.x novo e recongele; o código recusa protocolo
alterado sem novo congelamento.
