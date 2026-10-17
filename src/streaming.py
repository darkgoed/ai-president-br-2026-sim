"""Contagens Monte Carlo em streaming; sem previsão política ou falsa unicidade."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
import numpy as np
from .empirical import prepare_history, annual_blocks
from .engine import digest

EVENTS = {
    'debt_increase': 'Dívida/PIB final maior que a inicial',
    'unemployment_decrease': 'Desocupação final menor que a inicial',
    'activity_increase': 'IBC-Br final maior que o inicial — não é PIB',
    'prices_increase': 'Nível de preços final maior que o inicial',
    'inflation_annualized_above_6pct': 'Inflação anualizada de quatro anos acima de 6%; limiar descritivo, não meta oficial',
    'activity_up_and_unemployment_down': 'IBC-Br cresce e desocupação diminui simultaneamente'
}


def run_streaming(snapshot, output, runs=1_000_000_000, batch_size=100_000, seed=20261015):
    if type(runs) is not int or not 2 <= runs <= 1_000_000_000:
        raise ValueError('runs deve ser inteiro entre 2 e 1000000000')
    if type(batch_size) is not int or not 1 <= batch_size <= 1_000_000 or type(seed) is not int or seed < 0:
        raise ValueError('Lote/seed inválido')
    prepared = prepare_history(snapshot)
    blocks = annual_blocks(prepared['changes'])
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Destino ocupado; preservar histórico')
    output.mkdir(parents=True, exist_ok=True)
    (output/'calibration_snapshot.json').write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    params = {'runs': runs, 'seed': seed, 'horizon_years': 4, 'snapshot_sha256': digest(snapshot),
              'model': 'joint-moving-block-v2-streaming-events-v2', 'event_zero_tolerance_log_space': 1e-12,
              'code_sha256': {name: hashlib.sha256((Path(__file__).parent/name).read_bytes()).hexdigest()
                              for name in ['streaming.py', 'empirical.py', 'empirical_data.py']}}
    (output/'parameters.json').write_text(json.dumps(params, indent=2)+'\n')
    rng = np.random.Generator(np.random.PCG64(seed))
    counts = {k: 0 for k in EVENTS}
    hasher = hashlib.sha256()
    start = time.monotonic()
    progress = {}
    for offset in range(0, runs, batch_size):
        n = min(batch_size, runs-offset)
        indices = rng.integers(0, len(blocks), size=(n, 4), dtype=np.int32)
        hasher.update(indices.tobytes())
        # Soma na mesma ordem de project; não guarda trajetórias intermediárias.
        cumulative = blocks[indices].sum(axis=1)
        if not np.isfinite(cumulative).all():
            raise ValueError('Projeção não finita')
        tolerance = params['event_zero_tolerance_log_space']
        # Transformações são monotônicas. Zero numérico não deve virar melhora
        # por arredondamento da transformação inversa logit no nível inicial.
        activity_up, unemployed_down = cumulative[:, 2] > tolerance, cumulative[:, 1] < -tolerance
        masks = [cumulative[:, 0] > tolerance, unemployed_down, activity_up, cumulative[:, 3] > tolerance,
                 cumulative[:, 3] > 4*math.log1p(.06)+tolerance, activity_up & unemployed_down]
        for key, mask in zip(EVENTS, masks):
            counts[key] += int(np.count_nonzero(mask))
        done = offset+n
        if done == runs or done % (batch_size*10) == 0:
            progress = {'completed_paths': done, 'requested_paths': runs, 'event_counts': counts,
                        'elapsed_seconds': time.monotonic()-start, 'status': 'running',
                        'rng_state': rng.bit_generator.state, 'prefix_indices_sha256': hasher.hexdigest()}
            temp = output/'progress.next.json'
            temp.write_text(json.dumps(progress, indent=2)+'\n')
            temp.replace(output/'progress.json')
    percentages = {k: count/runs*100 for k, count in counts.items()}
    result = {'schema_version': 1, 'classification': 'conditional_bootstrap_event_frequencies_not_real_world_probabilities',
        'run_id': digest(params), 'parameters': params, 'created_at': datetime.now(timezone.utc).isoformat(),
        'counts': {'sampled_paths': runs, 'sampled_annual_blocks': runs*4,
                   'available_annual_blocks': len(blocks), 'historical_months': len(prepared['periods'])},
        'events': EVENTS, 'event_counts': counts, 'percentages': percentages,
        'numerical_mc_se_percentage_points': {k: math.sqrt((c/runs)*(1-c/runs)/runs)*100 for k,c in counts.items()},
        'indices_sha256': hasher.hexdigest(), 'elapsed_seconds': time.monotonic()-start,
        'history_start': prepared['periods'][0], 'initial_reference': prepared['periods'][-1],
        'government_ranking': None, 'candidate_effects_identified': False,
        'limitations': ['Frequências condicionais às hipóteses e ao histórico, não probabilidades de governos, eleições ou mundo real.',
            'Sorteios com reposição; não são trajetórias únicas nem observações independentes do Brasil.',
            'Não guarda caminhos/quantis; guarda contagens inteiras, seed, hash de todos os índices e snapshot para replay.',
            'Erro Monte Carlo mede apenas ruído de amostragem do modelo; não incerteza causal, viés ou erro preditivo.',
            'Variações transformadas com magnitude até 1e-12 são empates numéricos, não melhora/piora.',
            'Mesmo modelo histórico; o bilhão não melhora o backtest nem cria diferenças identificadas entre candidatos.']}
    (output/'streaming_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    progress['status'] = 'complete'
    (output/'progress.json').write_text(json.dumps(progress, indent=2)+'\n')
    return result
