"""Sondas de auditoria: somente fixtures isoladas; não altera snapshots/resultados.
Reauditoria: exige rejeição dos ataques locais; mantém relatório histórico separado.
"""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import runpy
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.cli import main
from src.knowledge_build import build_registry
from src.observed import load_snapshot, CATALOG
from src.public_data import normalize_ibge
verify = runpy.run_path(str(ROOT/'tools/verify_analysis.py'))['verify']


def audit(simulation_dir='results-1m-v2', catalog_file='research/public-extension-v2/public_catalog.json'):
    findings = {}
    indices = np.load(ROOT/simulation_dir/'block_indices.npy', mmap_mode='r')
    distinct = len(np.unique(indices, axis=0))
    current = json.loads((ROOT/simulation_dir/'empirical_results.json').read_text())
    assert 'unique_paths' not in current['counts']
    assert current['counts']['distinct_block_sequences'] == distinct
    findings['A01_corrected_counts'] = {
        'declared_sampled_paths': current['counts']['sampled_paths'],
        'draws': len(indices), 'distinct_block_sequences': distinct,
        'repeated_block_sequences': len(indices)-distinct,
        'status': 'pass', 'note': 'Repetição é esperada e não foi removida; contagens agora têm significados separados.'}

    # Oráculo independente: razões de níveis/odds e produto de IPCA nos
    # meses originais, sem chamar annual_blocks ou project do simulador.
    snapshot = json.loads((ROOT/simulation_dir/'calibration_snapshot.json').read_text())
    series = {s['id']: {r['period']: r['value'] for r in s['observations']} for s in snapshot['series']}
    periods = sorted(set.intersection(*(set(s) for s in series.values())))
    raw = np.array([[series[key][p] for key in ['debt', 'unemployment', 'activity', 'inflation']] for p in periods])
    paths = np.load(ROOT/simulation_dir/'paths.npy', mmap_mode='r')
    selected = np.random.default_rng(271828).choice(len(indices), size=min(1000, len(indices)), replace=False)
    max_error = 0.0
    for index in selected:
        expected = np.array([*raw[-1, :3], 100.0])
        for year, start in enumerate(indices[index], 1):
            end = start+12
            expected[0] *= raw[end, 0]/raw[start, 0]
            odds = expected[1]/(100-expected[1])
            odds *= (raw[end, 1]/(100-raw[end, 1]))/(raw[start, 1]/(100-raw[start, 1]))
            expected[1] = 100*odds/(1+odds)
            expected[2] *= raw[end, 2]/raw[start, 2]
            expected[3] *= np.prod(1+raw[start+1:end+1, 3]/100)
            np.testing.assert_allclose(paths[index, year], expected, rtol=1e-11, atol=1e-11)
            max_error = max(max_error, float(np.max(np.abs(paths[index, year]-expected))))
    findings['independent_projection_oracle'] = {'sampled_paths': len(selected), 'years_per_path': 4,
        'status': 'pass', 'maximum_absolute_roundoff_error': max_error}
    observed_now = load_snapshot(ROOT/'data/observed.json')
    expected_ids = {key: (sgs, unit) for key, sgs, _, unit, _, _ in CATALOG}
    findings['current_observed_series_identities'] = {'checked': len(observed_now['series']),
        'mismatches': [s['id'] for s in observed_now['series'] if expected_ids.get(s['id']) != (s['sgs_id'], s['unit'])]}

    catalog = json.loads((ROOT/catalog_file).read_text())
    mismatches = []
    for dataset in catalog['datasets']:
        raw = json.loads((ROOT/dataset['response_path']).read_text())
        if dataset['provider'] == 'IBGE':
            expected = normalize_ibge(raw, dataset['observations'][0]['aggregate'], dataset['observations'][0]['variable'])
        elif dataset['provider'] == 'Tesouro/Siconfi':
            expected = raw['items']
        else:
            expected = [{'period': r['date'], 'value': r['value'], 'entity': 'Brasil', 'entity_id': 'BRA'} for r in raw[1]]
        if expected != dataset['observations']:
            mismatches.append(dataset['id'])
    findings['current_public_data_comparison'] = {'datasets_checked': len(catalog['datasets']), 'mismatches': mismatches}

    with tempfile.TemporaryDirectory(prefix='presidencia-audit-', dir=os.environ['TMPDIR']) as temp:
        temp = Path(temp)
        root = temp/'fixture'
        (root/'research').mkdir(parents=True)
        dataset = deepcopy(next(d for d in catalog['datasets'] if d['provider'] == 'IBGE'))
        original = dataset['observations'][0]['value']
        assert original is not None
        dataset['observations'] = [dataset['observations'][0]]
        dataset['observations'][0]['value'] = original+999
        raw_path = root/dataset['response_path']
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes((ROOT/dataset['response_path']).read_bytes())
        meta_path = root/dataset['metadata']['response_path']
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_bytes((ROOT/dataset['metadata']['response_path']).read_bytes())
        (root/'research/public_catalog.json').write_text(json.dumps({'datasets': [dataset], 'errors': []}))
        try:
            build_registry(root, temp/'integrated')
        except ValueError as error:
            assert 'normalizad' in str(error)
            findings['A02_modified_value_rejected'] = {'status': 'pass', 'error': str(error)}
        else:
            raise AssertionError('A02: valor adulterado aceito')
        try:
            build_registry(root, temp/'empty-publication', publication=True)
        except ValueError as error:
            assert 'publicação' in str(error)
            findings['A06_publication_gate'] = {'status': 'pass', 'error': str(error)}
        else:
            raise AssertionError('A06: publicação incompleta aceita')

        observed = json.loads((ROOT/'data/observed.json').read_text())
        debt = next(s for s in observed['series'] if s['id'] == 'gross_debt_gdp')
        ipca = next(s for s in observed['series'] if s['id'] == 'ipca_month')
        debt['id'] = 'renamed_original_debt'
        ipca['id'] = 'gross_debt_gdp'
        snapshot_path = temp/'metadata-swapped.json'
        snapshot_path.write_text(json.dumps(observed))
        try:
            load_snapshot(snapshot_path)
        except ValueError as error:
            assert 'identidade' in str(error)
            findings['A03_identity_swap_rejected'] = {'status': 'pass', 'error': str(error)}
        else:
            raise AssertionError('A03: IPCA aceito como dívida')

        with redirect_stdout(io.StringIO()):
            main(['analyze', '--runs', '8', '--out', str(temp/'stale'), '--legacy-documentary-ranking'])
        before = {p.name: p.read_bytes() for p in (temp/'stale').iterdir()}
        try:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                main(['analyze', '--runs', '8', '--out', str(temp/'stale')])
        except SystemExit as error:
            assert error.code == 2
        else:
            raise AssertionError('A04: sobrescrita aceita')
        assert before == {p.name: p.read_bytes() for p in (temp/'stale').iterdir()}
        findings['A04_existing_output_preserved'] = {'status': 'pass', 'files_unchanged': True}
        with redirect_stdout(io.StringIO()):
            verify(temp/'stale', runs=8)
            main(['analyze', '--runs', '8', '--out', str(temp/'default')])
            verify(temp/'default', runs=8)
        findings['A05_both_verifier_modes'] = {'status': 'pass', 'default_and_legacy_verified': True}
    return findings


if __name__ == '__main__':
    print(json.dumps(audit(), ensure_ascii=False, indent=2))
