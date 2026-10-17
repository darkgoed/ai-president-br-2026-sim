# Um bilhão de sorteios — resultados para o vídeo

Entrega final: results-1b-streaming-v2/streaming_results.json.
Replay integral aprovado: results-1b-streaming-v2/verification.json.
Run ID: e278209a4ccbfc9a6d8c5bbd23af65f38552486708072c43113d832969d33b48.

## Execução real

Foram executados 1.000.000.000 de sorteios de quatro blocos anuais históricos
com reposição, em lotes de 100.000. O horizonte é de quatro anos. O modelo é o
mesmo bootstrap conjunto das quatro séries históricas auditadas, não um modelo
causal de políticas. Não usamos planos como coeficientes nem computamos chances
individuais de candidatos. Não é um bilhão de estudos ou trajetórias distintas.

Para não ocupar centenas de GB, foram preservadas contagens inteiras, snapshot,
seed, versão/hashes do código, estado final do RNG e SHA256 de todo o fluxo dos
índices. Caminhos individuais e quantis do bilhão não foram armazenados.

## Resultados condicionais ao modelo

| Evento ao final de quatro anos | Contagem no bilhão | Percentual para o vídeo |
|---|---:|---:|
| Dívida/PIB maior que a inicial | 811043175 | 81,10% |
| Desocupação menor que a inicial | 595979577 | 59,60% |
| IBC-Br maior que o inicial | 680084641 | 68,01% |
| IBC-Br cresce E desocupação diminui | 508150032 | 50,82% |

Eventos se sobrepõem: não somar como se fossem candidatos ou categorias exclusivas.
IBC-Br não é PIB. Esses percentuais não são probabilidade de acontecer no mundo
real, de vitória eleitoral ou de sucesso de governo.

## Verificação e correção antes da entrega

O primeiro replay integral detectou empate numérico da desocupação classificado
como queda pelo arredondamento da transformação inversa logit. A execução
preliminar foi mantida em results-1b-streaming/ com aviso NAO-USAR. Não foi
apagada nem usada no prompt final. A versão v2 conta sinais nas transformações
monotônicas, com tolerância declarada de 1e-12 para empates numéricos, e foi
integralmente executada novamente.

Uma segunda implementação percorreu os mesmos 1.000.000.000 de sorteios com lotes
de 77.777. Todos os índices, seu hash e as contagens dos eventos coincidiram.
Um oráculo por razões diretas dos níveis/odds e produto de inflação conferiu a
construção das janelas. O verificador não chama project/annual_blocks do runner.
A suíte final contém 102 testes aprovados; git diff --check aprovado.

Reproduzir com novo destino a partir da raiz do projeto:

    .venv/bin/python -c "import json;from pathlib import Path;from src.streaming import run_streaming;run_streaming(json.loads(Path('data/empirical_monthly.json').read_text()),'results-1b-novo',runs=1000000000,batch_size=100000,seed=20261015)"
    .venv/bin/python tools/verify_streaming.py results-1b-novo

O código não oferece retomada parcial: progress.json é diagnóstico de progresso,
não promessa de checkpoint recuperável. Usar processo único com recursos limitados
no host compartilhado. Uma execução incompleta não deve ser anunciada como concluída.

## Vídeo

Prompt: ../production/PROMPT-RESULTADOS-1B.txt (relativo ao projeto presidencia,
isto é, /var/www/ferramentas/videos/presidencia/production/PROMPT-RESULTADOS-1B.txt).
Dados para cards: /var/www/ferramentas/videos/presidencia/production/resultados-1b-video.json.

Preserva a identidade arcade escura/ciano, sprites, fontes, câmera e tratamento
igual do elenco. Troca o clímax por resultados do MODELO, não por porcentagens
políticas. Corrige cinco anos para quatro e proíbe apresentar planos documentais
como calibradores dos efeitos de governo. Prompt e dados estão prontos; o vídeo
não foi editado nem renderizado nesta entrega. Sem commit, push ou publicação.

## Limites mantidos

O bilhão reduz apenas ruído Monte Carlo; não melhora o backtest nem supera por
si as baselines simples. Dois cortes de quatro anos continuam insuficientes.
A precisão decimal não é certeza factual. O vídeo deve dizer 'em X% dos cenários
simulados' e exibir 'SIMULAÇÃO · 4 ANOS · NÃO É PREVISÃO', nunca 'X% de chance
real'. Não esconder as limitações para transformar a peça em aparente resultado
científico de candidato.
