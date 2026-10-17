"""Diagnósticos analíticos reproduzíveis: observado, derivado e simulado separados."""
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import numpy as np

from .empirical import prepare_history, annual_blocks, project, METRICS
from .engine import describe, digest
from .public_validation import validate_dataset


WARNING = ('Estatísticas descritivas e bootstrap não identificam efeito de candidato. '
           'Dados revisados atuais; backtest pseudo-fora-da-amostra, não validação em tempo real. '
           'Cortes não se sobrepõem dentro de cada horizonte, mas horizontes compartilham dados. '
           'Poucos cortes não comprovam precisão; não há seleção de vencedor ou ajuste retrospectivo de modelo.')


def summarize_observations(rows, unit):
    ordered = sorted(rows, key=lambda r: r['period'])
    if len({r['period'] for r in ordered}) != len(ordered):
        raise ValueError('Período duplicado no mesmo indicador/território/classificação')
    valid = [r for r in ordered if r['value'] is not None]
    if any(isinstance(r['value'], bool) or not isinstance(r['value'], (int, float)) or not math.isfinite(r['value']) for r in valid):
        raise ValueError('Valor observado não numérico/finito')
    values = np.array([r['value'] for r in valid], dtype=float)
    by_period = {r['period']: r for r in ordered}
    comparisons = []
    for row in valid:
        period = row['period']
        previous_period = str(int(period[:4])-1)+period[4:]
        previous = by_period.get(previous_period)
        if not unit or previous is None or previous['value'] is None:
            continue
        old, new = previous['value'], row['value']
        comparisons.append({'period': period, 'previous_period': previous_period,
            'value': new, 'previous_value': old, 'difference': new-old,
            'unit': 'p.p.' if unit.strip().startswith('%') else unit,
            'relative_change_pct': (new/old-1)*100 if old > 0 else None,
            'denominator_policy': 'Variação relativa somente com denominador positivo; não é variação em p.p.',
            'source_row': row.get('source_row'), 'previous_source_row': previous.get('source_row')})
    return {'rows': len(rows), 'valid_count': len(valid), 'missing_count': len(rows)-len(valid),
            'missing_pct': (len(rows)-len(valid))/len(rows)*100 if rows else None,
            'zero_count': sum(r['value'] == 0 for r in valid), 'unit': unit,
            'first_period': ordered[0]['period'] if ordered else None,
            'last_period': ordered[-1]['period'] if ordered else None,
            'latest': ordered[-1] if ordered else None,
            'last_nonmissing': valid[-1] if valid else None,
            'distribution': describe(values) if len(values) > 1 else None,
            'comparisons': comparisons,
            'interpretation': 'Distribuição temporal descritiva, não amostras independentes nem efeito de governo; sem ajuste monetário por inflação.'}


def _wilson(successes, count):
    if count == 0:
        return None
    z = 1.959963984540054
    p = successes/count
    center = (p+z*z/(2*count))/(1+z*z/count)
    half = z*math.sqrt(p*(1-p)/count+z*z/(4*count*count))/(1+z*z/count)
    return [max(0.0, center-half)*100, min(1.0, center+half)*100]


def multi_horizon_backtest(snapshot, horizons=(12, 24, 48), min_training_months=60, draws=2000, seed=20261015):
    if type(draws) is not int or draws < 2 or type(min_training_months) is not int or min_training_months < 24:
        raise ValueError('Backtest exige >=2 sorteios e >=24 meses de treino')
    if type(seed) is not int or seed < 0 or any(type(h) is not int or h < 12 or h % 12 for h in horizons):
        raise ValueError('Seed/horizonte inválido; horizontes devem ser múltiplos positivos de 12')
    prepared = prepare_history(snapshot)
    raw, changes = prepared['raw'], prepared['changes']
    reports = {}
    for horizon in horizons:
        rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, 2026, horizon])))
        origins = []
        for end in range(min_training_months-1, len(raw)-horizon, horizon):
            training = annual_blocks(changes[:end])
            initial = np.array([*raw[end, :3], 100.0])
            selections = rng.integers(0, len(training), size=(draws, horizon//12), dtype=np.int32)
            simulations = project(initial, training, selections)[:, -1]
            actual = np.array([*raw[end+horizon, :3], 100*np.prod(1+raw[end+1:end+horizon+1, 3]/100)])
            # Baseline adicional de drift: só média das transformações do treino.
            drift = project(initial, np.mean(changes[:end], axis=0, keepdims=True)*horizon,
                            np.zeros((1, 1), dtype=np.int32))[0, -1]
            metrics = {}
            for j, metric in enumerate(METRICS):
                sample = simulations[:, j]
                sorted_sample = np.sort(sample)
                spread_term = np.sum((2*np.arange(1, draws+1)-draws-1)*sorted_sample)/(draws*draws)
                intervals = {}
                for nominal in [50, 80, 95]:
                    alpha = 1-nominal/100
                    lo, hi = np.quantile(sample, [alpha/2, 1-alpha/2])
                    score = hi-lo+(2/alpha)*(max(lo-actual[j], 0)+max(actual[j]-hi, 0))
                    intervals[str(nominal)] = {'lower': float(lo), 'upper': float(hi),
                        'covered': bool(lo <= actual[j] <= hi), 'width': float(hi-lo), 'interval_score': float(score)}
                metrics[metric['id']] = {'unit': metric['unit'], 'actual': float(actual[j]),
                    'initial': float(initial[j]), 'baseline': float(initial[j]), 'drift_baseline': float(drift[j]),
                    'predicted_mean': float(sample.mean()), 'predicted_median': float(np.median(sample)),
                    'crps': max(0.0, float(np.mean(np.abs(sample-actual[j]))-spread_term)), 'intervals': intervals}
            origins.append({'last_training_month': prepared['periods'][end],
                'training_block_last_end': prepared['periods'][end], 'training_block_count': len(training),
                'target_month': prepared['periods'][end+horizon], 'horizon_months': horizon, 'metrics': metrics})
        by_metric = {}
        for metric in METRICS:
            rows = [o['metrics'][metric['id']] for o in origins]
            if not rows:
                by_metric[metric['id']] = {'status': 'insufficient_history', 'unit': metric['unit']}
                continue
            y = np.array([r['actual'] for r in rows])
            pred = np.array([r['predicted_mean'] for r in rows])
            errors = pred-y
            naive_errors = np.array([r['baseline'] for r in rows])-y
            drift_errors = np.array([r['drift_baseline'] for r in rows])-y
            mae = float(np.abs(errors).mean())
            naive_mae = float(np.abs(naive_errors).mean())
            drift_mae = float(np.abs(drift_errors).mean())
            by_metric[metric['id']] = {'status': 'evaluated', 'unit': metric['unit'], 'origins': len(rows),
                'bootstrap_mae': mae, 'bootstrap_rmse': float(np.sqrt(np.mean(errors**2))),
                'bootstrap_bias': float(errors.mean()), 'median_absolute_error': float(np.median(np.abs(errors))),
                'maximum_absolute_error': float(np.abs(errors).max()), 'baseline_mae': naive_mae,
                'drift_baseline_mae': drift_mae, 'skill_vs_no_change': 1-mae/naive_mae if naive_mae > 0 else None,
                'skill_vs_drift': 1-mae/drift_mae if drift_mae > 0 else None,
                'mean_crps': float(np.mean([r['crps'] for r in rows])),
                'directional_accuracy_pct': float(np.mean(np.sign(pred-np.array([r['initial'] for r in rows])) == np.sign(y-np.array([r['initial'] for r in rows])))*100),
                'intervals': {str(n): {'coverage_pct': sum(r['intervals'][str(n)]['covered'] for r in rows)/len(rows)*100,
                    'coverage_wilson_95_pct': _wilson(sum(r['intervals'][str(n)]['covered'] for r in rows), len(rows)),
                    'mean_width': float(np.mean([r['intervals'][str(n)]['width'] for r in rows])),
                    'mean_interval_score': float(np.mean([r['intervals'][str(n)]['interval_score'] for r in rows]))} for n in [50, 80, 95]}}
        reports[str(horizon)] = {'status': 'evaluated' if origins else 'insufficient_history',
            'counts': {'origins': len(origins), 'paths_per_origin': draws}, 'origins': origins, 'by_metric': by_metric}
    return {'schema_version': 1, 'horizons': reports, 'seed': seed, 'min_training_months': min_training_months,
            'snapshot_sha256': digest(snapshot), 'government_forecast_validated': False, 'warning': WARNING,
            'selection_policy': 'fixed_model_all_prespecified_horizons_and_baselines_no_winner_selection',
            'score_definitions': {'crps': 'E|X-y| - E|X-Xprime|/2; medida na unidade do indicador; menor é melhor.',
                'interval_score': 'largura + 2/alpha vezes distância fora do intervalo; menor é melhor.',
                'wilson': 'Faixa binomial descritiva aproximada para cobertura em poucos cortes, não confiança em candidatos.'}}


def simulated_metrics(paths):
    rows = []
    for year in range(1, paths.shape[1]):
        before, current = paths[:, 0], paths[:, year]
        measures = [
            ('debt_change_pp', 'Mudança da dívida desde o início', 'p.p. PIB', current[:, 0]-before[:, 0]),
            ('unemployment_change_pp', 'Mudança da desocupação desde o início', 'p.p.', current[:, 1]-before[:, 1]),
            ('activity_growth_pct', 'Variação acumulada do IBC-Br, não PIB', '%', (current[:, 2]/before[:, 2]-1)*100),
            ('activity_annualized_pct', 'Variação anualizada do IBC-Br, não PIB', '% a.a.', ((current[:, 2]/before[:, 2])**(1/year)-1)*100),
            ('cumulative_inflation_pct', 'Inflação acumulada', '%', (current[:, 3]/before[:, 3]-1)*100),
            ('annualized_inflation_pct', 'Inflação anualizada', '% a.a.', ((current[:, 3]/before[:, 3])**(1/year)-1)*100),
            ('purchasing_power_change_pct', 'Mudança do poder de compra de quantia nominal fixa', '%', (before[:, 3]/current[:, 3]-1)*100),
            ('debt_annual_change_pp', 'Mudança da dívida no último ano', 'p.p. PIB', current[:, 0]-paths[:, year-1, 0]),
            ('unemployment_annual_change_pp', 'Mudança da desocupação no último ano', 'p.p.', current[:, 1]-paths[:, year-1, 1]),
            ('debt_peak_change_pp', 'Pico anual da dívida acima do início', 'p.p. PIB', paths[:, :year+1, 0].max(axis=1)-before[:, 0]),
            ('unemployment_peak_change_pp', 'Pico anual da desocupação acima do início', 'p.p.', paths[:, :year+1, 1].max(axis=1)-before[:, 1]),
            ('activity_max_drawdown_pct', 'Maior drawdown do IBC-Br nos pontos anuais', '%', np.min(paths[:, :year+1, 2]/np.maximum.accumulate(paths[:, :year+1, 2], axis=1)-1, axis=1)*100)
        ]
        for key, label, unit, values in measures:
            q05, q95 = np.quantile(values, [.05, .95])
            rows.append({'id': f'year_{year}_{key}', 'year': year, 'label': label, 'unit': unit,
                'classification': 'simulated_not_government_effect', 'summary': describe(values),
                'lower_tail_mean_5pct': float(values[values <= q05].mean()),
                'upper_tail_mean_5pct': float(values[values >= q95].mean()),
                'positive_frequency_pct': float(np.mean(values > 0)*100),
                'negative_frequency_pct': float(np.mean(values < 0)*100),
                'zero_frequency_pct': float(np.mean(values == 0)*100),
                'note': 'Frequências condicionais ao bootstrap; picos/drawdowns só nos pontos anuais, não intramês; não é renda real das famílias.'})
    return rows


def observation_key(dataset, row):
    # Só o sufixo de consulta territorial IBGE é descartado. IDs WB como
    # wb-NY.GDP.PCAP.KD devem permanecer literais e completos.
    identity = dataset['id'].split('-N', 1)[0] if dataset['provider'] == 'IBGE' else dataset['id']
    return digest([dataset['provider'], identity, row['entity_id'], row.get('classifications', []), row['period']])


def build_analysis(root, output, simulation_dir, catalog_file='research/public_catalog.json'):
    root, output = Path(root), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    catalog = json.loads((root/catalog_file).read_text())
    groups, dataset_quality, canonical_cells = [], [], defaultdict(list)
    for dataset in catalog['datasets']:
        validate_dataset(root, dataset)
        if dataset['provider'] == 'Tesouro/Siconfi':
            for i, row in enumerate(dataset['observations']):
                key = digest(['siconfi', row['cod_ibge'], row['exercicio'], row['periodo'], row['cod_conta'], row['coluna']])
                canonical_cells[key].append({'dataset': dataset['id'], 'row': i, 'value': row['valor']})
            dataset_quality.append({'id': dataset['id'], 'provider': dataset['provider'], 'rows': len(dataset['observations']),
                'raw_sha256': dataset['sha256'], 'value_and_completeness_verified_against_raw': True,
                'numeric_aggregation': 'disabled_accounts_and_columns_are_not_additive_by_default'})
            continue
        grouped = defaultdict(list)
        for i, row in enumerate(dataset['observations']):
            key = digest({'entity': row['entity_id'], 'classifications': row.get('classifications', [])})
            grouped[key].append(dict(row, source_row=i))
            cell = observation_key(dataset, row)
            canonical_cells[cell].append({'dataset': dataset['id'], 'row': i, 'value': row['value']})
        dataset_quality.append({'id': dataset['id'], 'provider': dataset['provider'], 'rows': len(dataset['observations']),
            'groups': len(grouped), 'raw_sha256': dataset['sha256'], 'metadata_sha256': dataset['metadata']['sha256'],
            'value_and_completeness_verified_against_raw': True, 'unit_structured': bool(dataset.get('unit')),
            'entities': sorted({r['entity_id'] for r in dataset['observations']}),
            'suppressed_or_missing': sum(r['value'] is None for r in dataset['observations'])})
        for key, rows in sorted(grouped.items()):
            groups.append({'id': dataset['id']+':'+key, 'dataset_id': dataset['id'], 'label': dataset['label'],
                'entity_id': rows[0]['entity_id'], 'entity': rows[0]['entity'],
                'classifications': rows[0].get('classifications', []), 'frequency': dataset.get('frequency', 'anual'),
                'source': {'url': dataset['url'], 'response_path': dataset['response_path'], 'sha256': dataset['sha256']},
                **summarize_observations(rows, dataset.get('unit'))})
    # Detecta repetição entre relatórios expandidos e catálogo sem somar as contas.
    expanded = root/'research/expanded_evidence.json'
    if expanded.exists():
        from .public_validation import validate_embedded_fiscal
        for report in json.loads(expanded.read_text())['fiscal_reports']:
            validate_embedded_fiscal(report)
            for i, row in enumerate(report['items']):
                key = digest(['siconfi', row['cod_ibge'], row['exercicio'], row['periodo'], row['cod_conta'], row['coluna']])
                canonical_cells[key].append({'dataset': 'expanded:'+str(report['entity'])+':'+str(report['year']), 'row': i, 'value': row['valor']})
    conflicts = [{'cell': k, 'copies': v} for k, v in canonical_cells.items() if len({json.dumps(r['value']) for r in v}) > 1]
    duplicates = [{'cell': k, 'copies': v} for k, v in canonical_cells.items() if len(v) > 1]
    sim_dir = root/simulation_dir
    snapshot = json.loads((sim_dir/'calibration_snapshot.json').read_text())
    paths = np.load(sim_dir/'paths.npy', mmap_mode='r')
    result = json.loads((sim_dir/'empirical_results.json').read_text())
    if digest(snapshot) != result['parameters']['snapshot_sha256'] or digest(result['parameters']) != result['run_id']:
        raise ValueError('Identidade da calibração/simulação não confere')
    if paths.shape != (result['parameters']['runs'], 5, 4) or result['government_ranking'] is not None or result['candidate_effects_identified']:
        raise ValueError('Forma ou classificação da simulação incompatível')
    with (sim_dir/'paths.npy').open('rb') as file:
        if hashlib.file_digest(file, 'sha256').hexdigest() != result['artifact_sha256']['paths.npy']:
            raise ValueError('Trajetórias alteradas: análise interrompida')
    for j, metric in enumerate(METRICS):
        if describe(paths[:, -1, j]) != result['summary'][metric['id']]['final']:
            raise ValueError('Resumo final diverge das trajetórias')
    historical = []
    for series in snapshot['series']:
        historical.append({'id': series['id'], 'label': series['label'],
                           **summarize_observations(series['observations'], series['unit'])})
    metrics = simulated_metrics(paths)
    backtests = multi_horizon_backtest(snapshot, seed=result['parameters']['seed'])
    report = {'schema_version': 1, 'warning': WARNING, 'government_ranking': None,
        'catalog_file': catalog_file,
        'code_sha256': {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
                       ['src/analysis_suite.py', 'src/public_validation.py', 'src/empirical.py', 'src/empirical_data.py']},
        'simulation_run_id': result['run_id'], 'calibration_sha256': digest(snapshot),
        'dataset_quality': dataset_quality, 'series_groups': groups, 'historical_drivers': historical,
        'simulated_metrics': metrics, 'multi_horizon_backtest': backtests,
        'duplicates': duplicates, 'conflicts': conflicts, 'collection_errors': catalog['errors'],
        'counts': {'validated_datasets': len(dataset_quality), 'series_groups': len(groups),
            'same_period_yoy_comparisons': sum(len(g['comparisons']) for g in groups),
            'derived_simulated_metric_distributions': len(metrics), 'duplicate_cells': len(duplicates),
            'conflicting_cells': len(conflicts)},
        'policy': {'rank_candidates': False, 'impute_missing': False, 'sum_fiscal_accounts': False,
            'missing_units': 'Preservar desconhecido; sem variação em unidade inventada.',
            'conflicts': 'Preservados e sinalizados, nunca escolher valor por candidato.',
            'duplicate_counts': 'Cópias não são evidências independentes; diagnóstico não remove snapshots.',
            'yoy': 'Mesmo código de período do ano anterior; nunca substituir por linha anterior.'}}
    (output/'analysis.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    with (output/'observed_comparisons.csv').open('w', newline='') as file:
        fields = ['dataset_id', 'entity_id', 'group_id', 'period', 'previous_period', 'value', 'previous_value', 'difference', 'unit', 'relative_change_pct', 'source_sha256', 'source_row', 'previous_source_row']
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for group in groups:
            for row in group['comparisons']:
                writer.writerow({k: v for k, v in dict(row, dataset_id=group['dataset_id'], entity_id=group['entity_id'], group_id=group['id'], source_sha256=group['source']['sha256']).items() if k in fields})
    with (output/'simulated_metrics.csv').open('w', newline='') as file:
        fields = ['id', 'year', 'label', 'unit', 'n', 'mean', 'median', 'std', 'q025', 'q975', 'min', 'max',
                  'lower_tail_mean_5pct', 'upper_tail_mean_5pct', 'positive_frequency_pct', 'negative_frequency_pct', 'zero_frequency_pct']
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for metric in metrics:
            writer.writerow({k: v for k, v in dict(metric, **metric['summary']).items() if k in fields})
    with (output/'backtest_scores.csv').open('w', newline='') as file:
        fields = ['horizon_months', 'metric', 'unit', 'origins', 'bootstrap_mae', 'bootstrap_rmse', 'bootstrap_bias',
                  'baseline_mae', 'drift_baseline_mae', 'skill_vs_no_change', 'skill_vs_drift', 'mean_crps',
                  'coverage_50_pct', 'coverage_80_pct', 'coverage_95_pct', 'status']
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for horizon, backtest in backtests['horizons'].items():
            for key, score in backtest['by_metric'].items():
                row = dict(score, horizon_months=horizon, metric=key)
                for nominal in [50, 80, 95]:
                    row[f'coverage_{nominal}_pct'] = score.get('intervals', {}).get(str(nominal), {}).get('coverage_pct')
                writer.writerow({k: v for k, v in row.items() if k in fields})
    lines = ['# Análise ampliada — fatos, derivações e incerteza', '', WARNING, '',
             '## Cobertura e integridade', '', json.dumps(report['counts'], ensure_ascii=False), '',
             'Cópias repetidas não são evidência independente. Ausência de unidade impede cálculo de variação em unidade inventada. Não somamos contas fiscais de naturezas/colunas diferentes.', '',
             '## Backtest: não ocultar desempenho inferior às baselines', '',
             '| Horizonte (meses) | Cortes | Indicador | MAE bootstrap | MAE sem mudança | MAE drift | Skill sem mudança |',
             '|---|---:|---|---:|---:|---:|---:|']
    for horizon, backtest in backtests['horizons'].items():
        for key, score in backtest['by_metric'].items():
            if score['status'] == 'evaluated':
                skill = score['skill_vs_no_change']
                skill_text = f'{skill:.4f}' if skill is not None else 'indefinido (baseline sem erro)'
                lines.append(f"| {horizon} | {score['origins']} | {key} ({score['unit']}) | {score['bootstrap_mae']:.4f} | {score['baseline_mae']:.4f} | {score['drift_baseline_mae']:.4f} | {skill_text} |")
    lines += ['', 'Skill negativo significa erro MAIOR que o baseline. Dois cortes de quatro anos não validam previsão governamental. CRPS, interval score, faixas de cobertura e origens completas estão no JSON.', '',
              '## Arquivos para auditoria', '',
              '- analysis.json: definições, qualidade por dataset, grupos/territórios/classificações, duplicatas/conflitos, proveniência e backtests completos.',
              '- observed_comparisons.csv: comparação com mesmo período do ano anterior, com linha/hash de origem.',
              '- simulated_metrics.csv: distribuições derivadas das trajetórias; não são fatos futuros.',
              '- backtest_scores.csv: métricas de erro por horizonte e unidade; não são somadas em nota.', '',
              '## Lacunas da coleta', '', json.dumps(catalog['errors'], ensure_ascii=False, indent=2), '',
              'Entrevistas e debates externos não foram integralmente transcritos/checados nesta rodada. Nenhum canal conceitual virou coeficiente causal.']
    (output/'RELATORIO.md').write_text('\n'.join(lines)+'\n')
    return report
