import copy
import csv
import json
import shutil
from pathlib import Path

import pytest

from src import plan_comparison_v2 as V

OUT = V.ROOT / 'results-plan-comparison-v2'


@pytest.fixture(scope='module')
def base():
    return V.run(verify_pdf=False)


def _clone(tmp_path: Path, edit=None) -> Path:
    d = tmp_path / 'assess'
    shutil.copytree(V.ASSESS, d)
    if edit:
        edit(d)
    return d


def test_protocol_frozen():
    assert V.sha256(V.PROTOCOL) == json.loads(V.FREEZE.read_text())['sha256']


def test_quote_mismatch_blocks_output(monkeypatch):
    monkeypatch.setattr(V, 'verify_quotes', lambda cells: {
        'quotes_checked': 220, 'failures': [{'candidate_id': 'invalid-quote'}],
    })
    with pytest.raises(ValueError, match='publicação bloqueada'):
        V.run(verify_pdf=True)


def test_names_parties_order_do_not_change_scores(base):
    people = V.universe()
    shuffled = [dict(p, ballot_name=f'X{i}', party=f'P{i}') for i, p in enumerate(reversed(people))]
    other = V.run(verify_pdf=False, people=shuffled)
    a = {r['candidate_id']: (r['overall_0_100'], r['dimensions_0_100'], r['position']) for r in base['ranking']}
    b = {r['candidate_id']: (r['overall_0_100'], r['dimensions_0_100'], r['position']) for r in other['ranking']}
    assert a == b


def test_identical_assessments_tie(tmp_path):
    ids = [p['candidate_id'] for p in V.universe()]
    src, dst = ids[0], ids[1]

    def edit(d):
        doc = json.loads((d / f'{src}.json').read_text())
        doc['candidate_id'] = dst
        for c in doc['cells']:
            c['candidate_id'] = dst
        (d / f'{dst}.json').write_text(json.dumps(doc, ensure_ascii=False))
    r = V.run(assess_dir=_clone(tmp_path, edit), verify_pdf=False)
    rows = {x['candidate_id']: x for x in r['ranking']}
    assert rows[src]['overall_0_100'] == rows[dst]['overall_0_100']
    assert rows[src]['position'] == rows[dst]['position'] and rows[src]['tied']


def test_gap_is_not_zero_and_drops_dimension_for_all(tmp_path):
    cid = V.universe()[0]['candidate_id']

    def edit(d):
        doc = json.loads((d / f'{cid}.json').read_text())
        for c in doc['cells']:
            if c['dimension'] == 'ambiente' and c['criterion'].startswith('T1'):
                c.update(status='unavailable', score=None)
        (d / f'{cid}.json').write_text(json.dumps(doc, ensure_ascii=False))
    r = V.run(assess_dir=_clone(tmp_path, edit), verify_pdf=False)
    assert r['dimensions_dropped_for_all'] == ['ambiente']
    assert all('ambiente' not in x['dimensions_0_100'] for x in r['ranking'])
    assert abs(sum(r['weights'].values()) - 1) < 1e-5 and len(set(r['weights'].values())) == 1


def test_same_weights_and_denominators(base):
    assert len(set(base['weights'].values())) == 1
    assert {len(x['dimensions_0_100']) for x in base['ranking']} == {7}
    assert {x['coverage']['cells'] for x in base['ranking']} == {22}


def test_every_positive_score_has_traceable_evidence():
    for f in V.ASSESS.glob('2800*.json'):
        for c in json.loads(f.read_text())['cells']:
            assert c['justification']
            if c['score']:
                assert c['page'] and c['quote'], (f.name, c['criterion'])
            if c['status'] == 'uncertain':
                lo, hi = c['uncertain_range']
                assert lo <= c['score'] <= hi


def test_quotes_exist_in_pdf_pages():
    if not V.ARCHIVE.exists():
        pytest.skip('.cache/programs.zip ausente')
    cells = V.load_cells([p['candidate_id'] for p in V.universe()], V.protocol())
    v = V.verify_quotes(cells)
    assert v['quotes_checked'] >= 200 and v['failures'] == []


def test_history_and_billion_not_in_score():
    src = Path(V.__file__).read_text()
    for forbidden in ('mandate_history_v1.json', 'streaming_results', 'results-1b', 'first_round', 'government_history'):
        assert forbidden not in src
    r = V.run(verify_pdf=False)
    assert r['billion_scenarios_used_in_score'] is False and r['mandate_history_used_in_score'] is False


def test_outputs_agree_and_reproduce(base):
    published = json.loads((OUT / 'ranking.json').read_text())
    strip = lambda r: {k: v for k, v in r.items() if k != 'quote_verification'}  # noqa: E731
    assert strip(published) == strip(base)
    rows = list(csv.DictReader((OUT / 'ranking.csv').open()))
    for row, rec in zip(rows, published['ranking']):
        assert row['candidate_id'] == rec['candidate_id'] and float(row['overall_0_100']) == rec['overall_0_100']
        assert int(row['position']) == rec['position']
    report = (V.ROOT / 'research/RELATORIO-COMPARACAO-PLANOS-V2.md').read_text()
    for rec in published['ranking']:
        assert f'{rec["overall_0_100"]:.1f}'.replace('.', ',') in report


def test_overall_is_equal_weight_mean(base):
    for x in base['ranking']:
        m = sum(x['dimensions_0_100'].values()) / 7
        assert abs(m - x['overall_0_100']) < 0.11


def test_ranks_share_ties():
    assert V.ranks({'a': 50.04, 'b': 49.96, 'c': 40}) == {'a': 1, 'b': 1, 'c': 3}


def test_weight_grid_size():
    assert sum(1 for _ in V.simplex_grid(list('abcdefg'))) == 8008


def test_contract_rejects_missing_evidence(tmp_path):
    cid = V.universe()[0]['candidate_id']

    def edit(d):
        doc = json.loads((d / f'{cid}.json').read_text())
        bad = copy.deepcopy(doc)
        for c in bad['cells']:
            if c['score']:
                c['quote'] = None
                break
        (d / f'{cid}.json').write_text(json.dumps(bad, ensure_ascii=False))
    with pytest.raises(ValueError):
        V.run(assess_dir=_clone(tmp_path, edit), verify_pdf=False)
