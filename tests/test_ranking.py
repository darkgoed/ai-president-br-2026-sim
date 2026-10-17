import copy
import json
import pytest

from src.engine import ROOT
from src.ranking import analyze_programs, load_dossiers


def test_ranking_is_documentary_reproducible_and_has_audit_trail():
    dossiers = load_dossiers()
    result = analyze_programs(dossiers, runs=100, seed=17)
    assert result == analyze_programs(dossiers, runs=100, seed=17)
    assert result['classification'] == 'experimental_documentary_ranking_not_government_forecast'
    assert result['counts']['weight_analyses'] == 100
    assert result['counts']['candidate_weight_evaluations'] == 1200
    assert len(result['candidates']) == 12
    assert sum(row['first_place_fractional_pct'] for row in result['candidates']) == pytest.approx(100)
    for row in result['candidates']:
        assert len(row['indicators']) == 60
        assert 0 <= row['score_equal_weights'] <= 100
        assert row['government_outcome_estimate'] is None
        assert all(i['evidence_ids'] for i in row['indicators'] if i['detected'] is True)
        assert sum(row['rank_counts'].values()) == 100


def test_names_parties_order_never_affect_rank_scores():
    dossiers = load_dossiers()
    a = analyze_programs(dossiers, runs=80, seed=9)
    renamed = copy.deepcopy(dossiers[::-1])
    for d in renamed:
        d['supplied_name'] = 'Anonymous'
        d['verified_name'] = 'Anonymous'
        d['verified_party'] = 'Anonymous'
    b = analyze_programs(renamed, runs=80, seed=9)
    get = lambda r: {x['id']: (x['score_equal_weights'], x['first_place_fractional_pct'], x['rank_counts']) for x in r['candidates']}
    assert get(a) == get(b)


def test_missing_document_does_not_become_zero_government_performance():
    dossiers = load_dossiers()
    dossiers[0]['axes']['saude'] = []
    result = analyze_programs(dossiers, runs=30)
    assert 'saude' not in result['common_axes']
    row = next(x for x in result['candidates'] if x['id'] == dossiers[0]['official_candidate_id'])
    assert all(i['detected'] is None for i in row['indicators'] if i['axis'] == 'saude')
    assert row['government_outcome_estimate'] is None


def test_identical_documents_share_first_place_without_name_tiebreak():
    dossiers = load_dossiers()[:1]
    twin = copy.deepcopy(dossiers[0])
    twin['official_candidate_id'] = 'twin'
    result = analyze_programs(dossiers + [twin], runs=60)
    assert [x['position_equal_weights'] for x in result['candidates']] == [1, 1]
    assert all(x['first_place_fractional_pct'] == 50 for x in result['candidates'])


@pytest.mark.parametrize('runs', [True, 1, 1.2, -2])
def test_invalid_analysis_count_rejected(runs):
    with pytest.raises(ValueError):
        analyze_programs(load_dossiers(), runs=runs)


def test_analysis_cli_exports_ranking_without_inventing_policy_effects(tmp_path):
    import csv
    from src.cli import main
    main(['analyze', '--legacy-documentary-ranking', '--runs', '24', '--out', str(tmp_path)])
    result = json.loads((tmp_path/'results.json').read_text())
    assert result['counts']['unique_reference_trajectories'] == 24
    assert result['experimental_ranking']['counts']['weight_analyses'] == 24
    assert result['ranking'] is None
    assert result['candidate_comparison_identified'] is False
    assert len(result['analysis_id']) == 64
    with (tmp_path/'ranking_indicators.csv').open() as f:
        assert len(list(csv.DictReader(f))) == 720
    with (tmp_path/'ranking.csv').open() as f:
        assert len(list(csv.DictReader(f))) == 12
    html = (tmp_path/'dashboard.html').read_text()
    assert 'NÃO quem governará melhor' in html
    assert 'pesos iguais' in html
    assert all(value is None for p in result['profiles'] for value in p['outcomes'].values())


def test_history_summary_uses_same_period_previous_year_and_keeps_missing():
    from src.history import summarize_history
    data = {'series': [{'id': 'test', 'location': 'Brasil', 'label': 'Desocupação', 'unit': '%',
                       'frequency': 'trimestral', 'url': 'https://servicodados.ibge.gov.br/',
                       'observations': [{'period': '202502', 'value': 7.0}, {'period': '202601', 'value': 6.0}, {'period': '202602', 'value': 5.0}]}]}
    result = summarize_history(data)['summaries'][0]
    assert result['change_year_ago'] == -2
    assert result['previous'] == 6
    assert result['baseline'] is None
    assert result['classification'] == 'historical_descriptive_not_causal'
