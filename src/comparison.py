"""Comparação política v1: aplica research/measurement_plan_v1.json à matriz de evidências e decide se há ranking.

Regras (do protocolo, não ajustáveis por candidatura):
  * célula sem evidência elegível = None, nunca 0; qualquer None obrigatória bloqueia o ranking geral;
  * notas só a partir de raw_value com evidência primária; esta rotina NÃO inventa raw_value;
  * pesos iguais para todos, sem renormalizar; empates dividem posição; nome/partido/ordem não entram no cálculo;
  * grade de sensibilidade (passo 0.1, cada peso >= 0.1) e leave-one-out só rodam quando o ranking é elegível.

  .venv/bin/python -m src.comparison [--out results-comparison-v1]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'research/measurement_plan_v1.json'
PROTOCOL = ROOT / 'research/comparison_protocol_v1.json'
HISTORY = ROOT / 'research/mandate_history_v1.json'
REGISTER = ROOT / 'research/electoral_register.json'
MANIFEST = ROOT / 'research/program_manifest.json'
STRATEGIES = ROOT / 'data/strategies.json'
EVIDENCE = ROOT / 'research/comparison_evidence_v1.json'  # registros revisados; ausente = nenhuma célula preenchida
DIMENSIONS = ['historical_outcomes', 'verified_execution', 'fiscal_feasibility', 'policy_evidence', 'accountability']


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path, default: Any = None) -> Any:
    return json.loads(path.read_text()) if path.exists() else default


def population(strategies: list, register: list) -> list[dict]:
    reg = {r['SQ_CANDIDATO']: r for r in register}
    out = []
    for s in strategies:
        r = reg.get(s['id'])
        if not r or r['DS_SITUACAO_CANDIDATO_TOT'] != 'DEFERIDO':
            raise ValueError(f'{s["id"]}: perfil fora da regra de população (registro DEFERIDO na data de corte)')
        out.append({'candidate_id': s['id'], 'ballot_name': r['NM_URNA_CANDIDATO'], 'party_at_cutoff': r['SG_PARTIDO']})
    deferred = {r['SQ_CANDIDATO'] for r in register if r['DS_SITUACAO_CANDIDATO_TOT'] == 'DEFERIDO'}
    if deferred != {p['candidate_id'] for p in out}:
        raise ValueError('data/strategies.json não coincide com as candidaturas deferidas do registro')
    return out


def same_role_rule(history: dict, ids: list[str]) -> dict:
    roles = {sid: {r[1] for r in history['participants'][sid]['elected_executive']} for sid in ids}
    common = set.intersection(*roles.values()) if roles else set()
    return {'met': bool(common), 'common_roles': sorted(common),
            'per_candidate': {sid: sorted(v) for sid, v in roles.items()},
            'without_elected_executive': sorted(sid for sid, v in roles.items() if not v)}


def transform(spec: dict, raw):
    if raw is None:
        return None
    t = spec['transformation']
    if t['type'] == 'linear_clip':
        lo, hi = t['raw_at_0'], t['raw_at_100']
        return max(0.0, min(100.0, (raw - lo) / (hi - lo) * 100.0))
    if t['type'] == 'categorical_mean':
        values = [t['map'][c] for c in raw]
        return sum(values) / len(values) if values else None
    raise ValueError(f'transformação desconhecida: {t["type"]}')


def valid_record(rec: dict, required: list[str]) -> bool:
    return (all(k in rec and rec[k] not in (None, '', []) for k in required if k != 'score')
            and rec.get('review_status') == 'double_reviewed')


def matrix(plan: dict, people: list[dict], applicable: dict, evidence: list[dict], required: list[str]) -> list[dict]:
    by_key = {(e['candidate_id'], e['indicator_id']): e for e in evidence if valid_record(e, required)}
    cells = []
    for p in people:
        for ind in plan['indicators']:
            rule = ind['applicability']
            rec = by_key.get((p['candidate_id'], ind['id']))
            if not applicable[rule]['met']:
                status, score = 'not_comparable_for_set', None
            elif rec is None:
                status, score = 'missing_evidence', None
            else:
                status, score = 'scored', transform(ind, rec['raw_value'])
            cells.append({'candidate_id': p['candidate_id'], 'indicator_id': ind['id'], 'dimension': ind['dimension'],
                          'score': score, 'status': status,
                          'evidence_ids': rec['evidence_ids'] if rec else [], 'raw_value': rec['raw_value'] if rec else None})
    return cells


def dimension_scores(cells: list[dict], ids: list[str]) -> dict:
    out = {}
    for sid in ids:
        out[sid] = {}
        for d in DIMENSIONS:
            vals = [c['score'] for c in cells if c['candidate_id'] == sid and c['dimension'] == d]
            out[sid][d] = None if (not vals or any(v is None for v in vals)) else sum(vals) / len(vals)
    return out


def composite(dims: dict, weights: dict) -> dict:
    return {sid: (None if any(v is None for v in d.values()) else sum(weights[k] * d[k] for k in DIMENSIONS))
            for sid, d in dims.items()}


def rank(scores: dict) -> list[dict]:
    """Ranking de competição; empate (1e-9) divide posição; ordem final por nota e depois por ID só para estabilidade."""
    rows = sorted(scores.items(), key=lambda kv: (-round(kv[1], 9), kv[0]))
    out, pos = [], 0
    for i, (sid, s) in enumerate(rows):
        if i == 0 or round(s, 9) != round(rows[i - 1][1], 9):
            pos = i + 1
        out.append({'candidate_id': sid, 'score': s, 'position': pos})
    return out


def weight_grid(step: int = 10, minimum: int = 1) -> list[dict]:
    grid = []
    for combo in itertools.product(range(minimum, step + 1), repeat=len(DIMENSIONS) - 1):
        last = step - sum(combo)
        if last >= minimum:
            grid.append({k: v / step for k, v in zip(DIMENSIONS, (*combo, last))})
    return grid


def sensitivity(dims: dict) -> dict:
    grid = weight_grid()
    first, positions = {sid: 0 for sid in dims}, {sid: [] for sid in dims}
    for w in grid:
        ranking = rank(composite(dims, w))
        for r in ranking:
            positions[r['candidate_id']].append(r['position'])
            if r['position'] == 1:
                first[r['candidate_id']] += 1
    loo = {}
    for d in DIMENSIONS:
        w = {k: (0.0 if k == d else 1 / (len(DIMENSIONS) - 1)) for k in DIMENSIONS}
        loo[d] = rank(composite(dims, w))
    return {'grid_size': len(grid), 'ties_share_first': True,
            'first_place_count': first, 'position_range': {s: [min(p), max(p)] for s, p in positions.items()},
            'leave_one_dimension_out': loo,
            'meaning': 'robustez à grade editorial de pesos; não chance de governar bem nem de vencer'}


def run(evidence: list | None = None) -> dict:
    plan, protocol, history = load(PLAN), load(PROTOCOL), load(HISTORY)
    if evidence is None:
        evidence = load(EVIDENCE, {'records': []})['records']
    people = population(load(STRATEGIES), load(REGISTER))
    ids = [p['candidate_id'] for p in people]
    documented = {d['candidate_id'] for d in load(MANIFEST)}
    applicable = {'same_elected_executive_role_for_all': same_role_rule(history, ids),
                  'program_document': {'met': set(ids) <= documented, 'missing': sorted(set(ids) - documented)}}
    cells = matrix(plan, people, applicable, evidence, protocol['score_record_required_fields'])
    dims = dimension_scores(cells, ids)
    weights = {k: plan['weights'][k] for k in DIMENSIONS}
    scores = composite(dims, weights)
    blockers = []
    if not applicable['same_elected_executive_role_for_all']['met']:
        blockers.append('Nenhum cargo executivo titular foi vencido por todos os 12 participantes; '
                        'resultados históricos e execução verificada não são comparáveis para o conjunto.')
    missing = sorted({c['indicator_id'] for c in cells if c['status'] == 'missing_evidence'})
    if missing:
        blockers.append('Indicadores sem evidência revisada para todos: ' + ', '.join(missing))
    eligible = not blockers and all(v is not None for v in scores.values())
    coverage = {d: sum(1 for c in cells if c['dimension'] == d and c['score'] is not None) for d in DIMENSIONS}
    return {
        'schema_version': 1, 'plan_id': plan['plan_id'], 'protocol_id': protocol['protocol_id'],
        'input_hashes': {p.name: sha256(p) for p in [PLAN, PROTOCOL, HISTORY, REGISTER, MANIFEST, STRATEGIES]}
                        | ({EVIDENCE.name: sha256(EVIDENCE)} if EVIDENCE.exists() else {EVIDENCE.name: None}),
        'participants': people, 'applicability': applicable,
        'cells_total': len(cells), 'cells_scored': sum(c['score'] is not None for c in cells),
        'coverage_by_dimension': coverage, 'cells': cells, 'dimension_scores': dims,
        'overall_ranking_eligible': eligible, 'blockers': blockers,
        'winner': None if not eligible else [r['candidate_id'] for r in rank(scores) if r['position'] == 1],
        'ranking': rank(scores) if eligible else None,
        'sensitivity': sensitivity(dims) if eligible else None,
        'subcomparisons': 'nenhuma publicada: nenhuma célula tem evidência revisada' if not any(coverage.values()) else 'ver cells',
    }


def write(result: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / 'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    with (out / 'matrix.csv').open('w', newline='') as fh:
        w = csv.writer(fh, lineterminator='\n')
        w.writerow(['candidate_id', 'indicator_id', 'dimension', 'status', 'score', 'raw_value', 'evidence_ids'])
        for c in result['cells']:
            w.writerow([c['candidate_id'], c['indicator_id'], c['dimension'], c['status'],
                        '' if c['score'] is None else f'{c["score"]:.6f}', '' if c['raw_value'] is None else c['raw_value'],
                        ';'.join(c['evidence_ids'])])
    roles = result['applicability']['same_elected_executive_role_for_all']
    lines = [f'Comparação {result["protocol_id"]} — plano {result["plan_id"]}',
             f'Participantes: {len(result["participants"])} | células: {result["cells_total"]} | com nota: {result["cells_scored"]}',
             'Cargo executivo titular vencido por todos: ' + (', '.join(roles['common_roles']) or 'nenhum'),
             'Sem cargo executivo titular eleito: ' + str(len(roles['without_elected_executive'])) + ' de ' + str(len(result['participants'])),
             'Ranking geral elegível: ' + ('sim' if result['overall_ranking_eligible'] else 'NÃO'),
             'Vencedor: ' + (', '.join(result['winner']) if result['winner'] else 'nenhum (ranking bloqueado)')]
    lines += ['Bloqueio: ' + b for b in result['blockers']]
    (out / 'report.txt').write_text('\n'.join(lines) + '\n')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'results-comparison-v1'))
    args = ap.parse_args()
    result = run()
    write(result, Path(args.out))
    print((Path(args.out) / 'report.txt').read_text(), end='')
    return 0


if __name__ == '__main__':
    sys.exit(main())
