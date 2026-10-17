"""Normalização sem imputação ou atribuição de indicadores a governantes."""
import math

MISSING = {'-', '...', '..', 'X', '', 'C'}


def normalize_ibge(data, aggregate, expected_variable):
    if len(data) != 1 or str(data[0]['id']) != str(expected_variable):
        raise ValueError('Resposta IBGE de variável inesperada')
    variable = data[0]
    rows = []
    seen = set()
    for result in variable['resultados']:
        classifications = result['classificacoes']
        for series in result['series']:
            entity = series['localidade']
            for period, value in sorted(series['serie'].items()):
                number = None if value in MISSING else float(value)
                if number is not None and not math.isfinite(number):
                    raise ValueError('Valor IBGE não finito')
                # Distinções das classificações nunca são descartadas no dedup.
                key = (entity['id'], period, str(classifications))
                if key in seen:
                    raise ValueError('Observação duplicada na mesma classificação')
                seen.add(key)
                rows.append({'aggregate': aggregate, 'variable': expected_variable,
                             'label': variable['variavel'], 'unit': variable['unidade'],
                             'entity_id': entity['id'], 'entity': entity['nome'],
                             'territorial_level': entity['nivel']['id'], 'period': period,
                             'source_value': value, 'value': number, 'classifications': classifications,
                             'candidate_id': None})
    return rows
