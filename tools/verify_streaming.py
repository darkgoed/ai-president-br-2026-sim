"""Replay independente dos índices e eventos do experimento streaming.
Usa log-razões e odds diretamente dos níveis observados, sem project/annual_blocks.
"""
import hashlib
import json
import math
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import digest
from src.empirical_data import validate_snapshot


def verify(output, batch_size=77777):
    output = Path(output)
    result = json.loads((output/'streaming_results.json').read_text())
    params = result['parameters']
    assert digest(params) == result['run_id']
    snapshot = json.loads((output/'calibration_snapshot.json').read_text())
    validate_snapshot(snapshot)
    assert digest(snapshot) == params['snapshot_sha256']
    for name, sha in params['code_sha256'].items():
        assert hashlib.sha256((ROOT/'src'/name).read_bytes()).hexdigest() == sha
    series = {s['id']: {r['period']: r['value'] for r in s['observations']} for s in snapshot['series']}
    periods = sorted(set.intersection(*(set(s) for s in series.values())))
    raw = np.array([[series[k][p] for k in ['debt', 'unemployment', 'activity', 'inflation']] for p in periods])
    # Reconstrói transformações independentemente a partir dos dados primários.
    transformed = np.column_stack([np.log(raw[:, 0]), np.log(raw[:, 1]/(100-raw[:, 1])),
                                   np.log(raw[:, 2]), np.cumsum(np.log1p(raw[:, 3]/100))])
    # Oráculo por razão direta: também confere a janela e o deslocamento do IPCA.
    blocks = transformed[12:]-transformed[:-12]
    oracle = np.column_stack([np.log(raw[12:, 0]/raw[:-12, 0]),
        np.log((raw[12:, 1]/(100-raw[12:, 1]))/(raw[:-12, 1]/(100-raw[:-12, 1]))),
        np.log(raw[12:, 2]/raw[:-12, 2]),
        [np.sum(np.log1p(raw[i+1:i+13, 3]/100)) for i in range(len(raw)-12)]])
    np.testing.assert_allclose(blocks, oracle, rtol=1e-10, atol=1e-12)
    # Replica a soma cumulativa das mudanças mensais por operações NumPy independentes
    # para manter a mesma definição de fronteiras em ponto flutuante do experimento.
    cumulative_changes = np.vstack([np.zeros(4), np.cumsum(np.diff(transformed, axis=0), axis=0)])
    blocks = cumulative_changes[12:]-cumulative_changes[:-12]
    rng = np.random.Generator(np.random.PCG64(params['seed']))
    counts = dict.fromkeys(result['event_counts'], 0)
    h = hashlib.sha256()
    start = time.monotonic()
    for offset in range(0, params['runs'], batch_size):
        n = min(batch_size, params['runs']-offset)
        indices = rng.integers(0, len(blocks), size=(n, 4), dtype=np.int32)
        h.update(indices.tobytes())
        # Eventos monotônicos nos logaritmos: não usa o código do runner.
        total = blocks[indices].sum(axis=1)
        tolerance = params['event_zero_tolerance_log_space']
        activity_up, unemployment_down = total[:, 2] > tolerance, total[:, 1] < -tolerance
        masks = [total[:, 0] > tolerance, unemployment_down, activity_up, total[:, 3] > tolerance,
                 total[:, 3] > 4*math.log1p(.06)+tolerance, activity_up & unemployment_down]
        for key, mask in zip(counts, masks):
            counts[key] += int(np.count_nonzero(mask))
    assert h.hexdigest() == result['indices_sha256']
    assert counts == result['event_counts'], (counts, result['event_counts'])
    assert result['counts']['sampled_paths'] == params['runs']
    assert result['counts']['sampled_annual_blocks'] == params['runs']*4
    for key, count in counts.items():
        assert result['percentages'][key] == count/params['runs']*100
    assert result['government_ranking'] is None and result['candidate_effects_identified'] is False
    progress = json.loads((output/'progress.json').read_text())
    assert progress['status'] == 'complete' and progress['completed_paths'] == params['runs']
    assert progress['event_counts'] == counts
    report = {'status': 'pass', 'replayed_paths': params['runs'], 'different_batch_size': batch_size,
        'all_event_counts_match': True, 'all_indices_sha256_match': True,
        'snapshot_and_code_hashes_verified': True, 'direct_level_ratio_oracle_checked': True,
        'independent_log_event_implementation': True, 'elapsed_seconds': time.monotonic()-start,
        'run_id': result['run_id'], 'limits': 'Verifica execução, não validade preditiva ou causal do modelo.'}
    (output/'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


if __name__ == '__main__':
    verify(ROOT/sys.argv[1] if len(sys.argv)>1 else ROOT/'results-1b-streaming')
