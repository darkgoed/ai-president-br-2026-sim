import csv
import json
import pytest
from datetime import date

from src.engine import load_inputs, simulate
from src.cli import export_result


def test_fiscal_metrics_are_derived_from_executed_paths(tmp_path):
    cfg, profiles = load_inputs()
    cfg['bounds'] = {'interest': [.1, .1], 'growth': [.05, .05], 'primary': [.02, .02]}
    result = simulate(cfg, profiles, runs=8, scenario='stable')
    assert 'metrics' in result['reference']
    metrics = result['reference']['metrics']
    values = {m['id']: m for m in metrics['indicators']}
    assert len(values) == 90
    assert values['year_1_interest_cost']['value'] == pytest.approx(values['interest_cost']['value'])
    assert values['final_debt']['value'] == pytest.approx(result['reference']['summary']['mean'])
    assert values['debt_change']['value'] == pytest.approx(result['reference']['summary']['mean'] - 80)
    assert values['interest_cost']['value'] == pytest.approx(.1 / 1.05 * .8 * 100)
    assert values['stabilizing_primary']['value'] == pytest.approx((1.1 / 1.05 - 1) * .8 * 100)
    assert values['debt_increases']['value'] == 100
    assert len(metrics['annual']) == 4
    assert metrics['classification'] == 'hypothetical_not_forecast'
    export_result(result, tmp_path)
    assert (tmp_path/'metrics.csv').exists()
    assert (tmp_path/'dashboard.html').exists()
    assert 'Estimativa' in (tmp_path/'dashboard.html').read_text()
    with (tmp_path/'metrics.csv').open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 30
    assert all(row['classification'] == 'hypothetical_not_forecast' for row in rows)
    assert json.loads((tmp_path/'results.json').read_text()) == result


def test_official_snapshot_preserves_source_and_units():
    from src.observed import fetch_snapshot
    import hashlib
    payload = b'[{"data":"01/08/2026","valor":"0.2"},{"data":"01/09/2026","valor":"0.4"}]'
    snapshot = fetch_snapshot(fetcher=lambda url: payload, today=date(2026, 10, 16))
    assert len(snapshot['series']) == 12
    assert snapshot['errors'] == []
    series = snapshot['series'][0]
    assert series['sha256'] == hashlib.sha256(payload).hexdigest()
    assert series['statistics']['change'] == pytest.approx(.2)
    assert series['statistics']['mean'] == pytest.approx(.3)
    assert series['observations'][-1]['date'] == '2026-09-01'
    assert snapshot['classification'] == 'observed_not_policy_effect'


@pytest.mark.parametrize('payload', [b'[]', b'not json',
    b'[{"data":"01/01/2099","valor":"1"}]',
    b'[{"data":"01/08/2026","valor":"NaN"}]',
    b'[{"data":"01/08/2026","valor":"1"},{"data":"01/08/2026","valor":"2"}]'])
def test_invalid_official_data_is_missing_never_fabricated(payload):
    from src.observed import fetch_snapshot
    snapshot = fetch_snapshot(fetcher=lambda url: payload, today=date(2026, 10, 16))
    assert snapshot['series'] == []
    assert len(snapshot['errors']) == 12


def test_unavailable_official_data_is_reported():
    from src.observed import fetch_snapshot
    def unavailable(url):
        raise OSError('offline')
    snapshot = fetch_snapshot(fetcher=unavailable)
    assert snapshot['series'] == []
    assert len(snapshot['errors']) == 12


def test_cli_uses_observed_debt_only_when_explicit(tmp_path):
    from src.observed import fetch_snapshot
    from src.cli import main
    raw = b'[{"data":"01/08/2026","valor":"82.87"}]'
    snapshot = fetch_snapshot(fetcher=lambda url: raw, today=date(2026, 10, 16))
    path = tmp_path / 'observed.json'
    path.write_text(json.dumps(snapshot))
    main(['simulate', '--runs', '8', '--out', str(tmp_path/'observed-run'), '--observed', str(path), '--use-observed-debt'])
    result = json.loads((tmp_path/'observed-run/results.json').read_text())
    assert result['parameters']['initial_debt'] == pytest.approx(.8287)
    assert result['initial_debt_source']['date'] == '2026-08-01'
    assert result['candidate_comparison_identified'] is False
    assert 'Não calibrados' in (tmp_path/'observed-run/dashboard.html').read_text()
    assert result['reference']['metrics']['indicators'][0]['classification'] == 'observed'
    main(['simulate', '--runs', '8', '--out', str(tmp_path/'default-run'), '--observed', str(path)])
    default_result = json.loads((tmp_path/'default-run/results.json').read_text())
    cfg, _ = load_inputs()
    assert default_result['parameters']['initial_debt'] == cfg['initial_debt']
    assert default_result['reference']['metrics']['indicators'][0]['classification'] == 'hypothetical_not_forecast'


def test_snapshot_tampering_is_rejected(tmp_path):
    from src.observed import fetch_snapshot, load_snapshot
    snapshot = fetch_snapshot(fetcher=lambda url: b'[{"data":"01/08/2026","valor":"1"}]', today=date(2026, 10, 16))
    snapshot['series'][0]['raw_json'] = '[]'
    path = tmp_path / 'observed.json'
    path.write_text(json.dumps(snapshot))
    with pytest.raises(ValueError, match='Hash'):
        load_snapshot(path)


def test_refresh_total_failure_preserves_existing_snapshot(tmp_path, monkeypatch):
    from src import cli
    path = tmp_path / 'observed.json'
    path.write_text('previous snapshot')
    monkeypatch.setattr(cli, 'fetch_snapshot', lambda: {'series': [], 'errors': [{'error': 'offline'}]})
    with pytest.raises(SystemExit) as exc:
        cli.main(['refresh-data', '--observed', str(path)])
    assert exc.value.code == 2
    assert path.read_text() == 'previous snapshot'


def test_annual_accounting_and_frequency_reconcile_with_paths():
    cfg, profiles = load_inputs()
    result = simulate(cfg, profiles, runs=80)
    metrics = result['reference']['metrics']
    for row in metrics['annual']:
        assert row['change_mean_pp'] == pytest.approx(row['stabilizing_primary_mean_pct_gdp'] - row['primary_mean_pct_gdp'])
    values = {m['id']: m['value'] for m in metrics['indicators']}
    paths = result['reference']['trajectories']
    assert values['end_above_100'] == pytest.approx(sum(p['debt_pct_gdp'][-1] > 100 for p in paths) / len(paths) * 100)
    assert values['fiscal_gap'] == pytest.approx(values['annual_debt_change'])
