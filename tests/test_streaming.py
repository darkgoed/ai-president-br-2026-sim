import hashlib
import numpy as np
import pytest
from src.empirical import prepare_history, annual_blocks, project
from src.engine import ROOT
import runpy


def test_streamed_events_match_materialized_paths_and_batch_sizes(tmp_path):
    from src.streaming import run_streaming
    snapshot = runpy.run_path(str(ROOT/'tests/test_empirical.py'))['monthly_fixture']()
    prepared = prepare_history(snapshot)
    indices = np.random.Generator(np.random.PCG64(7)).integers(0, len(annual_blocks(prepared['changes'])), size=(1003, 4), dtype=np.int32)
    paths = project(prepared['initial'], annual_blocks(prepared['changes']), indices)
    a = run_streaming(snapshot, tmp_path/'a', runs=1003, batch_size=128, seed=7)
    b = run_streaming(snapshot, tmp_path/'b', runs=1003, batch_size=223, seed=7)
    assert a['counts']['sampled_paths'] == 1003
    assert a['event_counts'] == b['event_counts']
    assert a['indices_sha256'] == b['indices_sha256'] == hashlib.sha256(indices.tobytes()).hexdigest()
    assert a['event_counts']['debt_increase'] == int(np.sum(paths[:, -1, 0] > paths[:, 0, 0]))
    assert a['event_counts']['unemployment_decrease'] == int(np.sum(paths[:, -1, 1] < paths[:, 0, 1]-1e-10))
    assert a['event_counts']['activity_increase'] == int(np.sum(paths[:, -1, 2] > paths[:, 0, 2]))
    for key in a['event_counts']:
        assert a['percentages'][key] == pytest.approx(a['event_counts'][key]/1003*100)
    assert a['government_ranking'] is None
    with pytest.raises(ValueError):
        run_streaming(snapshot, tmp_path/'a', runs=1003)


def test_numerical_roundoff_is_not_reported_as_unemployment_improvement(tmp_path):
    from src.streaming import run_streaming
    snapshot = runpy.run_path(str(ROOT/'tests/test_empirical.py'))['monthly_fixture']()
    result = run_streaming(snapshot, tmp_path/'constant', runs=20, seed=1)
    assert result['event_counts']['unemployment_decrease'] == 0
    assert result['parameters']['event_zero_tolerance_log_space'] == 1e-12


def test_independent_streaming_verifier_replays_entire_small_experiment(tmp_path):
    from src.streaming import run_streaming
    snapshot = runpy.run_path(str(ROOT/'tests/test_empirical.py'))['monthly_fixture']()
    run_streaming(snapshot, tmp_path/'run', runs=1003, batch_size=120, seed=9)
    verify = runpy.run_path(str(ROOT/'tools/verify_streaming.py'))['verify']
    report = verify(tmp_path/'run', batch_size=177)
    assert report['replayed_paths'] == 1003
    assert report['all_event_counts_match']
