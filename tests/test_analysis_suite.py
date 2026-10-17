"""Especificações numéricas dos novos diagnósticos; dados sintéticos isolados."""
import json
import runpy
import numpy as np
import pytest
from src.engine import ROOT


def history():
    return runpy.run_path(str(ROOT/'tests/test_empirical.py'))['monthly_fixture']()


def test_multiyear_backtest_uses_only_past_and_exposes_short_history():
    from src.analysis_suite import multi_horizon_backtest
    snapshot = history()
    report = multi_horizon_backtest(snapshot, horizons=(12, 24, 48), min_training_months=24, draws=40)
    assert report['horizons']['12']['counts']['origins'] == 1
    assert report['horizons']['24']['counts']['origins'] == 0
    assert report['horizons']['48']['status'] == 'insufficient_history'
    assert report['government_forecast_validated'] is False
    first = report['horizons']['12']['origins'][0]
    assert first['last_training_month'] < first['target_month']

    assert first['metrics']['prices']['baseline'] == 100
    assert first['metrics']['prices']['actual'] == pytest.approx(100*1.0125**12)
    assert report['horizons']['12']['by_metric']['prices']['bootstrap_mae'] == pytest.approx(0, abs=1e-8)
    assert report['horizons']['12']['by_metric']['debt']['skill_vs_no_change'] is None


def test_history_metrics_match_same_period_previous_year_not_previous_row():
    from src.analysis_suite import summarize_observations
    rows = [{'period': '202001', 'value': 10}, {'period': '202101', 'value': 12},
            {'period': '202103', 'value': None}, {'period': '202201', 'value': 0}]
    report = summarize_observations(rows, unit='%')
    assert report['missing_count'] == 1
    assert report['zero_count'] == 1
    assert report['comparisons'][0]['difference'] == 2
    assert report['comparisons'][0]['unit'] == 'p.p.'
    assert report['comparisons'][0]['relative_change_pct'] == pytest.approx(20)
    assert report['comparisons'][1]['difference'] == -12
    assert report['latest']['value'] == 0
    with pytest.raises(ValueError, match='duplicad'):
        summarize_observations(rows+rows[:1], unit='%')


def test_missing_unit_not_invented_and_zero_denominator_not_divided():
    from src.analysis_suite import summarize_observations
    rows = [{'period': '2020', 'value': 0}, {'period': '2021', 'value': 2}]
    assert summarize_observations(rows, unit=None)['comparisons'] == []
    assert summarize_observations(rows, unit='pessoas')['comparisons'][0]['relative_change_pct'] is None


def test_derived_simulated_metrics_do_not_confuse_percent_and_percentage_points():
    from src.analysis_suite import simulated_metrics
    paths = np.array([[[80, 10, 100, 100], [88, 8, 110, 105]],
                      [[80, 10, 100, 100], [72, 12, 90, 110]]], dtype=float)
    rows = simulated_metrics(paths)
    by_id = {r['id']: r for r in rows}
    assert by_id['year_1_debt_change_pp']['summary']['mean'] == pytest.approx(0)
    assert by_id['year_1_cumulative_inflation_pct']['summary']['mean'] == pytest.approx(7.5)
    assert by_id['year_1_unemployment_change_pp']['unit'] == 'p.p.'
    assert by_id['year_1_activity_growth_pct']['summary']['mean'] == pytest.approx(0)
    assert all(r['classification'] == 'simulated_not_government_effect' for r in rows)


def test_future_values_do_not_change_first_forecast_at_any_horizon():
    from datetime import date, datetime
    from urllib.parse import parse_qs, urlparse
    from src.empirical_data import collect_history
    from src.analysis_suite import multi_horizon_backtest
    def fixture(change_future):
        def fetcher(url):
            query = parse_qs(urlparse(url).query)
            start = datetime.strptime(query['dataInicial'][0], '%d/%m/%Y').date()
            end = datetime.strptime(query['dataFinal'][0], '%d/%m/%Y').date()
            return json.dumps([{'data': f'01/{month:02d}/{year}',
                                'valor': '4.5' if change_future and year >= 2010 else '1.25'}
                               for year in range(2006, 2021) for month in range(1, 13)
                               if start <= date(year, month, 1) <= end]).encode()
        return collect_history(fetcher=fetcher, as_of=date(2020, 12, 31))
    a = multi_horizon_backtest(fixture(False), min_training_months=24, draws=40)
    b = multi_horizon_backtest(fixture(True), min_training_months=24, draws=40)
    for horizon in ['12', '24', '48']:
        first_a = a['horizons'][horizon]['origins'][0]
        first_b = b['horizons'][horizon]['origins'][0]
        assert first_a['last_training_month'] == first_b['last_training_month']
        for metric in ['debt', 'unemployment', 'activity', 'prices']:
            assert first_a['metrics'][metric]['predicted_mean'] == first_b['metrics'][metric]['predicted_mean']
            assert first_a['metrics'][metric]['drift_baseline'] == first_b['metrics'][metric]['drift_baseline']


def test_simulated_drawdowns_include_initial_value_and_are_never_positive():
    from src.analysis_suite import simulated_metrics
    paths = np.array([[[80, 10, 100, 100], [88, 8, 110, 105], [90, 7, 99, 110]],
                      [[80, 10, 100, 100], [72, 12, 90, 110], [70, 11, 81, 121]]], dtype=float)
    report = {r['id']: r for r in simulated_metrics(paths)}
    assert report['year_2_activity_max_drawdown_pct']['summary']['min'] == pytest.approx(-19)
    assert report['year_2_activity_max_drawdown_pct']['summary']['max'] == pytest.approx(-10)


def test_world_bank_indicator_ids_starting_with_n_never_collide():
    from src.analysis_suite import observation_key
    row = {'entity_id': 'BRA', 'period': '2020', 'value': 1}
    a = {'id': 'wb-NY.GDP.PCAP.KD', 'provider': 'Banco Mundial / Same primary source'}
    b = {'id': 'wb-NY.GDP.MKTP.KD.ZG', 'provider': 'Banco Mundial / Same primary source'}
    assert observation_key(a, row) != observation_key(b, row)
    # A mesma célula IBGE em consultas territoriais diferentes é uma repetição.
    c = {'id': 'ibge-6468-4099-N1[1]', 'provider': 'IBGE'}
    d = {'id': 'ibge-6468-4099-N3[all]', 'provider': 'IBGE'}
    assert observation_key(c, row) == observation_key(d, row)
