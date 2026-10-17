"""Bootstrap conjunto de blocos históricos, sem efeitos causais de candidaturas."""
import numpy as np
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
from .engine import describe, digest
from .empirical_data import DRIVERS, validate_snapshot

METRICS = [
    {'id': 'debt', 'label': 'Dívida bruta', 'unit': '% PIB'},
    {'id': 'unemployment', 'label': 'Desocupação — trimestre móvel', 'unit': '%'},
    {'id': 'activity', 'label': 'IBC-Br com ajuste sazonal', 'unit': 'índice'},
    {'id': 'prices', 'label': 'Preços acumulados (início = 100)', 'unit': 'índice'},
]


def prepare_history(snapshot):
    validate_snapshot(snapshot)
    by_id = {s['id']: {r['period']: r['value'] for r in s['observations']} for s in snapshot['series']}
    periods = sorted(set.intersection(*(set(by_id[key]) for key, *_ in DRIVERS)))
    if len(periods) < 25:
        raise ValueError('Histórico comum exige ao menos 25 meses')
    ordinals = [int(p[:4]) * 12 + int(p[5:]) for p in periods]
    if any(b - a != 1 for a, b in zip(ordinals, ordinals[1:])):
        raise ValueError('Lacuna mensal no histórico comum; não interpolar silenciosamente')
    raw = np.array([[by_id[key][p] for key, *_ in DRIVERS] for p in periods], dtype=float)
    if not np.isfinite(raw).all() or np.any(raw[:, [0, 2]] <= 0) or np.any((raw[:, 1] <= 0) | (raw[:, 1] >= 100)) or np.any(raw[:, 3] <= -100):
        raise ValueError('Unidade ou domínio físico inválido para as transformações')
    transformed = np.column_stack((np.log(raw[:, 0]), np.log(raw[:, 1] / (100 - raw[:, 1])),
                                   np.log(raw[:, 2]), np.log1p(raw[:, 3] / 100).cumsum()))
    return {'periods': periods, 'raw': raw, 'changes': np.diff(transformed, axis=0),
            'initial': np.array([raw[-1, 0], raw[-1, 1], raw[-1, 2], 100.0])}


def annual_blocks(changes, length=12):
    changes = np.asarray(changes, dtype=float)
    if changes.ndim != 2 or changes.shape[1] != 4 or len(changes) < length or not np.isfinite(changes).all():
        raise ValueError('Mudanças mensais insuficientes ou inválidas')
    cumulative = np.vstack((np.zeros(4), np.cumsum(changes, axis=0)))
    return cumulative[length:] - cumulative[:-length]


def project(initial, blocks, indices):
    initial = np.asarray(initial, dtype=float)
    indices = np.asarray(indices)
    if indices.ndim != 2 or indices.dtype.kind not in 'iu' or indices.min() < 0 or indices.max() >= len(blocks):
        raise ValueError('Índices de blocos inválidos')
    cumulative = np.asarray(blocks)[indices].cumsum(axis=1)
    paths = np.empty((len(indices), indices.shape[1]+1, 4))
    paths[:, 0] = initial
    paths[:, 1:, 0] = initial[0] * np.exp(cumulative[:, :, 0])
    odds = np.log(initial[1] / (100-initial[1])) + cumulative[:, :, 1]
    paths[:, 1:, 1] = 100 / (1 + np.exp(-odds))
    paths[:, 1:, 2] = initial[2] * np.exp(cumulative[:, :, 2])
    paths[:, 1:, 3] = initial[3] * np.exp(cumulative[:, :, 3])
    if not np.isfinite(paths).all():
        raise ValueError('Projeção não finita; execução interrompida')
    return paths


def run_empirical(snapshot, output, runs=1_000_000, seed=20261015, batch_size=10_000):
    if isinstance(runs, bool) or not isinstance(runs, int) or not 2 <= runs <= 10_000_000:
        raise ValueError('runs deve ser inteiro entre 2 e 10000000')
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError('seed deve ser inteiro não negativo')
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or not 1 <= batch_size <= 100_000:
        raise ValueError('batch_size deve ser inteiro entre 1 e 100000')
    prepared = prepare_history(snapshot)
    blocks = annual_blocks(prepared['changes'])
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    if (output/'paths.npy').exists():
        raise ValueError('Destino já contém trajetórias; use nova pasta para preservar resultados')
    (output/'calibration_snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    paths = np.lib.format.open_memmap(output/'paths.npy', mode='w+', dtype=np.float64, shape=(runs, 5, 4))
    selections = np.lib.format.open_memmap(output/'block_indices.npy', mode='w+', dtype=np.int32, shape=(runs, 4))
    rng = np.random.Generator(np.random.PCG64(seed))
    for offset in range(0, runs, batch_size):
        n = min(batch_size, runs-offset)
        indices = rng.integers(0, len(blocks), size=(n, 4), dtype=np.int32)
        paths[offset:offset+n] = project(prepared['initial'], blocks, indices)
        selections[offset:offset+n] = indices
        paths.flush()
        selections.flush()
        (output/'progress.json').write_text(json.dumps({'completed_paths': offset+n, 'requested_paths': runs,
                                                       'status': 'complete' if offset+n == runs else 'running'})+'\n')
    summary = {}
    annual = []
    for j, metric in enumerate(METRICS):
        end = np.asarray(paths[:, -1, j])
        changes = end - paths[:, 0, j]
        summary[metric['id']] = dict(metric, final=describe(end), change=describe(changes),
                                     numerical_mc_se=float(end.std(ddof=1) / np.sqrt(runs)))
    for year in range(5):
        annual.append({'year': year, 'metrics': {m['id']: describe(paths[:, year, j]) for j, m in enumerate(METRICS)}})
    with np.errstate(divide='ignore', invalid='ignore'):
        correlations = np.corrcoef(prepared['changes'].T)
    # Constantes não têm correlação definida; preservar null, nunca fabricar zero.
    correlation_rows = [[float(x) if np.isfinite(x) else None for x in row] for row in correlations]
    params = {'runs': runs, 'seed': seed, 'horizon_years': 4, 'block_months': 12,
              'snapshot_sha256': digest(snapshot), 'model_version': 'joint-moving-block-v2-audited-counts'}
    distinct_sequences = len(np.unique(selections, axis=0))
    result = {'schema_version': 2, 'kind': 'historically_calibrated_joint_bootstrap_not_government_forecast',
              'run_id': digest(params), 'parameters': params,
              'counts': {'sampled_paths': runs, 'distinct_block_sequences': distinct_sequences,
                         'repeated_block_sequences': runs-distinct_sequences, 'sampled_annual_blocks': runs*4,
                         'historical_months': len(prepared['periods']), 'available_annual_blocks': len(blocks)},
              'initial_reference': prepared['periods'][-1], 'history_start': prepared['periods'][0],
              'summary': summary, 'annual': annual, 'historical_change_correlation': correlation_rows,
              'metric_order': [m['id'] for m in METRICS], 'government_ranking': None,
              'candidate_effects_identified': False, 'created_at': datetime.now(timezone.utc).isoformat(),
              'artifacts': {'paths': 'paths.npy', 'block_indices': 'block_indices.npy'},
              'limitations': [
                  'Reamostragem de blocos históricos conjuntos de 12 meses, com reposição; preserva relações dentro de cada bloco, não entre blocos.',
                  'Supõe transferibilidade do passado e dinâmica estacionária nas transformações. Crises históricas podem reaparecer com frequência artificial.',
                  'Dívida projetada por variação histórica logarítmica, não pela identidade juros/PIB/primário. Não inferir taxas efetivas ou custos de programas.',
                  'Desocupação usa logit, atividade e dívida usam log, IPCA mensal compõe índice de preços. IBC-Br não é PIB; projeção não cobre renda ou mortalidade.',
                  'Um milhão de trajetórias não equivale a um milhão de observações ou estudos independentes. Quantis são condicionais ao bootstrap, não confiança em governos.',
                  'Não estima efeitos por candidato e não utiliza ranking documental como parâmetro macroeconômico.'
              ]}
    for filename in result['artifacts'].values():
        with (output/filename).open('rb') as file:
            result.setdefault('artifact_sha256', {})[filename] = hashlib.file_digest(file, 'sha256').hexdigest()
    (output/'empirical_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    return result


def rolling_backtest(snapshot, min_training_months=60, draws=2000, seed=20261015):
    prepared = prepare_history(snapshot)
    if min_training_months < 24 or draws < 2:
        raise ValueError('Backtest exige treino >=24 meses e >=2 trajetórias')
    raw, changes = prepared['raw'], prepared['changes']
    origins = []
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, 117])))
    # Cortes anuais evitam alvos sobrepostos de 12 meses.
    for end in range(min_training_months-1, len(raw)-12, 12):
        blocks = annual_blocks(changes[:end])
        initial = np.array([raw[end, 0], raw[end, 1], raw[end, 2], 100.0])
        paths = project(initial, blocks, rng.integers(0, len(blocks), size=(draws, 1), dtype=np.int32))
        final = paths[:, -1]
        actual = raw[end+12].copy()
        actual[3] = 100 * np.prod(1 + raw[end+1:end+13, 3]/100)
        median = np.median(final, axis=0)
        low, high = np.quantile(final, [.025, .975], axis=0)
        origins.append({'last_training_month': prepared['periods'][end],
                        'training_block_last_end': prepared['periods'][end],
                        'target_month': prepared['periods'][end+12], 'training_months': end+1,
                        'metrics': {m['id']: {'actual': float(actual[j]), 'bootstrap_median': float(median[j]),
                                             'baseline_no_change': float(initial[j]),
                                             'q025': float(low[j]), 'q975': float(high[j]),
                                             'covered_95': bool(low[j]-1e-10 <= actual[j] <= high[j]+1e-10)}
                                    for j, m in enumerate(METRICS)}})
    by_metric = {}
    for metric in METRICS:
        rows = [o['metrics'][metric['id']] for o in origins]
        if not rows:
            by_metric[metric['id']] = {'status': 'insufficient_history'}
            continue
        error = np.array([r['bootstrap_median']-r['actual'] for r in rows])
        baseline = np.array([r['baseline_no_change']-r['actual'] for r in rows])
        mae, baseline_mae = float(np.abs(error).mean()), float(np.abs(baseline).mean())
        by_metric[metric['id']] = {'status': 'evaluated', 'unit': metric['unit'],
                                  'bootstrap_mae': mae, 'bootstrap_rmse': float(np.sqrt((error**2).mean())),
                                  'bootstrap_bias': float(error.mean()), 'baseline_mae': baseline_mae,
                                  'mae_skill_vs_no_change': 1-mae/baseline_mae if baseline_mae > 0 else None,
                                  'coverage_95_pct': sum(r['covered_95'] for r in rows)/len(rows)*100,
                                  'mean_interval_width': float(np.mean([r['q975']-r['q025'] for r in rows]))}
    return {'classification': 'historical_pseudo_out_of_sample_diagnostic',
            'vintage_policy': 'latest_revised_data_pseudo_out_of_sample_not_real_time',
            'counts': {'origins': len(origins), 'paths_per_origin': draws},
            'origins': origins, 'by_metric': by_metric, 'government_forecast_validated': False,
            'warning': 'Treina apenas com períodos anteriores ao alvo, mas usa a edição revisada atual das séries: não é validação em tempo real. Backtest de 12 meses, não valida automaticamente horizonte de 4 anos. Poucos cortes anuais e quebras estruturais limitam as conclusões. Skill negativo indica pior MAE que repetir o nível inicial; cobertura larga não prova utilidade.'}
