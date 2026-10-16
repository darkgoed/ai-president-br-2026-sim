# Presidente IA — Brasil 2026

Experimento educacional do Tour Cyber: pesquisa documental das 12 candidaturas com votos válidos no primeiro turno de 2026 e benchmark numérico reproduzível. Não é previsão eleitoral, avaliação causal de governos ou recomendação de voto.

## Resultado científico

A pesquisa documenta propostas, mas não identifica efeitos causais comparáveis para os 12 programas. Portanto não há vencedor, ranking nem empate político. Ausência de efeito identificado não é efeito zero.

O motor executa 1.000 trajetórias hipotéticas comuns de dinâmica de dívida em quatro anos, em oito famílias balanceadas. Os 12 perfis são avaliados frente às mesmas condições; isso corresponde a 12.000 avaliações perfil/cenário, NÃO a 12.000 mundos independentes nem a 12.000 governos previstos. Os resultados políticos de renda, emprego, inflação, segurança, saúde e educação permanecem desconhecidos.

## Instalação e execução

Requer Python 3.14 e NumPy fixado. Sem APIs de IA durante as simulações.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m src.cli research
python -m src.cli validate
python -m src.cli simulate --runs 1000 --seed 20261015
python -m src.cli sensitivity --runs 1000 --seed 20261015
python -m src.cli simulate --scenario fiscal --out results-fiscal
python -m src.cli report
python -m src.cli export
python -m pytest -q
```

Exportação: `results/results.json`, `trajectories.csv`, `profiles.csv`, `report.md`, `report.txt` e `sensitivity.json`. CSV de perfis deixa efeitos vazios e identifica a ausência; não grava zero.

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

`data/strategies.json` usa o mesmo esquema para os 12 nomes. Propostas qualitativas e metas declaradas não viram coeficientes. O motor rejeita efeitos políticos preenchidos sem modelo identificado. Pesos alternativos não fabricam resultados sociais ausentes; por isso não há índice composto nem inversões de ranking a reportar.

Os compromissos também estão preservados nos snapshots documentais de `data/strategies.json` e `research/impacts.json`. Esses snapshots correspondem à versão usada na execução publicada. Campos numéricos documentais complementares (unidades, metas e horizontes) foram posteriormente explicitados nos dossiers `research/candidates/`, que são a referência atual para essa catalogação. Isso não preenche efeitos causais nem altera as trajetórias; uma meta de dez anos não foi dividida para fabricar entrega em quatro anos.

## Reprodutibilidade e testes

Verifique novamente os 199 excertos nos PDFs oficiais com `python tools/verify_sources.py` (requer rede). A ferramenta confere hashes e páginas; mudanças posteriores da fonte são reportadas. `evidence/terminal.png` é uma renderização literal de stdout real, não uma foto de emulador GUI. O log e o hash acompanham a imagem. Para regenerar, instale Pillow e execute `python tools/capture_terminal.py`.

Seed padrão 20261015; gerador PCG64. Mesmo ambiente, configuração e seed reproduzem os mesmos resultados. `run_id` inclui hashes dos insumos. Alterar nomes/partidos/ordem não altera trajetória numérica, embora o hash documental mude. Testes verificam fórmula analítica, sinal, unidades, seed, simetria, lacunas, pesos, sensibilidade, votos, exportação e contagens. Resultados de robustez ficam separados da execução principal.

## Limitações documentais

A seleção temática não é inventário exaustivo de todas as propostas. Os documentos têm 7–200 páginas e os dossiers diferem em quantidade de excertos. Não há nota por tamanho de programa, documentação ou orientação política. Custos dos próprios programas não são estimativas independentes; histórico administrativo não foi validado uniformemente. Essas lacunas bloqueiam a comparação causal, não justificam penalidades.

## Licença e audiovisual

Código sob MIT. Citações e dados de terceiros mantêm sua autoria/licença original; MIT não relicencia os planos. Este repositório não contém vídeo, projeto Remotion, narração, retratos, assets privados ou credenciais. A produção audiovisual é separada.
