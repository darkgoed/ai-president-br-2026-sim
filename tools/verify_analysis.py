"""Valida os artefatos reais de uma análise completa, sem rede."""
import csv
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import digest
from src.ranking import analyze_programs, load_dossiers
from src.diagnostics import build_diagnostics


def csv_count(path):
    with path.open(newline='') as f:
        return sum(1 for _ in csv.DictReader(f))


def verify(path, runs=100_000):
    result = json.loads((path/'results.json').read_text())
    ranking = result.get('experimental_ranking')
    profiles = result['profiles']
    trajectories = result['reference']['trajectories']
    assert len(trajectories) == runs == result['counts']['unique_reference_trajectories']
    assert result['counts']['profile_scenario_evaluations'] == runs * len(profiles)
    assert len(profiles) == 12
    assert result['ranking'] is None and not result['candidate_comparison_identified']
    assert all(value is None for p in profiles for value in p['outcomes'].values())
    if ranking:
        assert ranking['counts']['weight_analyses'] == runs
        assert ranking['counts']['candidate_weight_evaluations'] == runs * len(profiles)
        assert len(ranking['candidates']) == len(profiles)
        assert all(c['government_outcome_estimate'] is None for c in ranking['candidates'])
        assert math.isclose(sum(c['first_place_fractional_pct'] for c in ranking['candidates']), 100, abs_tol=1e-9)
        assert ranking == analyze_programs(load_dossiers(), runs=runs, seed=ranking['seed'])
        assert json.loads((path/'ranking.json').read_text()) == ranking
    else:
        for name in ['ranking.json', 'ranking.csv', 'ranking_indicators.csv']:
            assert not (path/name).exists(), 'Ranking obsoleto junto de análise nova: '+name
    assert result['analysis_id'] == digest({'run_id': result['run_id'], 'ranking': ranking,
                                         'history': result.get('history'), 'observed': result.get('observed_snapshot_sha256')})
    assert result['observed_snapshot_sha256'] == digest(result['observed'])
    assert math.isclose(math.fsum(t['debt_pct_gdp'][-1] for t in trajectories) / runs,
                        result['reference']['summary']['mean'], abs_tol=1e-9)
    expected = {'trajectories.csv': runs * (result['reference']['horizon_years']+1),
                'metrics.csv': len(result['reference']['metrics']['indicators']),
                'observed.csv': sum(len(s['observations']) for s in result['observed']['series']),
                'history.csv': sum(len(s['observations']) for s in result['history']['series'])}
    if ranking:
        expected.update({'ranking.csv': len(profiles), 'ranking_indicators.csv': sum(len(c['indicators']) for c in ranking['candidates'])})
    if result.get('diagnostics'):
        diagnostic = result['diagnostics']
        assert diagnostic == build_diagnostics(result, as_of=date.fromisoformat(diagnostic['as_of']))
        assert json.loads((path/'diagnostics.json').read_text()) == diagnostic
        expected['diagnostics.csv'] = len(diagnostic['indicators'])
    for name, n in expected.items():
        assert csv_count(path/name) == n, name
    checks = {'status': 'pass', 'verified_at': datetime.now(timezone.utc).isoformat(),
              'analysis_id': result['analysis_id'], 'macro_counts': result['counts'],
              'ranking_counts': ranking['counts'] if ranking else None, 'csv_rows': expected,
              'ranking_mode': 'legacy' if ranking else 'disabled',
              'official_series': len(result['observed']['series']), 'historical_series': len(result['history']['series']),
              'history_source_errors': result['history']['errors'],
              'diagnostics_reproduced_for_reference_date': bool(result.get('diagnostics')),
              'ranking_reproduced_with_same_seed': True if ranking else None, 'unknown_government_effects_preserved': True}
    (path/'verification.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(checks, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    verify(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results-100k')
