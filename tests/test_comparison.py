import copy
import json

from src import comparison as C

PLAN = json.loads(C.PLAN.read_text())
IDS = [s['id'] for s in json.loads(C.STRATEGIES.read_text())]


def full_evidence(value_for=lambda sid, ind: 0.5):
    recs = []
    for sid in IDS:
        for ind in PLAN['indicators']:
            raw = ['aprovacao'] if ind['transformation']['type'] == 'categorical_mean' else value_for(sid, ind)
            recs.append({'candidate_id': sid, 'indicator_id': ind['id'], 'raw_value': raw, 'score': None,
                         'scale_definition_id': ind['id'], 'evidence_ids': [f'ev-{sid}-{ind["id"]}'],
                         'calculation': 'teste', 'uncertainty': 'teste', 'review_status': 'double_reviewed'})
    return recs


def all_applicable(monkeypatch):
    real = C.same_role_rule
    monkeypatch.setattr(C, 'same_role_rule', lambda h, ids: dict(real(h, ids), met=True, common_roles=['TESTE']))


def test_current_data_refuses_winner():
    r = C.run()
    assert r['overall_ranking_eligible'] is False and r['winner'] is None and r['ranking'] is None
    assert r['cells_scored'] == 0 and r['cells_total'] == len(IDS) * len(PLAN['indicators'])
    assert all(c['score'] is None for c in r['cells'])  # faltante nunca vira zero


def test_no_common_executive_role_in_official_history():
    roles = C.run()['applicability']['same_elected_executive_role_for_all']
    assert roles['met'] is False and roles['common_roles'] == []
    assert len(roles['without_elected_executive']) >= 1


def test_identical_evidence_ties_everyone(monkeypatch):
    all_applicable(monkeypatch)
    r = C.run(full_evidence())
    assert r['overall_ranking_eligible'] is True
    assert {x['position'] for x in r['ranking']} == {1} and sorted(r['winner']) == sorted(IDS)


def test_single_missing_cell_blocks_ranking(monkeypatch):
    all_applicable(monkeypatch)
    ev = full_evidence()[1:]
    r = C.run(ev)
    assert r['overall_ranking_eligible'] is False and r['winner'] is None
    assert any(c['status'] == 'missing_evidence' and c['score'] is None for c in r['cells'])


def test_unreviewed_record_is_ignored(monkeypatch):
    all_applicable(monkeypatch)
    ev = full_evidence()
    ev[0]['review_status'] = 'llm_suggested'
    assert C.run(ev)['overall_ranking_eligible'] is False


def test_scores_depend_on_id_not_name_party_or_order(monkeypatch):
    all_applicable(monkeypatch)
    ev = full_evidence(lambda sid, ind: (int(sid[-3:]) % 7) / 7)
    base = {x['candidate_id']: x['score'] for x in C.run(ev)['ranking']}
    strategies = json.loads(C.STRATEGIES.read_text())
    shuffled = list(reversed(copy.deepcopy(strategies)))
    for s in shuffled:
        s['name'], s['party'] = 'X', 'Y'
    monkeypatch.setattr(C, 'load', lambda p, d=None: shuffled if p == C.STRATEGIES else (
        json.loads(p.read_text()) if p.exists() else d))
    again = {x['candidate_id']: x['score'] for x in C.run(list(reversed(ev)))['ranking']}
    assert base == again


def test_weight_grid_contract():
    grid = C.weight_grid()
    assert len(grid) == 126
    assert all(abs(sum(w.values()) - 1) < 1e-9 and min(w.values()) >= 0.1 - 1e-9 for w in grid)


def test_sensitivity_same_vectors_for_all(monkeypatch):
    all_applicable(monkeypatch)
    r = C.run(full_evidence(lambda sid, ind: (int(sid[-2:]) % 5) / 5))
    s = r['sensitivity']
    assert s['grid_size'] == 126
    assert all(len(v) == 2 for v in s['position_range'].values())
    assert sum(s['first_place_count'].values()) >= 126


def test_transform_clips_and_handles_direction():
    ind = next(i for i in PLAN['indicators'] if i['id'] == 'HO1_desocupacao_relativa')
    assert C.transform(ind, -3.0) == 100 and C.transform(ind, 3.0) == 0 and C.transform(ind, 99) == 0
    assert C.transform(ind, None) is None


def test_billion_and_legacy_rankings_are_not_inputs():
    names = set(C.run()['input_hashes'])
    assert not any('1b' in n or 'streaming' in n or 'ranking_protocol' in n or 'candidates' in n for n in names)


def test_mandate_history_has_no_personal_identifiers():
    text = C.HISTORY.read_text()
    for field in ['NR_TITULO_ELEITORAL', 'NR_CPF', 'DS_EMAIL', 'DT_NASCIMENTO']:
        assert field not in text


def test_population_matches_deferred_register_and_flags_others():
    reg = json.loads(C.REGISTER.read_text())
    others = {r['SQ_CANDIDATO'] for r in reg} - set(IDS)
    assert others and all(r['DS_SITUACAO_CANDIDATO_TOT'] != 'DEFERIDO' for r in reg if r['SQ_CANDIDATO'] in others)


def test_frozen_hashes_match():
    frozen = json.loads((C.ROOT / 'research/comparison_v1_freeze.json').read_text())
    for name, digest in frozen['sha256'].items():
        assert C.sha256(C.ROOT / name) == digest, name
