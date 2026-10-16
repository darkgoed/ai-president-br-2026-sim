import copy
import json
import math
from decimal import Decimal, ROUND_HALF_UP
import numpy as np
import pytest
from src.engine import ROOT, debt_step, load_inputs, simulate, describe
from src.cli import export_result, sensitivity, validate


def test_names_parties_and_order_never_change_numeric_reference():
    cfg, profiles = load_inputs()
    base = simulate(cfg, profiles, runs=80)
    renamed = copy.deepcopy(profiles[::-1])
    for i, p in enumerate(renamed):
        p.update(name=f'Anonymous {i}', party='Anonymous', id=f'new-{i}')
    other = simulate(cfg, renamed, runs=80)
    assert other['reference'] == base['reference']
    assert other['ranking'] is None
    assert all(v is None for p in other['profiles'] for v in p['outcomes'].values())


@pytest.mark.parametrize('weights', [{'health': 1}, {'education': 1}, {'employment': .5, 'social': .5}])
def test_objective_weights_cannot_invent_missing_outcomes(weights):
    cfg, profiles = load_inputs()
    a = simulate(cfg, profiles, runs=80)
    b = simulate(cfg, profiles, runs=80, weights=weights)
    assert a['reference'] == b['reference']
    assert b['ranking'] is None


def test_analytical_four_year_solution_and_units():
    cfg, profiles = load_inputs()
    cfg['bounds'] = {'interest': [.1, .1], 'growth': [.05, .05], 'primary': [.02, .02]}
    result = simulate(cfg, profiles, runs=20, scenario='stable')
    factor = 1.1/1.05
    manual = .8*factor**4 - .02*sum(factor**j for j in range(4))
    for row in result['reference']['trajectories']:
        assert row['debt_pct_gdp'][-1] == pytest.approx(manual*100)


def test_paired_parameter_sensitivity_has_expected_accounting_sign():
    cfg, profiles = load_inputs()
    base = simulate(cfg, profiles, runs=80)
    get = lambda r: np.array([x['debt_pct_gdp'][-1] for x in r['reference']['trajectories']])
    for key, sign in [('primary', -1), ('growth', -1), ('interest', 1)]:
        changed = simulate(cfg, profiles, runs=80, shifts={key: .005})
        assert np.all((get(changed)-get(base))*sign > 0)
        assert changed['ranking'] is None


def test_alternative_seed_changes_distribution_not_identification():
    cfg, profiles = load_inputs()
    a, b = [simulate(cfg, profiles, runs=80, seed=s) for s in [1, 2]]
    assert a['reference']['trajectories'] != b['reference']['trajectories']
    assert not a['candidate_comparison_identified'] and not b['candidate_comparison_identified']


@pytest.mark.parametrize('kwargs', [{'runs': 1}, {'runs': True}, {'runs': 2.5}, {'seed': -1}, {'scenario': 'fake'}, {'uncertainty_scale': 0}, {'initial_debt': float('nan')}, {'weights': {'health': -1}}])
def test_invalid_inputs_rejected(kwargs):
    cfg, profiles = load_inputs()
    with pytest.raises(ValueError):
        simulate(cfg, profiles, **kwargs)


def test_unsupported_political_effect_fails_closed():
    cfg, profiles = load_inputs()
    profiles[0]['axes']['health']['policy_effect'] = .1
    with pytest.raises(ValueError, match='causal'):
        simulate(cfg, profiles)


def test_official_votes_and_rounding():
    data = json.loads((ROOT/'research/first_round.json').read_text())
    assert sum(c['votes'] for c in data['candidates']) == data['valid_votes']
    for c in data['candidates']:
        percentage = (Decimal(c['votes'])*100/Decimal(data['valid_votes'])).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
        assert percentage == Decimal(c['valid_vote_percent_official'].replace(',', '.'))


def test_summaries_match_independent_python_calculation():
    import statistics
    values = [1., 2., 3., 4., 5.]
    summary = describe(values)
    assert summary['mean'] == statistics.mean(values)
    assert summary['median'] == statistics.median(values)
    assert summary['std'] == pytest.approx(statistics.stdev(values))
    assert summary['q025'] == pytest.approx(1.1)
    assert summary['q975'] == pytest.approx(4.9)


def test_export_roundtrip_and_exact_csv_row_counts(tmp_path):
    import csv
    cfg, profiles = load_inputs()
    result = simulate(cfg, profiles, runs=80)
    export_result(result, tmp_path)
    assert json.loads((tmp_path/'results.json').read_text()) == result
    with (tmp_path/'trajectories.csv').open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 80*5
    assert sum(result['reference']['histogram']['counts']) == 80
    assert 'NÃO IDENTIFICADA' in (tmp_path/'report.txt').read_text()


def test_evidence_integrity_and_equal_missingness():
    result = validate()
    assert result['status'] == 'pass'
    _, profiles = load_inputs()
    assert len({tuple(p['axes']) for p in profiles}) == 1
    assert all(a['origin']=='informacao_indisponivel' for p in profiles for a in p['axes'].values())
    impacts = json.loads((ROOT/'research/impacts.json').read_text())
    assert len(impacts['dossiers']) == 12
    assert all(x['quantified_population_effect'] is None for d in impacts['dossiers'] for x in d['proposals'])


def test_complete_sensitivity_ledger_and_no_rank_inversions():
    cfg, profiles = load_inputs()
    result = sensitivity(cfg, profiles, 80, 3)
    assert len(result['variants']) == 15
    assert result['executed_reference_trajectories_in_this_sensitivity_call'] == 1280
    assert result['ranking_inversions'] is None


@pytest.mark.parametrize('key,value', [('horizon_years', 0), ('bounds', {'interest': [.12, .06], 'growth': [.02, .08], 'primary': [-.02, .02]})])
def test_invalid_config_rejected(key, value):
    cfg, profiles = load_inputs()
    cfg[key] = value
    with pytest.raises(ValueError):
        simulate(cfg, profiles)


def test_unknown_shift_not_silently_ignored():
    cfg, profiles = load_inputs()
    with pytest.raises(ValueError):
        simulate(cfg, profiles, shifts={'employment': .1})
