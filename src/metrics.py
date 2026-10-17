"""Indicadores contábeis do benchmark, sem efeitos atribuídos a candidatos."""
import numpy as np


def fiscal_metrics(debt, draws):
    """Debt em frações do PIB; retornos em %, pontos percentuais ou anos."""
    pct = debt * 100
    end = pct[:, -1]
    changes = np.diff(pct, axis=1)
    interest, growth, primary = (draws[:, :, i] for i in range(3))
    # Convert the interest bill on last year's stock to this year's GDP.
    cost = interest / (1 + growth) * debt[:, :-1] * 100
    snowball = ((1 + interest) / (1 + growth) - 1) * debt[:, :-1] * 100
    gap = snowball - primary * 100
    indicators = []

    def add(key, label, value, unit, formula):
        indicators.append({'id': key, 'label': label, 'value': float(value),
                           'unit': unit, 'definition': formula,
                           'classification': 'hypothetical_not_forecast'})

    add('initial_debt', 'Dívida inicial', pct[:, 0].mean(), '% PIB', 'Dívida no ano zero.')
    add('final_debt', 'Dívida final média', end.mean(), '% PIB', 'Média entre trajetórias no último ano.')
    for key, label, value in [('median', 'mediana', np.median(end)),
                              ('std', 'desvio amostral', end.std(ddof=1)),
                              ('min', 'mínima', end.min()), ('max', 'máxima', end.max())]:
        add('final_' + key, 'Dívida final: ' + label, value, '% PIB', 'Distribuição artificial da dívida final.')
    for q in [2.5, 10, 25, 75, 90, 97.5]:
        add('final_q' + str(q), f'Dívida final: percentil {q:g}', np.percentile(end, q), '% PIB',
            'Quantil de stress; não é intervalo de confiança de previsão.')
    add('debt_change', 'Variação total da dívida', (end - pct[:, 0]).mean(), 'p.p. PIB', 'Média de dívida final menos inicial.')
    add('annual_debt_change', 'Variação anual média da dívida', changes.mean(), 'p.p. PIB/ano', 'Média das diferenças anuais.')
    add('peak_debt', 'Pico médio da dívida', pct.max(axis=1).mean(), '% PIB', 'Média dos máximos por trajetória, incluindo ano zero.')
    add('worst_tail', 'Dívida média na cauda superior de 10%', end[end >= np.percentile(end, 90)].mean(), '% PIB',
        'Média das trajetórias com dívida final igual ou superior ao percentil 90; inclui empates.')
    add('debt_increases', 'Trajetórias com dívida crescente no horizonte', np.mean(end > pct[:, 0]) * 100, '% trajetórias',
        'Frequência simulada de dívida final > inicial; não probabilidade do Brasil.')
    add('debt_decreases', 'Trajetórias com dívida menor no horizonte', np.mean(end < pct[:, 0]) * 100, '% trajetórias',
        'Frequência simulada de dívida final < inicial.')
    add('all_years_increase', 'Alta da dívida em todos os anos', np.all(changes > 0, axis=1).mean() * 100, '% trajetórias',
        'Todos os incrementos anuais estritamente positivos.')
    for threshold in [80, 90, 100, 120]:
        add(f'end_above_{threshold}', f'Dívida final acima de {threshold}% PIB', np.mean(end > threshold) * 100, '% trajetórias',
            f'Frequência estritamente acima de {threshold}% PIB no último ano; limiar ilustrativo, não limite legal.')
        add(f'ever_above_{threshold}', f'Dívida supera {threshold}% PIB durante o mandato', np.any(pct[:, 1:] > threshold, axis=1).mean() * 100, '% trajetórias',
            'Considera anos simulados, excluindo ano zero; limiar ilustrativo.')
    for key, label, array in [('interest', 'Juros nominais efetivos médios', interest),
                               ('growth', 'Crescimento nominal médio', growth),
                               ('primary', 'Superávit primário médio', primary)]:
        add(key + '_mean', label, array.mean() * 100, '% a.a.' if key != 'primary' else '% PIB', 'Média dos parâmetros efetivamente sorteados.')
    add('interest_growth_spread', 'Diferença juros–crescimento nominal', (interest - growth).mean() * 100, 'p.p./ano', 'Média de juros nominais menos crescimento nominal.')
    add('interest_cost', 'Juros sobre estoque inicial no primeiro ano', cost[:, 0].mean(), '% PIB', 'i[1] × d[0] / (1 + g[1]) × 100.')
    add('mean_interest_cost', 'Custo anual médio dos juros', cost.mean(), '% PIB', 'Média dos juros sobre estoque anterior, em PIB corrente.')
    add('stabilizing_primary', 'Primário estabilizador no primeiro ano', snowball[:, 0].mean(), '% PIB', '((1+i)/(1+g) − 1) × dívida inicial × 100.')
    add('mean_stabilizing_primary', 'Primário estabilizador médio', snowball.mean(), '% PIB', 'Primário necessário para manter dívida/PIB de cada ano anterior.')
    add('fiscal_gap', 'Ajuste primário médio para estabilizar dívida', gap.mean(), 'p.p. PIB', 'Primário estabilizador menos primário sorteado; positivo indica ajuste necessário.')
    add('primary_deficit_years', 'Anos com déficit primário', (primary < 0).mean() * 100, '% anos-trajetória', 'Fração de observações anuais com primário negativo.')
    add('snowball_positive_years', 'Anos com efeito bola de neve positivo', (snowball > 0).mean() * 100, '% anos-trajetória', 'Fração anual com contribuição juros/crescimento elevando dívida.')
    annual = []
    for t in range(draws.shape[1]):
        year = t + 1
        for key, label, value, unit in [
            ('debt_median', 'Dívida mediana', np.median(pct[:, year]), '% PIB'),
            ('debt_q10', 'Dívida: percentil 10', np.percentile(pct[:, year], 10), '% PIB'),
            ('debt_q90', 'Dívida: percentil 90', np.percentile(pct[:, year], 90), '% PIB'),
            ('change_q10', 'Variação da dívida: percentil 10', np.percentile(changes[:, t], 10), 'p.p. PIB'),
            ('change_q90', 'Variação da dívida: percentil 90', np.percentile(changes[:, t], 90), 'p.p. PIB'),
            ('interest', 'Juros efetivos médios', interest[:, t].mean() * 100, '% a.a.'),
            ('growth', 'Crescimento nominal médio', growth[:, t].mean() * 100, '% a.a.'),
            ('primary', 'Primário médio', primary[:, t].mean() * 100, '% PIB'),
            ('interest_cost', 'Custo médio dos juros', cost[:, t].mean(), '% PIB'),
            ('stabilizing_primary', 'Primário estabilizador médio', snowball[:, t].mean(), '% PIB'),
            ('fiscal_gap', 'Ajuste primário médio', gap[:, t].mean(), 'p.p. PIB'),
            ('above_100', 'Frequência de dívida >100% PIB', (pct[:, year] > 100).mean() * 100, '% trajetórias'),
            ('above_120', 'Frequência de dívida >120% PIB', (pct[:, year] > 120).mean() * 100, '% trajetórias'),
        ]:
            add(f'year_{year}_{key}', f'Ano {year}: {label}', value, unit,
                f'Estatística entre trajetórias no ano {year}; mesmas identidades contábeis do horizonte. Não é previsão nem probabilidade real.')
        annual.append({'year': t + 1, 'debt_mean_pct_gdp': float(pct[:, t+1].mean()),
                       'debt_q10_pct_gdp': float(np.percentile(pct[:, t+1], 10)),
                       'debt_q90_pct_gdp': float(np.percentile(pct[:, t+1], 90)),
                       'change_mean_pp': float(changes[:, t].mean()),
                       'interest_cost_mean_pct_gdp': float(cost[:, t].mean()),
                       'stabilizing_primary_mean_pct_gdp': float(snowball[:, t].mean()),
                       'primary_mean_pct_gdp': float(primary[:, t].mean() * 100)})
    return {'classification': 'hypothetical_not_forecast', 'indicators': indicators, 'annual': annual,
            'warning': 'Frequências e quantis de hipóteses artificiais; não são chances reais de um governo.'}
