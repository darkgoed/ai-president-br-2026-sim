"""Regressões adversariais dos achados da auditoria; fixtures não são fatos."""
from copy import deepcopy
from datetime import date
import json
import pytest


def test_observed_series_identity_swap_fails_closed(tmp_path):
    from src.observed import fetch_snapshot, load_snapshot
    snapshot = fetch_snapshot(fetcher=lambda url: b'[{"data":"01/01/2020","valor":"1"}]', today=date(2020, 1, 31))
    snapshot['series'][0]['id'] = 'gross_debt_gdp'
    path = tmp_path/'swapped.json'
    path.write_text(json.dumps(snapshot))
    with pytest.raises(ValueError, match='identidade|duplicad'):
        load_snapshot(path)


def test_integrator_rejects_normalized_value_changed_under_valid_raw_hash(tmp_path):
    import hashlib
    from src.knowledge_build import build_registry
    raw_row = {'exercicio': 2025, 'cod_ibge': 1, 'periodo': 6,
               'conta': 'Receita', 'coluna': 'Até o Bimestre', 'cod_conta': 'Receita',
               'instituicao': 'União', 'valor': 12}
    raw = json.dumps({'count': 1, 'hasMore': False, 'items': [raw_row]}).encode()
    (tmp_path/'research').mkdir()
    (tmp_path/'response.json').write_bytes(raw)
    row = dict(raw_row, valor=999)
    dataset = {'provider': 'Tesouro/Siconfi', 'id': 'siconfi-1-2025',
               'entity_id': '1', 'period': '2025-B6', 'label': 'RREO-Anexo 14',
               'response_path': 'response.json', 'sha256': hashlib.sha256(raw).hexdigest(),
               'url': 'https://apidatalake.tesouro.gov.br/ords/cdwhprd/siconfi/tt/rreo?an_exercicio=2025&nr_periodo=6&id_ente=1',
               'retrieved_at': '2026-01-01T00:00:00Z', 'observations': [row]}
    (tmp_path/'research/public_catalog.json').write_text(json.dumps({'datasets': [dataset], 'errors': []}))
    with pytest.raises(ValueError, match='original|normalizad'):
        build_registry(tmp_path, tmp_path/'out')


def test_new_analysis_refuses_reusing_output_with_legacy_ranking(tmp_path):
    from src.cli import main
    main(['analyze', '--runs', '8', '--out', str(tmp_path), '--legacy-documentary-ranking'])
    before = {p.name: p.read_bytes() for p in tmp_path.iterdir()}
    with pytest.raises(SystemExit) as error:
        main(['analyze', '--runs', '8', '--out', str(tmp_path)])
    assert error.value.code == 2
    assert before == {p.name: p.read_bytes() for p in tmp_path.iterdir()}


@pytest.mark.parametrize('legacy', [False, True])
def test_verifier_accepts_each_explicit_ranking_mode(tmp_path, legacy):
    import runpy
    from src.engine import ROOT
    from src.cli import main
    main(['analyze', '--runs', '8', '--out', str(tmp_path)] + (['--legacy-documentary-ranking'] if legacy else []))
    verify = runpy.run_path(str(ROOT/'tools/verify_analysis.py'))['verify']
    verify(tmp_path, runs=8)
    report = json.loads((tmp_path/'verification.json').read_text())
    assert report['ranking_mode'] == ('legacy' if legacy else 'disabled')


def test_bootstrap_counts_draws_and_measures_sequences_separately(tmp_path):
    import numpy as np
    from src.empirical import run_empirical
    import runpy
    from src.engine import ROOT
    fixture = runpy.run_path(str(ROOT/'tests/test_empirical.py'))['monthly_fixture']
    result = run_empirical(fixture(), tmp_path, runs=20, batch_size=7)
    indices = np.load(tmp_path/'block_indices.npy')
    assert result['counts']['sampled_paths'] == 20
    assert 'unique_paths' not in result['counts']
    assert result['counts']['distinct_block_sequences'] == len(np.unique(indices, axis=0))


def test_publication_gate_rejects_empty_candidate_corpus_before_creating_output(tmp_path):
    from src.knowledge_build import build_registry
    with pytest.raises(ValueError, match='publicação'):
        build_registry(tmp_path, tmp_path/'out', publication=True)
    assert not (tmp_path/'out').exists()


def test_empirical_chunk_cannot_claim_different_source_url():
    import runpy
    from src.engine import ROOT
    from src.empirical_data import validate_snapshot
    snapshot = runpy.run_path(str(ROOT/'tests/test_empirical.py'))['monthly_fixture']()
    snapshot['series'][0]['chunks'][0]['url'] = snapshot['series'][1]['chunks'][0]['url']
    with pytest.raises(ValueError, match='identidade|URL'):
        validate_snapshot(snapshot)


def test_observed_summary_cannot_diverge_from_verified_observations(tmp_path):
    from src.observed import fetch_snapshot, load_snapshot
    snapshot = fetch_snapshot(fetcher=lambda url: b'[{"data":"01/01/2020","valor":"1"}]', today=date(2020, 1, 31))
    snapshot['series'][0]['statistics']['n'] = 999
    path = tmp_path/'changed-summary.json'
    path.write_text(json.dumps(snapshot))
    with pytest.raises(ValueError, match='Estatísticas'):
        load_snapshot(path)
