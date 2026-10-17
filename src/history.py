"""Resumos territoriais: mesma definição para todos, sem nota de governante."""
import math
from statistics import mean, stdev


def summarize_history(data) -> dict:
    summaries = []
    for series in data['series']:
        rows = series['observations']
        if not rows or any(not math.isfinite(r['value']) for r in rows):
            raise ValueError('Série histórica vazia ou não finita')
        periods = [r['period'] for r in rows]
        if periods != sorted(set(periods)):
            raise ValueError('Períodos históricos duplicados ou fora de ordem')
        values = [r['value'] for r in rows]
        last = rows[-1]
        previous_year = str(int(last['period'][:4]) - 1) + last['period'][4:]
        year_ago = next((r for r in rows if r['period'] == previous_year), None)
        # Um recorte territorial fixo, não uma janela causal de mandato.
        baseline_period = '201804' if len(last['period']) == 6 else '2018'
        baseline = next((r for r in rows if r['period'] == baseline_period), None)
        summaries.append({'id': series['id'], 'location': series['location'], 'label': series['label'],
                          'unit': series['unit'], 'frequency': series['frequency'], 'url': series['url'],
                          'n': len(rows), 'first_period': rows[0]['period'], 'last_period': last['period'],
                          'latest': last['value'], 'previous': rows[-2]['value'] if len(rows) > 1 else None,
                          'mean': mean(values), 'min': min(values), 'max': max(values),
                          'std': stdev(values) if len(values) > 1 else None,
                          'year_ago': year_ago['value'] if year_ago else None,
                          'change_year_ago': last['value'] - year_ago['value'] if year_ago else None,
                          'baseline_period': baseline_period, 'baseline': baseline['value'] if baseline else None,
                          'change_baseline': last['value'] - baseline['value'] if baseline else None,
                          'classification': 'historical_descriptive_not_causal'})
    return dict(data, summaries=summaries,
                warning='Mudanças territoriais não são efeitos de governantes. PIB aqui é nominal, não crescimento real. Renda real usa deflator da edição coletada. PNADC tem incerteza amostral; trimestre não é mês. Choques, sucessores, competências e composição diferem.')
