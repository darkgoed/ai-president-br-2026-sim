"""Diagnósticos de erro numérico e fragilidade, nunca confiança em governos."""
from collections import Counter
from datetime import date, datetime, timezone
import math
import numpy as np


def _stratified_estimate(values, families, weights):
    estimates = []
    variance = 0.0
    enough = True
    for family, weight in weights.items():
        sample = values[families == family]
        n = len(sample)
        if not n:
            return {'mean_pct_gdp': None, 'mc_se_pp_gdp': None,
                    'mc_approx_95_half_width_pp_gdp': None, 'status': 'missing_scenario_stratum'}
        estimates.append(weight * float(sample.mean()))
        if n < 2:
            enough = False
        else:
            variance += weight**2 * float(sample.var(ddof=1)) / n
    se = math.sqrt(variance) if enough else None
    return {'mean_pct_gdp': math.fsum(estimates), 'mc_se_pp_gdp': se,
            'mc_approx_95_half_width_pp_gdp': 1.96 * se if se is not None else None,
            'status': 'estimated' if enough else 'insufficient_within_family_replication'}


def macro_diagnostics(result):
    rows = result['reference']['trajectories']
    counts = result['reference']['scenario_counts']
    if not rows or Counter(r['family'] for r in rows) != counts:
        raise ValueError('Contagens de cenários não conferem com trajetórias')
    if len({r['scenario_id'] for r in rows}) != len(rows):
        raise ValueError('IDs de trajetórias duplicados')
    values = np.array([r['debt_pct_gdp'][-1] for r in rows], dtype=float)
    if not np.isfinite(values).all():
        raise ValueError('Dívida final não finita')
    families = np.array([r['family'] for r in rows])
    weights = {key: count / len(rows) for key, count in counts.items()}
    full = _stratified_estimate(values, families, weights)
    convergence = []
    for n in sorted({n for n in [100, 1000, 10_000, 50_000, len(rows)] if n <= len(rows)}):
        estimate = _stratified_estimate(values[:n], families[:n], weights)
        convergence.append(dict(estimate, runs=n,
                                delta_from_full_pp=estimate['mean_pct_gdp'] - full['mean_pct_gdp'] if estimate['mean_pct_gdp'] is not None else None))
    by_family = {}
    for family in counts:
        sample = values[families == family]
        by_family[family] = dict(_stratified_estimate(sample, np.full(len(sample), family), {family: 1.0}), n=len(sample))
    return dict(full, classification='numerical_error_conditional_on_artificial_model',
                runs=len(rows), scenario_weights=weights, by_family=by_family, convergence=convergence,
                normal_approximation_small_strata=any(n < 30 for n in counts.values()),
                formula='SE = sqrt(sum_h(w_h^2 * sample_variance_h / n_h)); normal half-width = 1.96 * SE',
                warning='Erro Monte Carlo da média do laboratório. Não cobre hipótese errada, viés, dados ausentes, erro estrutural ou previsão de governos. Prefixos da mesma execução não são replicações independentes; aproximação normal exige amostras adequadas por família.')


def ranking_diagnostics(ranking):
    axes = ranking['common_axes']
    criteria = [c['id'] for c in ranking['protocol']['criteria']]
    candidates = ranking['candidates']
    if not axes or not criteria or not candidates:
        raise ValueError('Ranking sem dimensões comparáveis')
    matrices = []
    for candidate in candidates:
        lookup = {(i['axis'], i['criterion']): i['detected'] for i in candidate['indicators']}
        cells = [[lookup.get((axis, criterion)) for criterion in criteria] for axis in axes]
        if any(type(value) is not bool for row in cells for value in row):
            raise ValueError('Critério comum não revisado; não pode virar zero')
        matrices.append(cells)
    matrix = np.asarray(matrices, dtype=float)

    def positions(scores):
        return [int(1 + np.sum(scores > score + 1e-10)) for score in scores]

    def leaders(scores):
        return sorted(candidates[j]['id'] for j, value in enumerate(scores) if abs(value - scores.max()) <= 1e-10)

    base = matrix.mean(axis=(1, 2)) * 100
    base_positions = positions(base)
    baseline_leaders = leaders(base)
    variants = []
    for dimension, names, array_axis in [('axis', axes, 1), ('criterion', criteria, 2)]:
        if len(names) < 2:
            continue
        for index, name in enumerate(names):
            scores = np.delete(matrix, index, axis=array_axis).mean(axis=(1, 2)) * 100
            variant_positions = positions(scores)
            variants.append({'removed_dimension': dimension, 'removed': name,
                             'leaders': leaders(scores),
                             'positions': {c['id']: variant_positions[j] for j, c in enumerate(candidates)}})
    fragility = []
    for j, candidate in enumerate(candidates):
        observed_positions = [base_positions[j]] + [v['positions'][candidate['id']] for v in variants]
        fragility.append({'id': candidate['id'], 'name': candidate['name'],
                          'baseline_position': base_positions[j], 'best_position': min(observed_positions),
                          'worst_position': max(observed_positions),
                          'max_position_shift': max(abs(p - base_positions[j]) for p in observed_positions)})
    dominance = [{'dominant_id': a['id'], 'dominated_id': b['id']}
                 for i, a in enumerate(candidates) for j, b in enumerate(candidates)
                 if i != j and np.all(matrix[i] >= matrix[j]) and np.any(matrix[i] > matrix[j])]
    return {'classification': 'documentary_method_sensitivity_not_government_confidence',
            'status': 'assessed' if variants else 'insufficient_dimensions',
            'baseline_leaders': baseline_leaders, 'variants': variants,
            'leader_set_changes': sum(v['leaders'] != baseline_leaders for v in variants),
            'candidate_fragility': fragility, 'documentary_dominance_pairs': dominance,
            'government_performance_validated': False,
            'warning': 'Remove um eixo ou critério por vez e recalcula pesos iguais nos restantes. Conta escolhas metodológicas, não probabilidades. Dominância refere-se apenas às detecções documentais; não prova superioridade de governo.'}


def build_diagnostics(result, as_of=None):
    as_of = as_of or datetime.now(timezone.utc).date()
    observed = result.get('observed', {})
    history = result.get('history', {})
    collected = observed.get('retrieved_at')
    collected_date = datetime.fromisoformat(collected).date() if collected else None
    series_quality = []
    invalid_values = 0
    for series in observed.get('series', []):
        rows = series['observations']
        invalid_values += sum(not isinstance(row['value'], (int, float)) or isinstance(row['value'], bool)
                              or not math.isfinite(row['value']) for row in rows)
        last = max((row['date'] for row in rows), default=None)
        try:
            reference = date.fromisoformat(last) if last else None
            age = (as_of - reference).days if reference else None
            status = 'reference_in_future' if age is not None and age < 0 else ('available' if reference else 'missing')
        except ValueError:
            age = None
            status = 'invalid_reference_date'
        series_quality.append({'id': series['id'], 'frequency': series['frequency'],
                               'observations': len(rows), 'last_reference_date': last,
                               'days_since_reference_date': age, 'status': status})
    outcomes = [v for p in result['profiles'] for v in p['outcomes'].values()]
    quality = {'snapshot_age_days': (as_of - collected_date).days if collected_date else None,
               'snapshot_collected_at': collected, 'series': series_quality,
               'observed_series': len(series_quality), 'historical_series': len(history.get('series', [])),
               'observed_source_errors': len(observed.get('errors', [])),
               'historical_source_errors': len(history.get('errors', [])),
               'invalid_observed_values': invalid_values,
               'unknown_policy_outcomes': sum(v is None for v in outcomes),
               'non_null_policy_outcomes': sum(v is not None for v in outcomes),
               'warning': 'Idade desde a data de referência original, não atraso de publicação. Série mensal pode usar dia 1; frequências e calendários de publicação diferem. Quantidade de dados não mede validade causal.'}
    macro = macro_diagnostics(result)
    ranking = ranking_diagnostics(result['experimental_ranking']) if result.get('experimental_ranking') else None
    indicators = [
        {'id': 'mc_standard_error', 'label': 'Erro-padrão Monte Carlo da média', 'value': macro['mc_se_pp_gdp'], 'unit': 'p.p. PIB'},
        {'id': 'mc_normal_half_width', 'label': 'Meia largura normal aproximada 95% — só erro numérico', 'value': macro['mc_approx_95_half_width_pp_gdp'], 'unit': 'p.p. PIB'},
        {'id': 'snapshot_age', 'label': 'Idade do snapshot coletado', 'value': quality['snapshot_age_days'], 'unit': 'dias'},
        {'id': 'observed_source_errors', 'label': 'Erros na coleta observada', 'value': quality['observed_source_errors'], 'unit': 'fontes'},
        {'id': 'historical_source_errors', 'label': 'Erros na coleta histórica', 'value': quality['historical_source_errors'], 'unit': 'fontes'},
        {'id': 'invalid_values', 'label': 'Valores observados inválidos', 'value': invalid_values, 'unit': 'observações'},
        {'id': 'unknown_policy_outcomes', 'label': 'Resultados políticos ainda desconhecidos', 'value': quality['unknown_policy_outcomes'], 'unit': 'campos'},
    ]
    if ranking:
        indicators += [
            {'id': 'method_variants', 'label': 'Testes de retirada de eixo ou critério', 'value': len(ranking['variants']), 'unit': 'variantes'},
            {'id': 'leader_set_changes', 'label': 'Variantes que alteram o conjunto líder', 'value': ranking['leader_set_changes'], 'unit': 'variantes'},
        ]
    return {'schema_version': 1, 'as_of': as_of.isoformat(),
            'source_run_id': result['run_id'], 'source_analysis_id': result.get('analysis_id'),
            'classification': 'diagnostics_not_forecast_accuracy', 'macro': macro, 'ranking': ranking,
            'data_quality': quality, 'indicators': indicators,
            'validation': {'government_forecast_validated': False,
                           'backtest_status': 'not_available', 'causal_calibration_status': 'not_identified',
                           'warning': 'Este diagnóstico não inclui backtest de previsões contra governos reais. Estabilidade numérica e documental não validam hipóteses nem reduzem automaticamente erro de previsão.'}}
