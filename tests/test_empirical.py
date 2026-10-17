import json
from datetime import date
import pytest


def test_history_parser_preserves_more_than_twenty_months():
    from src.empirical_data import parse_sgs_history
    rows = [{'data': f'01/{m:02d}/{year}', 'valor': '1.25'}
            for year in range(2020, 2023) for m in range(1, 13)]
    observations = parse_sgs_history(json.dumps(rows).encode(), date(2026, 10, 16))
    assert len(observations) == 36
    assert observations[0] == {'period': '2020-01', 'value': 1.25}
    assert observations[-1]['period'] == '2022-12'


def test_collector_keeps_raw_provenance_and_rejects_tampering():
    from src.empirical_data import collect_history, validate_snapshot
    snapshot = collect_history(fetcher=lambda url: b'[{"data":"01/01/2010","valor":"1.25"}]', as_of=date(2010, 12, 31))
    assert snapshot['status'] == 'complete'
    assert len(snapshot['series']) == 4
    validate_snapshot(snapshot)
    snapshot['series'][0]['chunks'][0]['raw_json'] = '[]'
    with pytest.raises(ValueError, match='hash'):
        validate_snapshot(snapshot)


def monthly_fixture():
    from src.empirical_data import collect_history
    raw = json.dumps([{'data': f'01/{m:02d}/{year}', 'valor': '1.25'}
                      for year in range(2008, 2011) for m in range(1, 13)]).encode()
    return collect_history(fetcher=lambda url: raw, as_of=date(2010, 12, 31))


def test_joint_preparation_and_projection_preserve_observed_units():
    import numpy as np
    from src.empirical import prepare_history, annual_blocks, project
    prepared = prepare_history(monthly_fixture())
    blocks = annual_blocks(prepared['changes'])
    assert prepared['changes'].shape == (35, 4)
    assert blocks.shape == (24, 4)
    paths = project(prepared['initial'], blocks, np.zeros((2, 4), dtype=int))
    assert paths.shape == (2, 5, 4)
    assert paths[0, -1, 0] == pytest.approx(1.25)
    assert paths[0, -1, 1] == pytest.approx(1.25)
    assert paths[0, -1, 2] == pytest.approx(1.25)
    assert paths[0, -1, 3] == pytest.approx(100 * (1 + .0125)**48)


def test_batched_execution_has_exact_total_and_is_batch_size_invariant(tmp_path):
    import numpy as np
    from src.empirical import run_empirical
    a = run_empirical(monthly_fixture(), tmp_path/'a', runs=35, seed=7, batch_size=8)
    b = run_empirical(monthly_fixture(), tmp_path/'b', runs=35, seed=7, batch_size=13)
    assert a['counts']['sampled_paths'] == 35
    assert a['summary'] == b['summary']
    paths = np.load(tmp_path/'a/paths.npy', mmap_mode='r')
    assert paths.shape == (35, 5, 4)
    assert np.array_equal(paths, np.load(tmp_path/'b/paths.npy', mmap_mode='r'))
    assert a['government_ranking'] is None
    assert a['candidate_effects_identified'] is False
    assert json.loads((tmp_path/'a/progress.json').read_text())['completed_paths'] == 35


def test_backtest_uses_only_past_training_blocks_and_naive_baseline():
    from src.empirical import rolling_backtest
    snapshot = monthly_fixture()
    result = rolling_backtest(snapshot, min_training_months=24, draws=50)
    assert result['vintage_policy'] == 'latest_revised_data_pseudo_out_of_sample_not_real_time'
    assert result['counts']['origins'] == 1
    assert result['origins'][0]['last_training_month'] < result['origins'][0]['target_month']
    assert result['origins'][0]['training_block_last_end'] <= result['origins'][0]['last_training_month']
    assert result['by_metric']['debt']['baseline_mae'] == pytest.approx(0)
    assert result['by_metric']['prices']['baseline_mae'] > 0
    assert result['by_metric']['prices']['bootstrap_mae'] == pytest.approx(0, abs=1e-8)
    assert result['government_forecast_validated'] is False


def test_cli_empirical_writes_dashboard_and_does_not_reuse_documentary_ranking(tmp_path):
    from src.cli import main
    snapshot = tmp_path/'history.json'
    snapshot.write_text(json.dumps(monthly_fixture()))
    output = tmp_path/'output'
    main(['empirical', '--empirical-data', str(snapshot), '--runs', '30', '--out', str(output)])
    result = json.loads((output/'empirical_results.json').read_text())
    assert result['counts']['sampled_paths'] == 30
    assert result['government_ranking'] is None
    assert (output/'dashboard.html').exists()
    assert 'Não é ranking de governos' in (output/'dashboard.html').read_text()
    assert (output/'backtest.json').exists()


@pytest.mark.parametrize('runs', [True, 1, -1, 1.5, 10000001])
def test_empirical_rejects_invalid_counts_before_creating_output(tmp_path, runs):
    from src.empirical import run_empirical
    with pytest.raises(ValueError, match='runs'):
        run_empirical(monthly_fixture(), tmp_path/'invalid', runs=runs)
    assert not (tmp_path/'invalid').exists()


def test_empirical_refuses_to_overwrite_completed_paths(tmp_path):
    from src.empirical import run_empirical
    run_empirical(monthly_fixture(), tmp_path, runs=8)
    with pytest.raises(ValueError, match='preservar'):
        run_empirical(monthly_fixture(), tmp_path, runs=8)


def test_history_joint_gap_and_invalid_domains_fail_closed():
    from src.empirical_data import collect_history
    from src.empirical import prepare_history
    rows = [{'data': f'01/{m:02d}/{y}', 'valor': '1.25'} for y in range(2008, 2011) for m in range(1, 13)]
    del rows[15]
    snapshot = collect_history(fetcher=lambda url: json.dumps(rows).encode(), as_of=date(2010, 12, 31))
    with pytest.raises(ValueError, match='Lacuna'):
        prepare_history(snapshot)
    rows.insert(15, {'data': '01/04/2009', 'valor': '0'})
    snapshot = collect_history(fetcher=lambda url: json.dumps(rows).encode(), as_of=date(2010, 12, 31))
    with pytest.raises(ValueError, match='domínio'):
        prepare_history(snapshot)


def test_backtest_future_values_cannot_change_training_prediction():
    from src.empirical_data import collect_history
    from src.empirical import rolling_backtest
    rows = [{'data': f'01/{m:02d}/{y}', 'valor': '1.25'} for y in range(2008, 2012) for m in range(1, 13)]
    first = collect_history(fetcher=lambda url: json.dumps(rows).encode(), as_of=date(2011, 12, 31))
    original = rolling_backtest(first, min_training_months=24, draws=50)
    for row in rows[24:]:
        row['valor'] = '2.5'
    changed = collect_history(fetcher=lambda url: json.dumps(rows).encode(), as_of=date(2011, 12, 31))
    other = rolling_backtest(changed, min_training_months=24, draws=50)
    for metric in original['by_metric']:
        a, b = original['origins'][0]['metrics'][metric], other['origins'][0]['metrics'][metric]
        assert a['bootstrap_median'] == b['bootstrap_median']
        assert a['q025'] == b['q025']
        assert a['q975'] == b['q975']
        assert a['actual'] != b['actual']
