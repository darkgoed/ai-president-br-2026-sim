import math
import pytest


def test_monte_carlo_error_respects_balanced_scenario_strata():
    from src.diagnostics import macro_diagnostics
    result = {'reference': {'scenario_counts': {'a': 2, 'b': 2},
              'trajectories': [
                  {'scenario_id': 0, 'family': 'a', 'debt_pct_gdp': [80, 0]},
                  {'scenario_id': 1, 'family': 'b', 'debt_pct_gdp': [80, 10]},
                  {'scenario_id': 2, 'family': 'a', 'debt_pct_gdp': [80, 2]},
                  {'scenario_id': 3, 'family': 'b', 'debt_pct_gdp': [80, 12]}]}}
    diagnostic = macro_diagnostics(result)
    assert diagnostic['mean_pct_gdp'] == 6
    assert diagnostic['mc_se_pp_gdp'] == pytest.approx(math.sqrt(.5))
    assert diagnostic['mc_approx_95_half_width_pp_gdp'] == pytest.approx(1.96 * math.sqrt(.5))
    assert diagnostic['classification'] == 'numerical_error_conditional_on_artificial_model'
    assert diagnostic['convergence'][-1]['runs'] == 4
    assert diagnostic['convergence'][-1]['delta_from_full_pp'] == 0


def test_ranking_diagnostic_reveals_dependence_on_one_axis_without_policy_claims():
    from src.diagnostics import ranking_diagnostics
    import copy
    ranking = {'common_axes': ['a', 'b'], 'protocol': {'criteria': [{'id': 'x'}, {'id': 'y'}]}, 'candidates': []}
    for name, matrix in [('A', [[True, True], [False, False]]), ('B', [[False, False], [True, False]])]:
        ranking['candidates'].append({'id': name, 'name': name, 'indicators': [
            {'axis': axis, 'criterion': criterion, 'detected': matrix[i][j]}
            for i, axis in enumerate(['a', 'b']) for j, criterion in enumerate(['x', 'y'])]})
    original = copy.deepcopy(ranking)
    result = ranking_diagnostics(ranking)
    assert ranking == original
    assert len(result['variants']) == 4
    assert result['variants'][0]['leaders'] == ['B']
    assert result['baseline_leaders'] == ['A']
    assert result['leader_set_changes'] > 0
    assert result['candidate_fragility'][0]['worst_position'] == 2
    assert result['government_performance_validated'] is False
    assert result['classification'] == 'documentary_method_sensitivity_not_government_confidence'


def test_diagnostics_expose_source_lag_and_missing_government_effects():
    from datetime import date
    from src.diagnostics import build_diagnostics
    from src.engine import load_inputs, simulate
    cfg, profiles = load_inputs()
    result = simulate(cfg, profiles, runs=80)
    result['observed'] = {'retrieved_at': '2026-10-01T12:00:00+00:00', 'errors': [],
                          'series': [{'id': 'ipca', 'frequency': 'mensal', 'unit': '% no mês',
                                      'observations': [{'date': '2026-09-01', 'value': .82}]}]}
    diagnostic = build_diagnostics(result, as_of=date(2026, 10, 16))
    assert diagnostic['data_quality']['snapshot_age_days'] == 15
    assert diagnostic['data_quality']['series'][0]['days_since_reference_date'] == 45
    assert diagnostic['data_quality']['unknown_policy_outcomes'] > 0
    assert diagnostic['validation']['government_forecast_validated'] is False
    assert diagnostic['validation']['backtest_status'] == 'not_available'
    assert diagnostic['ranking'] is None


def test_diagnose_cli_updates_existing_artifact_without_changing_simulation(tmp_path):
    import json
    from src.cli import main
    main(['analyze', '--runs', '80', '--out', str(tmp_path)])
    before = json.loads((tmp_path/'results.json').read_text())
    main(['diagnose', '--out', str(tmp_path)])
    after = json.loads((tmp_path/'results.json').read_text())
    assert after['reference'] == before['reference']
    assert after['run_id'] == before['run_id']
    assert after['analysis_id'] == before['analysis_id']
    assert after.get('experimental_ranking') == before.get('experimental_ranking') is None
    assert after['diagnostics']['validation']['government_forecast_validated'] is False
    assert (tmp_path/'diagnostics.json').exists()
    assert (tmp_path/'diagnostics.csv').exists()
    assert 'Fragilidade e erro numérico' in (tmp_path/'dashboard.html').read_text()


def test_singleton_strata_do_not_claim_zero_numerical_error():
    from src.diagnostics import macro_diagnostics
    from src.engine import load_inputs, simulate
    cfg, profiles = load_inputs()
    diagnostic = macro_diagnostics(simulate(cfg, profiles, runs=2))
    assert diagnostic['mc_se_pp_gdp'] is None
    assert diagnostic['status'] == 'insufficient_within_family_replication'


def test_zero_monte_carlo_noise_does_not_validate_artificial_assumptions():
    from src.diagnostics import build_diagnostics
    from src.engine import load_inputs, simulate
    cfg, profiles = load_inputs()
    cfg['bounds'] = {'interest': [.1, .1], 'growth': [.05, .05], 'primary': [.02, .02]}
    diagnostic = build_diagnostics(simulate(cfg, profiles, runs=80))
    assert diagnostic['macro']['mc_se_pp_gdp'] == pytest.approx(0, abs=1e-10)
    assert diagnostic['validation']['government_forecast_validated'] is False


def test_duplicate_trajectory_ids_are_rejected():
    from src.diagnostics import macro_diagnostics
    from src.engine import load_inputs, simulate
    cfg, profiles = load_inputs()
    result = simulate(cfg, profiles, runs=8)
    result['reference']['trajectories'][1]['scenario_id'] = result['reference']['trajectories'][0]['scenario_id']
    with pytest.raises(ValueError, match='duplicados'):
        macro_diagnostics(result)


def test_missing_common_criterion_cannot_silently_become_zero():
    from src.diagnostics import ranking_diagnostics
    from src.ranking import analyze_programs, load_dossiers
    ranking = analyze_programs(load_dossiers(), runs=20)
    ranking['candidates'][0]['indicators'][0]['detected'] = None
    with pytest.raises(ValueError, match='não revisado'):
        ranking_diagnostics(ranking)
