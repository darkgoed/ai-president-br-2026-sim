"""Identidades contábeis, não um modelo causal de governos."""

from pathlib import Path
import hashlib
import json
import platform
import numpy as np
from .metrics import fiscal_metrics

ROOT = Path(__file__).resolve().parents[1]


def load_inputs(root=ROOT):
    return (json.loads((root / 'data/model.json').read_text()),
            json.loads((root / 'data/strategies.json').read_text()))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False).encode()).hexdigest()

def debt_step(debt, interest, nominal_growth, primary):
    """Frações do PIB; superávit positivo. Sem stock-flow adjustments."""
    return ((1 + interest) / (1 + nominal_growth)) * debt - primary


def describe(values):
    """Quantis da distribuição de stress, não IC de previsão de governo."""
    values = np.asarray(values, dtype=float)
    return {'n': len(values), 'mean': float(values.mean()),
            'median': float(np.median(values)), 'std': float(values.std(ddof=1)),
            'q025': float(np.quantile(values, 0.025)),
            'q975': float(np.quantile(values, 0.975)),
            'min': float(values.min()), 'max': float(values.max())}


def simulate(config, profiles, runs=100_000, seed=20261015, scenario='all',
             shifts=None, uncertainty_scale=1.0, initial_debt=None, weights=None):
    """Um benchmark compartilhado; efeitos políticos desconhecidos continuam null.

    Há N trajetórias únicas e N*K avaliações documentais, não N*K mundos
    independentes. Nomes, partidos e votos nunca entram nas equações.
    """
    if isinstance(runs, bool) or not isinstance(runs, int) or not 2 <= runs <= 200000:
        raise ValueError('runs must be an integer in [2, 200000]')
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError('seed must be a nonnegative integer')
    if not np.isfinite(uncertainty_scale) or not 0 < uncertainty_scale <= 2:
        raise ValueError('uncertainty_scale must be in (0, 2]')
    if scenario != 'all' and scenario not in config['scenarios']:
        raise ValueError('unknown scenario')
    if len({p['id'] for p in profiles}) != len(profiles) or not profiles:
        raise ValueError('profiles must have unique identifiers')
    # No extension can smuggle in unsupported causal parameters.
    if any(axis['policy_effect'] is not None for p in profiles for axis in p['axes'].values()):
        raise ValueError('non-null political effect lacks an identified causal model')
    if weights is not None and (not weights or any(not np.isfinite(v) or v < 0 for v in weights.values())
                                or sum(weights.values()) <= 0):
        raise ValueError('weights must be finite, nonnegative and nonzero')
    years = config['horizon_years']
    if isinstance(years, bool) or not isinstance(years, int) or not 1 <= years <= 100:
        raise ValueError('horizon_years must be an integer in [1, 100]')
    for key in ('interest', 'growth', 'primary'):
        bounds = config['bounds'][key]
        if len(bounds) != 2 or not all(np.isfinite(v) for v in bounds) or bounds[0] > bounds[1]:
            raise ValueError('invalid parameter bounds')
    keys = list(config['scenarios'])
    if not keys or any(len(v) != 3 or not all(np.isfinite(x) for x in v)
                       for v in config['scenarios'].values()):
        raise ValueError('scenario shifts must contain three finite values')
    rng = np.random.Generator(np.random.PCG64(seed))
    labels = np.arange(runs) % len(keys) if scenario == 'all' else np.full(runs, keys.index(scenario))
    rng.shuffle(labels)
    u = rng.random((runs, years, 3))
    draws = np.empty_like(u)
    offsets = shifts or {}
    if not set(offsets) <= {'interest', 'growth', 'primary'} or not all(np.isfinite(v) for v in offsets.values()):
        raise ValueError('unknown or non-finite parameter shift')
    for j, key in enumerate(('interest', 'growth', 'primary')):
        low, high = config['bounds'][key]
        draws[:, :, j] = (low + high) / 2 + (u[:, :, j] - .5) * (high - low) * uncertainty_scale
        draws[:, :, j] += np.array([config['scenarios'][keys[i]][j] for i in labels])[:, None]
        draws[:, :, j] += offsets.get(key, 0)
    start = config['initial_debt'] if initial_debt is None else initial_debt
    if not np.isfinite(start) or start < 0 or not np.isfinite(draws).all() or (draws[:, :, 1] <= -1).any():
        raise ValueError('invalid debt, rates or nominal GDP denominator')
    debt = np.empty((runs, years + 1))
    debt[:, 0] = start
    for year in range(years):
        debt[:, year + 1] = debt_step(debt[:, year], draws[:, year, 0],
                                        draws[:, year, 1], draws[:, year, 2])
    end = debt[:, -1] * 100
    hist, edges = np.histogram(end, bins=20)
    params = {'runs': runs, 'seed': seed, 'scenario': scenario, 'shifts': offsets,
              'uncertainty_scale': uncertainty_scale, 'initial_debt': start,
              'weights': weights, 'config_sha256': digest(config), 'profiles_sha256': digest(profiles)}
    rows = [{'scenario_id': i, 'family': keys[int(labels[i])],
             'debt_pct_gdp': debt[i].__mul__(100).tolist(),
             'interest_fraction': draws[i, :, 0].tolist(),
             'nominal_growth_fraction': draws[i, :, 1].tolist(),
             'primary_surplus_fraction_gdp': draws[i, :, 2].tolist()} for i in range(runs)]
    return {'schema_version': 1, 'kind': 'exploratory_common_reference_not_government_forecast',
            'run_id': digest(params), 'parameters': params,
            'runtime': {'python': platform.python_version(), 'numpy': np.__version__, 'rng': 'PCG64'},
            'counts': {'unique_reference_trajectories': runs,
                       'profile_scenario_evaluations': runs * len(profiles),
                       'identified_government_effects': 0},
            'candidate_comparison_identified': False, 'ranking': None,
            'weight_sensitivity': 'not_identified_missing_social_outcomes',
            'profiles': [{'id': p['id'], 'name': p['name'], 'party': p['party'],
                          'scenarios_assessed': runs, 'reference_run_id': digest(params),
                          'outcomes': {key: None for key in p['axes']}} for p in profiles],
            'reference': {'unit': 'percent_gdp', 'horizon_years': years,
                          'metrics': fiscal_metrics(debt, draws),
                          'summary': describe(end),
                          'by_scenario': {key: describe(end[labels == i]) for i, key in enumerate(keys)
                                          if (labels == i).sum() >= 2},
                          'scenario_counts': {key: int((labels == i).sum()) for i, key in enumerate(keys)
                                              if (labels == i).any()},
                          'histogram': {'counts': hist.tolist(), 'bin_edges': edges.tolist()},
                          'trajectories': rows},
            'limitations': ['Hipóteses de stress artificiais, não calibradas para prever o Brasil.',
                            'Efeitos políticos desconhecidos não equivalem a zero ou empate.',
                            'Sem resultados identificados de emprego, saúde, educação, segurança ou inflação.',
                            'Sem feedback macroeconômico, câmbio ou ajustes stock-flow.',
                            'Pesos de objetivos não permitem completar efeitos ausentes.']}
