"""Verificação independente de todas as trajetórias empíricas em lotes."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.empirical import prepare_history, annual_blocks, project, rolling_backtest
from src.engine import describe, digest


def verify(output, expected_runs=1_000_000):
    output = Path(output)
    result = json.loads((output/'empirical_results.json').read_text())
    snapshot_path = output/'calibration_snapshot.json'
    snapshot = json.loads(snapshot_path.read_text())
    assert digest(snapshot) == result['parameters']['snapshot_sha256']
    assert digest(result['parameters']) == result['run_id']
    for name, expected in result['artifact_sha256'].items():
        with (output/name).open('rb') as file:
            assert hashlib.file_digest(file, 'sha256').hexdigest() == expected
    prepared = prepare_history(snapshot)
    blocks = annual_blocks(prepared['changes'])
    paths = np.load(output/'paths.npy', mmap_mode='r')
    selections = np.load(output/'block_indices.npy', mmap_mode='r')
    assert paths.shape == (expected_runs, 5, 4)
    assert selections.shape == (expected_runs, 4)
    rng = np.random.Generator(np.random.PCG64(result['parameters']['seed']))
    for offset in range(0, expected_runs, 7777):
        n = min(7777, expected_runs-offset)
        expected = rng.integers(0, len(blocks), size=(n, 4), dtype=np.int32)
        assert np.array_equal(selections[offset:offset+n], expected)
        np.testing.assert_array_equal(paths[offset:offset+n], project(prepared['initial'], blocks, expected))
    for j, metric in enumerate(result['metric_order']):
        assert describe(paths[:, -1, j]) == result['summary'][metric]['final']
        for annual in result['annual']:
            assert describe(paths[:, annual['year'], j]) == annual['metrics'][metric]
    if result.get('schema_version', 1) >= 2:
        assert result['counts']['sampled_paths'] == expected_runs
        distinct = len(np.unique(selections, axis=0))
        assert result['counts']['distinct_block_sequences'] == distinct
        assert result['counts']['repeated_block_sequences'] == expected_runs-distinct
        assert 'unique_paths' not in result['counts']
    else:
        # Legado: este campo contava sorteios; NÃO certifica unicidade.
        assert result['counts']['unique_paths'] == expected_runs
    assert result['counts']['sampled_annual_blocks'] == expected_runs*4
    assert result['government_ranking'] is None and result['candidate_effects_identified'] is False
    backtest = json.loads((output/'backtest.json').read_text())
    assert backtest == rolling_backtest(snapshot, seed=result['parameters']['seed']) == result['backtest']
    evidence = json.loads((output/'evidence.json').read_text())
    assert len(evidence['programs']) == len({p['id'] for p in evidence['programs']}) == 12
    assert sum(p['pages_scanned'] for p in evidence['programs']) == result['evidence_summary']['pages_scanned']
    for report in evidence['fiscal_reports']:
        assert hashlib.sha256(report['raw_json'].encode()).hexdigest() == report['sha256']
        data = json.loads(report['raw_json'])
        assert not data['hasMore'] and data['count'] == len(data['items']) == report['count']
        assert data['items'] == report['items']
    progress = json.loads((output/'progress.json').read_text())
    assert progress['completed_paths'] == expected_runs and progress['status'] == 'complete'
    verified = {'status': 'pass', 'run_id': result['run_id'], 'all_paths_replayed_exactly': expected_runs,
                'seed_reproduced_across_different_batch_sizes': True, 'artifact_hashes_verified': True,
                'backtest_reproduced': True, 'backtest_origins': backtest['counts']['origins'],
                'candidate_effects_invented': False, 'full_programs': len(evidence['programs']),
                'pages_scanned': result['evidence_summary']['pages_scanned'],
                'fiscal_reports': len(evidence['fiscal_reports']), 'source_errors': evidence['errors']}
    (output/'verification.json').write_text(json.dumps(verified, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(verified, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    verify(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results-1m')
