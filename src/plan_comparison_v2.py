"""Comparação dos PLANOS v2 — ranking exploratório, avaliação assistida por IA (research/plan_comparison_protocol_v2.json).

Lê as avaliações por célula (research/plan_assessment_v2/<id>.json), verifica cada trecho no PDF original e calcula:
nota por dimensão, nota geral 0–100 (pesos iguais 1/7), posições com empate, cobertura, grade de pesos
(passo 0,1 nas 7 dimensões), retirada de uma dimensão por vez, faixas de incerteza (mín/máx) e só temas × só transversais.

Não usa nome, partido, histórico de mandato nem o bilhão de cenários no cálculo (nome/partido só no rótulo de saída).

  .venv/bin/python -m src.plan_comparison_v2 [--out results-plan-comparison-v2] [--no-verify-pdf]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'research/plan_comparison_protocol_v2.json'
FREEZE = ROOT / 'research/plan_comparison_v2_freeze.json'
ASSESS = ROOT / 'research/plan_assessment_v2'
REGISTER = ROOT / 'research/electoral_register.json'
MANIFEST = ROOT / 'research/program_manifest.json'
ARCHIVE = ROOT / '.cache/programs.zip'
STATUSES = {'assessed', 'absent_after_review', 'unavailable', 'not_applicable', 'uncertain'}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(s: str) -> str:
    return ' '.join(s.replace('\u00ad', '').split())


def protocol() -> dict:
    p = json.loads(PROTOCOL.read_text())
    frozen = json.loads(FREEZE.read_text())['sha256']
    if sha256(PROTOCOL) != frozen:
        raise SystemExit('protocolo v2 mudou depois do congelamento: crie v2.x e recalcule tudo')
    return p


def criteria_for(p: dict, dim: dict) -> list[str]:
    key = dim['id'] if dim['kind'] == 'transversal' else 'tematica'
    return [c['id'] for c in p['criteria'][key]]


def universe() -> list[dict]:
    reg = json.loads(REGISTER.read_text())
    return sorted(({'candidate_id': r['SQ_CANDIDATO'], 'ballot_name': r['NM_URNA_CANDIDATO'], 'party': r['SG_PARTIDO']}
                   for r in reg if r['DS_SITUACAO_CANDIDATO_TOT'] == 'DEFERIDO'), key=lambda x: x['candidate_id'])


def load_cells(ids: list[str], p: dict, assess_dir: Path = ASSESS) -> dict:
    """{cid: {(dim, crit): cell}} com validação de contrato (todas as células, estados válidos, evidência)."""
    out = {}
    for cid in ids:
        f = assess_dir / f'{cid}.json'
        if not f.exists():
            raise SystemExit(f'{cid}: avaliação ausente ({f})')
        doc = json.loads(f.read_text())
        cells = {}
        for c in doc['cells']:
            if c['status'] not in STATUSES:
                raise ValueError(f'{cid}: status inválido {c["status"]}')
            if c['status'] in ('assessed', 'uncertain') and c['score'] and not (c['page'] and c['quote']):
                raise ValueError(f'{cid} {c["criterion"]}: nota > 0 sem página/trecho')
            if not c.get('justification'):
                raise ValueError(f'{cid} {c["criterion"]}: sem justificativa')
            if c['status'] == 'uncertain' and not c.get('uncertain_range'):
                raise ValueError(f'{cid} {c["criterion"]}: incerta sem faixa')
            cells[(c['dimension'], c['criterion'])] = c
        for dim in p['dimensions']:
            for crit in criteria_for(p, dim):
                if (dim['id'], crit) not in cells:
                    raise ValueError(f'{cid}: falta célula {dim["id"]}/{crit}')
        out[cid] = cells
    return out


def verify_quotes(cells: dict) -> dict:
    import pymupdf  # noqa: PLC0415
    man = {m['candidate_id']: m for m in json.loads(MANIFEST.read_text())}
    z = zipfile.ZipFile(ARCHIVE)
    checked, failures = 0, []
    for cid, cc in cells.items():
        blob = z.read(man[cid]['archive_member'])
        if hashlib.sha256(blob).hexdigest() != man[cid]['sha256']:
            raise SystemExit(f'{cid}: PDF diverge do manifesto')
        pages = [norm(pg.get_text()) for pg in pymupdf.open(stream=blob, filetype='pdf')]
        for (dim, crit), c in cc.items():
            if c['quote']:
                checked += 1
                if norm(c['quote']) not in pages[c['page'] - 1]:
                    failures.append({'candidate_id': cid, 'dimension': dim, 'criterion': crit, 'page': c['page']})
    return {'quotes_checked': checked, 'failures': failures}


def value(cell: dict, mode: str):
    if cell['status'] in ('unavailable', 'not_applicable') or cell['score'] is None:
        return None
    if cell['status'] == 'uncertain' and mode in ('min', 'max'):
        lo, hi = cell['uncertain_range']
        return lo if mode == 'min' else hi
    return cell['score']


def dimension_scores(cells: dict, p: dict, mode: str = 'point') -> tuple[dict, list[str]]:
    """Nota 0–100 por dimensão. Qualquer None em uma dimensão de qualquer candidatura tira a dimensão de TODOS."""
    dims = [d['id'] for d in p['dimensions']]
    raw = {cid: {} for cid in cells}
    dropped = set()
    for dim in p['dimensions']:
        crits = criteria_for(p, dim)
        for cid, cc in cells.items():
            vals = [value(cc[(dim['id'], k)], mode) for k in crits]
            if any(v is None for v in vals):
                dropped.add(dim['id'])
                raw[cid][dim['id']] = None
            else:
                raw[cid][dim['id']] = sum(vals) / len(vals) / 3 * 100
    common = [d for d in dims if d not in dropped]
    return raw, common


def overall(ds: dict, weights: dict) -> dict:
    tot = sum(weights.values())
    return {cid: sum(weights[d] * v[d] for d in weights) / tot for cid, v in ds.items()}


def ranks(scores: dict) -> dict:
    """1 casa decimal; empates dividem posição (1, 2, 2, 4)."""
    r = {cid: round(s, 1) for cid, s in scores.items()}
    return {cid: 1 + sum(1 for o in r.values() if o > v) for cid, v in r.items()}


def simplex_grid(dims: list[str], step: int = 10):
    for combo in itertools.combinations(range(step + len(dims) - 1), len(dims) - 1):
        parts, prev = [], -1
        for c in combo:
            parts.append(c - prev - 1)
            prev = c
        parts.append(step + len(dims) - 1 - prev - 1)
        yield dict(zip(dims, (x / step for x in parts)))


def run(assess_dir: Path = ASSESS, verify_pdf: bool = True, people: list[dict] | None = None) -> dict:
    p = protocol()
    people = people or universe()
    ids = [x['candidate_id'] for x in people]
    cells = load_cells(ids, p, assess_dir)
    ds, common = dimension_scores(cells, p)
    w = {d: 1 / len(common) for d in common}
    sc = overall(ds, w)
    rk = ranks(sc)
    # sensibilidade (a): grade simplex de pesos
    lead, positions, n = {cid: 0 for cid in ids}, {cid: [] for cid in ids}, 0
    for wv in simplex_grid(common):
        nz = {d: x for d, x in wv.items() if x > 0}
        s = overall(ds, nz)
        r = ranks(s)
        n += 1
        for cid in ids:
            positions[cid].append(r[cid])
            if r[cid] == 1:
                lead[cid] += 1
    # (b) retirada de uma dimensão por vez
    loo = {}
    for d in common:
        rest = [x for x in common if x != d]
        s = overall(ds, {x: 1 / len(rest) for x in rest})
        loo[d] = {'scores': {c: round(v, 1) for c, v in s.items()}, 'ranks': ranks(s)}
    # (c) faixas de incerteza
    band = {}
    for mode in ('min', 'max'):
        dsm, _ = dimension_scores(cells, p, mode)
        s = overall({c: {d: dsm[c][d] for d in common} for c in ids}, w)
        band[mode] = {'scores': {c: round(v, 1) for c, v in s.items()}, 'ranks': ranks(s)}
    # (d) só temas × só transversais
    them = [d['id'] for d in p['dimensions'] if d['kind'] == 'tematica' and d['id'] in common]
    trans = [d['id'] for d in p['dimensions'] if d['kind'] == 'transversal' and d['id'] in common]
    blocks = {}
    for name, sub in (('so_tematicas', them), ('so_transversais', trans)):
        s = overall(ds, {x: 1 / len(sub) for x in sub})
        blocks[name] = {'dimensions': sub, 'scores': {c: round(v, 1) for c, v in s.items()}, 'ranks': ranks(s)}
    coverage = {}
    for cid, cc in cells.items():
        st = {}
        for c in cc.values():
            st[c['status']] = st.get(c['status'], 0) + 1
        pages = json.loads((assess_dir / f'{cid}.json').read_text())['pages_read_in_full']
        coverage[cid] = {'cells': len(cc), 'by_status': st, 'pages_read_in_full': len(pages)}
    label = {x['candidate_id']: x for x in people}
    table = []
    for cid in sorted(ids, key=lambda c: (rk[c], c)):
        pos = positions[cid]
        table.append({'position': rk[cid], 'tied': list(rk.values()).count(rk[cid]) > 1, 'candidate_id': cid,
                      'ballot_name': label[cid]['ballot_name'], 'party': label[cid]['party'],
                      'overall_0_100': round(sc[cid], 1),
                      'dimensions_0_100': {d: round(ds[cid][d], 1) for d in common},
                      'uncertainty_band': [band['min']['scores'][cid], band['max']['scores'][cid]],
                      'position_range_weight_grid': [min(pos), max(pos)],
                      'first_in_weight_vectors': lead[cid],
                      'coverage': coverage[cid]})
    result = {
        'schema_version': 2, 'title': p['label'], 'protocol_id': p['protocol_id'], 'protocol_sha256': sha256(PROTOCOL),
        'review_status': 'ai_single_pass_unreviewed', 'assessor': p['assessment_method']['assessor'],
        'excluded_from_score': p['does_not_measure'],
        'dimensions_common': common, 'dimensions_dropped_for_all': [d['id'] for d in p['dimensions'] if d['id'] not in common],
        'weights': {d: round(v, 6) for d, v in w.items()},
        'ranking': table,
        'sensitivity': {
            'weight_grid': {'vectors': n, 'step': 0.1, 'tie_policy': 'empate na liderança conta para todos os empatados',
                            'first_place_counts': lead,
                            'reading': 'robustez da ordenação a pesos; não é probabilidade de bom governo'},
            'leave_one_dimension_out': loo, 'uncertain_cells_min_max': band, 'blocks': blocks},
        'quote_verification': verify_quotes(cells) if verify_pdf else None,
        'billion_scenarios_used_in_score': False, 'mandate_history_used_in_score': False,
    }
    if result['quote_verification'] and result['quote_verification']['failures']:
        raise ValueError('trechos v2 não encontrados nos PDFs: publicação bloqueada')
    return result


def write(result: dict, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / 'ranking.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    dims = result['dimensions_common']
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator='\n')
    w.writerow(['position', 'tied', 'candidate_id', 'ballot_name', 'party', 'overall_0_100', *dims,
                'band_min', 'band_max', 'grid_pos_min', 'grid_pos_max', 'first_in_weight_vectors', 'review_status'])
    for r in result['ranking']:
        w.writerow([r['position'], r['tied'], r['candidate_id'], r['ballot_name'], r['party'], f'{r["overall_0_100"]:.1f}',
                    *[f'{r["dimensions_0_100"][d]:.1f}' for d in dims], f'{r["uncertainty_band"][0]:.1f}',
                    f'{r["uncertainty_band"][1]:.1f}', *r['position_range_weight_grid'], r['first_in_weight_vectors'],
                    result['review_status']])
    (out / 'ranking.csv').write_text(buf.getvalue())
    rows = []
    for f in sorted(ASSESS.glob('2800*.json')):
        for c in json.loads(f.read_text())['cells']:
            rows.append(c)
    buf = io.StringIO()
    keys = ['candidate_id', 'dimension', 'criterion', 'score', 'status', 'uncertain_range', 'page', 'quote',
            'justification', 'limitation', 'review_status']
    w = csv.DictWriter(buf, fieldnames=keys, lineterminator='\n')
    w.writeheader()
    for c in rows:
        w.writerow({k: json.dumps(c[k], ensure_ascii=False) if isinstance(c[k], list) else c[k] for k in keys})
    (out / 'evidence_matrix.csv').write_text(buf.getvalue())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'results-plan-comparison-v2'))
    ap.add_argument('--no-verify-pdf', action='store_true')
    a = ap.parse_args()
    r = run(verify_pdf=not a.no_verify_pdf)
    write(r, Path(a.out))
    print(r['title'])
    print(f'dimensões comuns: {r["dimensions_common"]} | retiradas: {r["dimensions_dropped_for_all"]}')
    for x in r['ranking']:
        print(f'{x["position"]:>2}{"=" if x["tied"] else " "} {x["overall_0_100"]:5.1f}  [{x["uncertainty_band"][0]:.1f}–'
              f'{x["uncertainty_band"][1]:.1f}]  grade {x["position_range_weight_grid"]}  1º em {x["first_in_weight_vectors"]}  '
              f'{x["ballot_name"]} — {x["party"]}')
    if r['quote_verification']:
        print('trechos verificados:', r['quote_verification']['quotes_checked'], 'falhas:', len(r['quote_verification']['failures']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
