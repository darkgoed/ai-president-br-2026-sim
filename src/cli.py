"""CLI reproduzível: python -m src.cli --help."""
import argparse
import csv
import json
from pathlib import Path
from .engine import ROOT, load_inputs, simulate, digest


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
    lines += ['Comparação entre candidaturas: NÃO IDENTIFICADA.',
              'Ranking: não calculado. Ausência de dados não é zero nem empate.',
              'Pesos alternativos: não identificáveis sem resultados sociais.',
              'Limitações:'] + ['  ' + x for x in result['limitations']]
    return '\n'.join(lines) + '\n'


def export_result(result, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    text = report_text(result)
    (out / 'report.txt').write_text(text)
    (out / 'report.md').write_text('# Execução real\n\n```text\n'+text+'```\n')
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
    parser = argparse.ArgumentParser(description='Pesquisa oficial e stress exploratório sem ranking político')
    parser.add_argument('command', choices=['research', 'validate', 'simulate', 'report', 'export', 'sensitivity'])
    parser.add_argument('--runs', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=20261015)
    parser.add_argument('--scenario', default='all')
    parser.add_argument('--out', type=Path, default=ROOT/'results')
    args = parser.parse_args(argv)
    try:
        config, profiles = load_inputs()
        if args.command == 'research':
            for p in profiles:
                d = json.loads((ROOT/p['research_file']).read_text())
                print(f"{p['name']} | {p['party']} | evidências: {len(d['evidence'])}")
            print('Fontes oficiais e trechos: research/; impactos condicionais: research/impacts.json')
        elif args.command == 'validate':
            print(json.dumps(validate(), ensure_ascii=False, indent=2))
        elif args.command == 'simulate':
            validate()
            result = simulate(config, profiles, runs=args.runs, seed=args.seed, scenario=args.scenario)
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
            if args.command == 'export':
                export_result(result, args.out)
            print(report_text(result), end='')
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f'Erro: {exc}\n')


if __name__ == '__main__':
    main()
