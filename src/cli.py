"""CLI reproduzível: python -m src.cli --help."""
import argparse
import csv
import json
from pathlib import Path
from .engine import ROOT, load_inputs, simulate, digest
from .dashboard import dashboard
from .observed import fetch_snapshot, load_snapshot
from .ranking import analyze_programs, load_dossiers
from .history import summarize_history
from .diagnostics import build_diagnostics
from .empirical import run_empirical, rolling_backtest
from .empirical_dashboard import export_empirical
from .knowledge_build import build_registry


def report_text(result):
    counts = result['counts']
    summary = result['reference']['summary']
    lines = ['PRESIDENTE IA | BRASIL 2026',
             'BENCHMARK EXPLORATÓRIO — NÃO É PREVISÃO DE GOVERNO',
             f"Run: {result['run_id']}",
             f"Seed: {result['parameters']['seed']} | perfis: {len(result['profiles'])}",
             f"Trajetórias únicas executadas: {counts['unique_reference_trajectories']}",
             f"Avaliações perfil/cenário: {counts['profile_scenario_evaluations']}",
             f"Efeitos de governo identificados: {counts['identified_government_effects']}",
             'Dívida final da referência artificial (% PIB):',
             f"  média {summary['mean']:.4f} | mediana {summary['median']:.4f}",
             f"  desvio amostral {summary['std']:.4f}",
             f"  quantis 2,5–97,5%: [{summary['q025']:.4f}; {summary['q975']:.4f}]",
             'Famílias de stress:']
    for key, stats in result['reference']['by_scenario'].items():
        lines.append(f"  {key:16} n={stats['n']:5} média={stats['mean']:.4f}")
    for metric in result['reference'].get('metrics', {}).get('indicators', []):
        kind = 'OBSERVADO' if metric['classification'] == 'observed' else 'HIPÓTESE'
        lines.append(f"  {metric['label']}: {metric['value']:.4f} {metric['unit']} [{kind}]")
    if result.get('initial_debt_source'):
        lines.append(f"Dívida inicial: SGS 13762, referência {result['initial_debt_source']['date']}; demais parâmetros continuam hipotéticos.")
    if result.get('observed'):
        lines.append('DADOS OFICIAIS OBSERVADOS — não calibram automaticamente os cenários:')
        for series in result['observed']['series']:
            last = series['observations'][-1]
            lines.append(f"  {series['label']}: {last['value']} {series['unit']} | {last['date']} | SGS {series['sgs_id']}")
    if result.get('experimental_ranking'):
        ranking = result['experimental_ranking']
        lines += ['LEGADO DESCONTINUADO: seleção desigual e pesos editoriais; não usar como evidência de melhor governo.',
                  ranking['title'].upper(), ranking['interpretation'],
                  f"Análises de pesos: {ranking['counts']['weight_analyses']}; avaliações candidato/pesos: {ranking['counts']['candidate_weight_evaluations']}"]
        for row in ranking['candidates']:
            lines.append(f"  {row['position_equal_weights']:2}. {row['name']}: {row['score_equal_weights']:.2f}/100 | posições {row['best_rank']}–{row['worst_rank']} | primeiro lugar fracionado {row['first_place_fractional_pct']:.2f}% dos pesos")
        lines.extend('  ' + x for x in ranking['protocol']['limitations'])
    if result.get('diagnostics'):
        diagnostic = result['diagnostics']
        lines += ['FRAGILIDADE E ERRO NUMÉRICO — NÃO É CONFIANÇA EM GOVERNOS', diagnostic['macro']['warning']]
        for indicator in diagnostic['indicators']:
            value = 'não estimado' if indicator['value'] is None else indicator['value']
            lines.append(f"  {indicator['label']}: {value} {indicator['unit']}")
        lines.append(diagnostic['validation']['warning'])
    lines += ['Comparação causal entre candidaturas: NÃO IDENTIFICADA.',
              'Ranking de desempenho de governo: não calculado. Ranking documental experimental separado, quando solicitado.',
              'Pesos alternativos: não identificáveis sem resultados sociais.',
              'Limitações:'] + ['  ' + x for x in result['limitations']]
    return '\n'.join(lines) + '\n'


def export_result(result, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    text = report_text(result)
    (out / 'report.txt').write_text(text)
    (out / 'report.md').write_text('# Execução real\n\n```text\n'+text+'```\n')
    (out / 'dashboard.html').write_text(dashboard(result), encoding='utf-8')
    with (out / 'metrics.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['id', 'label', 'value', 'unit', 'definition', 'classification'], lineterminator='\n')
        writer.writeheader()
        writer.writerows(result['reference'].get('metrics', {}).get('indicators', []))
    with (out / 'observed.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['id', 'label', 'date', 'value', 'unit', 'sgs_id', 'source_url', 'classification'])
        for series in result.get('observed', {}).get('series', []):
            for row in series['observations']:
                writer.writerow([series['id'], series['label'], row['date'], row['value'], series['unit'], series['sgs_id'], series['url'], 'observed'])
    with (out / 'trajectories.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['scenario_id', 'family', 'year', 'debt_pct_gdp', 'interest_fraction', 'nominal_growth_fraction', 'primary_surplus_fraction_gdp'])
        for row in result['reference']['trajectories']:
            for year, value in enumerate(row['debt_pct_gdp']):
                writer.writerow([row['scenario_id'], row['family'], year, value,
                                 row['interest_fraction'][year-1] if year else '',
                                 row['nominal_growth_fraction'][year-1] if year else '',
                                 row['primary_surplus_fraction_gdp'][year-1] if year else ''])
    with (out / 'profiles.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['id', 'name', 'party', 'scenarios_assessed', 'political_effect', 'identification_status'])
        for row in result['profiles']:
            writer.writerow([row['id'], row['name'], row['party'], row['scenarios_assessed'], '', 'not_identified'])
    if result.get('experimental_ranking'):
        ranking = result['experimental_ranking']
        (out/'ranking.json').write_text(json.dumps(ranking, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        with (out/'ranking.csv').open('w', newline='') as f:
            fields = ['id', 'name', 'position_equal_weights', 'score_equal_weights', 'best_rank', 'worst_rank', 'mean_rank', 'first_place_fractional_pct']
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
            writer.writeheader()
            writer.writerows(ranking['candidates'])
        with (out/'ranking_indicators.csv').open('w', newline='') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow(['candidate_id', 'axis', 'criterion', 'detected_in_selection', 'evidence_ids', 'classification'])
            for candidate in ranking['candidates']:
                for indicator in candidate['indicators']:
                    writer.writerow([candidate['id'], indicator['axis'], indicator['criterion'],
                                     '' if indicator['detected'] is None else int(indicator['detected']),
                                     ';'.join(indicator['evidence_ids']), ranking['classification']])
    with (out/'history.csv').open('w', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['id', 'location', 'label', 'period', 'value', 'unit', 'source_url', 'classification'])
        for series in result.get('history', {}).get('series', []):
            for row in series['observations']:
                writer.writerow([series['id'], series['location'], series['label'], row['period'], row['value'], series['unit'], series['url'], 'historical_descriptive_not_causal'])
    if result.get('diagnostics'):
        diagnostic = result['diagnostics']
        (out/'diagnostics.json').write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
        with (out/'diagnostics.csv').open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['id', 'label', 'value', 'unit'], lineterminator='\n')
            writer.writeheader()
            writer.writerows(diagnostic['indicators'])


def sensitivity(config, profiles, runs, seed):
    base = simulate(config, profiles, runs=runs, seed=seed)
    variants = []
    for key in ['primary', 'interest', 'growth']:
        for delta in [-0.005, 0.005]:
            r = simulate(config, profiles, runs=runs, seed=seed, shifts={key: delta})
            variants.append({'parameter': key, 'delta': delta,
                             'mean_debt_pct_gdp': r['reference']['summary']['mean'],
                             'paired_mean_change_pp': r['reference']['summary']['mean']-base['reference']['summary']['mean'],
                             'ranking': None})
    for scale in [.9, 1.1]:
        r = simulate(config, profiles, runs=runs, seed=seed, uncertainty_scale=scale)
        variants.append({'parameter': 'uncertainty_scale', 'value': scale, 'summary': r['reference']['summary'], 'ranking': None})
    for debt in [config['initial_debt']-.01, config['initial_debt']+.01]:
        r = simulate(config, profiles, runs=runs, seed=seed, initial_debt=debt)
        variants.append({'parameter': 'initial_debt', 'value': debt, 'summary': r['reference']['summary'], 'ranking': None})
    for alternative_seed in [seed+1, seed+2]:
        r = simulate(config, profiles, runs=runs, seed=alternative_seed)
        variants.append({'parameter': 'seed', 'value': alternative_seed, 'summary': r['reference']['summary'], 'ranking': None})
    for weights in [{'health': 1}, {'employment': 1}, {'health': .5, 'education': .5}]:
        r = simulate(config, profiles, runs=runs, seed=seed, weights=weights)
        variants.append({'parameter': 'weights', 'value': weights, 'ranking': r['ranking'],
                         'reference_unchanged': r['reference']==base['reference'],
                         'status': r['weight_sensitivity']})
    return {'baseline_run_id': base['run_id'], 'variants': variants,
            'executed_reference_trajectories_in_this_sensitivity_call': runs*(1+len(variants)),
            'ranking_inversions': None, 'reason': 'No identified political ranking exists to invert.'}


def validate(root=ROOT):
    config, profiles = load_inputs(root)
    audit = json.loads((root/'research/audit_checks.json').read_text())
    first = json.loads((root/'research/first_round.json').read_text())
    if audit['status'] != 'pass':
        raise ValueError('research audit did not pass')
    if {p['id'] for p in profiles} != {c['id'] for c in first['candidates']}:
        raise ValueError('strategy/electoral identifier mismatch')
    if sum(c['votes'] for c in first['candidates']) != first['valid_votes']:
        raise ValueError('electoral sum mismatch')
    for profile in profiles:
        dossier = json.loads((root/profile['research_file']).read_text())
        evidence_ids = {e['id'] for e in dossier['evidence']}
        for axis in profile['axes'].values():
            if axis['policy_effect'] is not None or not set(axis['evidence_ids']) <= evidence_ids:
                raise ValueError('unsupported effect or broken evidence link')
    simulate(config, profiles, runs=8)
    return {'status': 'pass', 'profiles': len(profiles),
            'program_excerpts_verified_in_audit': audit['verified_program_excerpts'],
            'scientific_gate': audit['scientific_gate'], 'config_sha256': digest(config)}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Pesquisa oficial, stress exploratório e ranking documental experimental')
    parser.add_argument('command', choices=['research', 'validate', 'simulate', 'analyze', 'empirical', 'integrate', 'diagnose', 'report', 'export', 'sensitivity', 'refresh-data'])
    parser.add_argument('--runs', type=int, default=100_000)
    parser.add_argument('--seed', type=int, default=20261015)
    parser.add_argument('--scenario', default='all')
    parser.add_argument('--out', type=Path, default=ROOT/'results')
    parser.add_argument('--observed', type=Path, default=ROOT/'data/observed.json', help='Snapshot oficial; não calibra parâmetros do benchmark')
    parser.add_argument('--use-observed-debt', action='store_true', help='Usa somente a dívida inicial oficial; juros, crescimento e primário continuam hipotéticos')
    parser.add_argument('--empirical-data', type=Path, default=ROOT/'data/empirical_monthly.json')
    parser.add_argument('--batch-size', type=int, default=10_000)
    parser.add_argument('--simulation-dir', default='results-1m', help='Simulação empírica preservada a vincular na integração, relativa à raiz do projeto')
    parser.add_argument('--public-catalog', default='research/public_catalog.json', help='Catálogo versionado de respostas públicas, relativo à raiz do projeto')
    parser.add_argument('--legacy-documentary-ranking', action='store_true', help='Somente reprodução histórica: ranking documental descontinuado por seleção desigual; não usar como ranking de governo')
    args = parser.parse_args(argv)
    try:
        if args.use_observed_debt and args.command not in ['simulate', 'analyze']:
            raise ValueError('--use-observed-debt aplica-se somente a simulate/analyze')
        if args.legacy_documentary_ranking and args.command != 'analyze':
            raise ValueError('--legacy-documentary-ranking aplica-se somente a analyze')
        if args.command in {'simulate', 'analyze', 'empirical', 'integrate'} and args.out.exists() and any(args.out.iterdir()):
            raise ValueError('Destino ocupado: use --out com nova pasta para preservar o histórico e evitar artefatos obsoletos')
        config, profiles = load_inputs()
        if args.command == 'integrate':
            report = build_registry(ROOT, args.out, simulation_dir=args.simulation_dir, publication=True, catalog_file=args.public_catalog)
            print(json.dumps({'bundle_id': report['bundle_id'], 'counts': report['counts'],
                              'missing': report['coverage']['missing'], 'dashboard': str(args.out/'dashboard.html')}, ensure_ascii=False, indent=2))
        elif args.command == 'empirical':
            if args.scenario != 'all':
                raise ValueError('Cenários artificiais não se aplicam ao modo empírico')
            snapshot = json.loads(args.empirical_data.read_text())
            result = run_empirical(snapshot, args.out, runs=args.runs, seed=args.seed, batch_size=args.batch_size)
            backtest = rolling_backtest(snapshot, seed=args.seed)
            evidence_path = ROOT/'research/expanded_evidence.json'
            evidence = json.loads(evidence_path.read_text()) if evidence_path.exists() else None
            export_empirical(result, backtest, args.out, evidence=evidence)
            print(json.dumps({'run_id': result['run_id'], 'counts': result['counts'], 'backtest': backtest['by_metric'],
                              'dashboard': str(args.out/'dashboard.html')}, ensure_ascii=False, indent=2))
        elif args.command == 'research':
            for p in profiles:
                d = json.loads((ROOT/p['research_file']).read_text())
                print(f"{p['name']} | {p['party']} | evidências: {len(d['evidence'])}")
            print('Fontes oficiais e trechos: research/; impactos condicionais: research/impacts.json')
        elif args.command == 'refresh-data':
            snapshot = fetch_snapshot()
            if not snapshot['series']:
                raise ValueError('Nenhuma fonte disponível; snapshot anterior preservado. ' + json.dumps(snapshot['errors'], ensure_ascii=False))
            args.observed.parent.mkdir(parents=True, exist_ok=True)
            args.observed.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(json.dumps({'snapshot': str(args.observed), 'series': len(snapshot['series']), 'errors': snapshot['errors']}, ensure_ascii=False, indent=2))
        elif args.command == 'validate':
            print(json.dumps(validate(), ensure_ascii=False, indent=2))
        elif args.command in ['simulate', 'analyze']:
            validate()
            observed = load_snapshot(args.observed) if args.observed.exists() else None
            debt_source = None
            if args.use_observed_debt:
                debt_series = next((s for s in (observed or {}).get('series', []) if s['id'] == 'gross_debt_gdp'), None)
                if debt_series is None:
                    raise ValueError('Dívida oficial ausente; execute refresh-data antes de --use-observed-debt')
                debt_source = dict(debt_series['observations'][-1], sgs_id=debt_series['sgs_id'], url=debt_series['url'])
            result = simulate(config, profiles, runs=args.runs, seed=args.seed, scenario=args.scenario,
                              initial_debt=debt_source['value']/100 if debt_source else None)
            if debt_source:
                result['initial_debt_source'] = debt_source
                result['reference']['metrics']['indicators'][0]['classification'] = 'observed'
            if observed is not None:
                result['observed'] = observed
                result['observed_snapshot_sha256'] = digest(result['observed'])
            if args.command == 'analyze':
                result['documentary_ranking_status'] = 'disabled_by_default_unequal_corpus_and_editorial_weights'
                if args.legacy_documentary_ranking:
                    result['experimental_ranking'] = analyze_programs(load_dossiers(), runs=args.runs, seed=args.seed)
                    result['documentary_ranking_status'] = 'legacy_reproduction_not_government_evidence'
                history_path = ROOT/'research/government_history.json'
                if history_path.exists():
                    result['history'] = summarize_history(json.loads(history_path.read_text()))
                result['analysis_id'] = digest({'run_id': result['run_id'], 'ranking': result.get('experimental_ranking'),
                                                'history': result.get('history'), 'observed': result.get('observed_snapshot_sha256')})
            result['diagnostics'] = build_diagnostics(result)
            export_result(result, args.out)
            print(report_text(result), end='')
        elif args.command == 'sensitivity':
            validate()
            result = sensitivity(config, profiles, args.runs, args.seed)
            args.out.mkdir(parents=True, exist_ok=True)
            (args.out/'sensitivity.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            result = json.loads((args.out/'results.json').read_text())
            if args.command == 'diagnose':
                result['diagnostics'] = build_diagnostics(result)
            if args.command in ['export', 'diagnose']:
                export_result(result, args.out)
            print(report_text(result), end='')
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f'Erro: {exc}\n')


if __name__ == '__main__':
    main()
