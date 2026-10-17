"""Ranking documental separado do motor macro e de qualquer efeito de governo.
100 mil vetores de pesos não são 100 mil estudos nem probabilidades políticas.
"""
import json
import re
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def load_dossiers():
    rows = []
    for path in sorted((ROOT/'research/candidates').glob('*.json')):
        rows.append(dict(json.loads(path.read_text()), _source_slug=path.stem))
    return rows


def protocol():
    return json.loads((ROOT/'research/ranking_protocol.json').read_text())


def documentary_indicators(dossier, spec):
    axes = spec['axes']
    commitments = dossier['quantitative_commitments']
    assignment = spec['commitment_axes_by_source'][dossier['_source_slug']]
    if len(commitments) != len(assignment):
        raise ValueError('Catálogo de compromissos mudou: revisar mapeamento de eixos')
    evidence = {e['id']: e for e in dossier['evidence'] if e.get('classification') == 'official_program_proposal' and e.get('page') is not None}
    indicators = []
    for axis in axes:
        proposals = dossier['axes'].get(axis, [])
        reviewed = bool(proposals)
        axis_commitments = [c for c, a in zip(commitments, assignment) if a == axis] if reviewed else []
        ids = {eid for p in proposals for eid in p['evidence_ids']}
        ids.update(eid for c in axis_commitments for eid in c['evidence_ids'])
        if not ids <= evidence.keys():
            raise ValueError('Evidência oficial paginada ausente no eixo ' + axis)
        for criterion in spec['criteria']:
            hits = []
            for c in axis_commitments:
                method = criterion.get('method')
                if method == 'quantitative_commitments':
                    hits.extend(c['evidence_ids'])
                elif method == 'commitment_horizon' and any(c.get(k) is not None for k in ['deadline', 'horizon_years', 'target_year']):
                    hits.extend(c['evidence_ids'])
                elif method == 'declared_aggregate_amount':
                    text = ' '.join(evidence[eid]['quote'] for eid in c['evidence_ids'])
                    if re.search(r'(?:R\$|US\$)\s*[\d.,]+\s*(?:a\s*R\$\s*[\d.,]+\s*)?(?:bilh|trilh)', text, re.I):
                        hits.extend(c['evidence_ids'])
            if criterion.get('pattern'):
                hits.extend(eid for eid in ids if re.search(criterion['pattern'], evidence[eid]['quote'], re.I))
            indicators.append({'axis': axis, 'criterion': criterion['id'], 'label': criterion['label'],
                               'detected': bool(hits) if reviewed else None,
                               'evidence_ids': sorted(set(hits)), 'definition': criterion['definition']})
    return indicators


def analyze_programs(dossiers, runs=100_000, seed=20261015):
    if isinstance(runs, bool) or not isinstance(runs, int) or runs < 2:
        raise ValueError('Análises devem ser inteiro >= 2')
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError('Seed inválida')
    if not dossiers or len({d['official_candidate_id'] for d in dossiers}) != len(dossiers):
        raise ValueError('Dossiers vazios ou IDs duplicados')
    spec = protocol()
    dossiers = sorted(dossiers, key=lambda d: d['official_candidate_id'])
    candidates = []
    for dossier in dossiers:
        indicators = documentary_indicators(dossier, spec)
        lookup = {e['id']: e for e in dossier['evidence']}
        referenced = sorted({eid for i in indicators for eid in i['evidence_ids']})
        candidates.append({'id': dossier['official_candidate_id'], 'name': dossier['supplied_name'],
                           'party': dossier['verified_party'], 'source': f'research/candidates/{dossier["_source_slug"]}.json',
                           'program_url': dossier['program_url'], 'archive_member': dossier['program_archive_member'],
                           'program_sha256': dossier['program_sha256'], 'indicators': indicators,
                           'evidence': [lookup[eid] for eid in referenced], 'government_outcome_estimate': None})
    common = [a for a in spec['axes'] if all(any(i['axis'] == a and i['detected'] is not None for i in c['indicators']) for c in candidates)]
    if not common:
        raise ValueError('Sem eixos revisados comuns; ranking bloqueado')
    matrix = np.array([[[int(next(i['detected'] for i in c['indicators'] if i['axis'] == a and i['criterion'] == k['id']))
                         for k in spec['criteria']] for a in common] for c in candidates], dtype=float)
    base = matrix.mean(axis=(1, 2)) * 100
    rng = np.random.Generator(np.random.PCG64(np.random.SeedSequence([seed, 714])))
    scores = np.empty((runs, len(candidates)))
    for offset in range(0, runs, 4096):
        size = min(4096, runs - offset)
        axis_weights = rng.dirichlet(np.ones(len(common)), size)
        criteria_weights = rng.dirichlet(np.ones(len(spec['criteria'])), size)
        scores[offset:offset+size] = np.einsum('na,nk,cak->nc', axis_weights, criteria_weights, matrix) * 100
    tied_first = np.isclose(scores, scores.max(axis=1, keepdims=True), rtol=0, atol=1e-10)
    fractional = tied_first / tied_first.sum(axis=1, keepdims=True)
    for j, candidate in enumerate(candidates):
        ranks = 1 + (scores > scores[:, [j]] + 1e-10).sum(axis=1)
        candidate.update(score_equal_weights=float(base[j]),
                         position_equal_weights=int(1 + np.sum(base > base[j] + 1e-10)),
                         score_q025=float(np.quantile(scores[:, j], .025)),
                         score_q975=float(np.quantile(scores[:, j], .975)),
                         first_place_fractional_pct=float(fractional[:, j].mean() * 100),
                         best_rank=int(ranks.min()), worst_rank=int(ranks.max()),
                         mean_rank=float(ranks.mean()),
                         rank_counts={str(i): int((ranks == i).sum()) for i in range(1, len(candidates)+1)},
                         axes={axis: float(matrix[j, a].mean() * 100) for a, axis in enumerate(common)})
    candidates.sort(key=lambda c: (-c['score_equal_weights'], c['id']))
    return {'schema_version': 1, 'classification': spec['classification'], 'title': spec['title'],
            'seed': seed, 'protocol': spec, 'common_axes': common, 'candidates': candidates,
            'counts': {'weight_analyses': runs, 'candidate_weight_evaluations': runs * len(candidates),
                       'indicators_per_candidate': len(spec['axes']) * len(spec['criteria']),
                       'identified_government_effects': 0},
            'interpretation': 'Nota de especificação detectada na seleção auditada. Não mede melhor governo; frequências apenas variam pesos editoriais.'}
