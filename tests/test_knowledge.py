import json
import sqlite3
import pytest


def test_registry_rejects_candidate_impacts_and_preserves_missing(tmp_path):
    from src.knowledge import Registry
    registry = Registry(tmp_path/'base.sqlite')
    source = registry.source('test.json', b'{"value":null}', url='https://example.gov.br/data')
    registry.add('missing', source, '/value', 'Valor não disponível', payload={'value': None}, value=None)
    with pytest.raises(ValueError, match='impacto'):
        registry.add('observed', source, '/fake', 'Impacto fabricado', payload={}, candidate_id='candidate', value=2, unit='% PIB')
    row = registry.connection.execute('select value,payload_json from records').fetchone()
    assert row[0] is None
    assert json.loads(row[1])['value'] is None
    assert registry.connection.execute('pragma foreign_key_check').fetchall() == []
    registry.close()


def test_registry_search_is_literal_paged_and_keeps_declared_numbers_separate(tmp_path):
    from src.knowledge import Registry
    registry = Registry(tmp_path/'base.sqlite')
    registry.candidate('id', 'Pessoa', 'Partido')
    source = registry.source('program.txt', 'Promete saúde'.encode())
    registry.add('official_declaration', source, '/p1', 'Promessa de saúde',
                 payload={'declared_target': 100, 'causal_impact': None}, candidate_id='id', text='Saúde pública')
    registry.add('observed', source, '/v1', 'Dívida contextual', payload={}, value=80, unit='% PIB', entity='Brasil')
    assert registry.query('saude')['total'] == 1
    assert registry.query(candidate_id='id')['total'] == 1
    assert registry.query(kind='observed')['records'][0]['candidate_id'] is None
    assert registry.query('" OR 1=1 --')['total'] == 0
    assert len(registry.query(limit=1)['records']) == 1
    assert registry.query(limit=1, offset=1)['total'] == 2
    registry.close()


def test_integrated_builder_links_every_candidate_and_keeps_rank_blocked(tmp_path):
    from src.knowledge_build import build_registry
    from src.engine import ROOT
    import hashlib
    import zipfile
    import pymupdf
    root = tmp_path/'root'
    (root/'research/candidates').mkdir(parents=True)
    (root/'.cache').mkdir()
    # Fixture isolada: CI não depende do milhão de trajetórias ou de cache privado.
    with zipfile.ZipFile(root/'.cache/programs.zip', 'w') as archive:
        for path in sorted((ROOT/'research/candidates').glob('*.json'))[:2]:
            dossier = json.loads(path.read_text())
            with pymupdf.open() as pdf:
                pdf.new_page().insert_text((50,50), 'Fixture de teste; nao e evidencia real.')
                raw = pdf.tobytes()
            dossier['program_sha256'] = hashlib.sha256(raw).hexdigest()
            archive.writestr(dossier['program_archive_member'], raw)
            (root/'research/candidates'/path.name).write_text(json.dumps(dossier))
    report = build_registry(root, tmp_path/'integrated')
    assert report['counts']['candidates'] == 2
    assert report['counts']['by_kind']['document_page'] == 2
    assert report['government_ranking'] is None
    assert report['policy']['invented_impacts_allowed'] is False
    assert report['coverage']['known_unequal_excerpt_selection'] is True
    connection = sqlite3.connect(tmp_path/'integrated/evidence.sqlite')
    assert connection.execute("select count(*) from records where candidate_id is not null and kind in ('observed','simulated')").fetchone()[0] == 0
    assert connection.execute('pragma foreign_key_check').fetchall() == []
    assert connection.execute('select count(distinct candidate_id) from records where kind="document_page"').fetchone()[0] == 2
    assert report['simulation'] is None
    assert (tmp_path/'integrated/dashboard.html').exists()
    connection.close()


def test_default_analysis_no_longer_generates_documentary_winner(tmp_path):
    from src.cli import main
    main(['analyze', '--runs', '8', '--out', str(tmp_path)])
    result = json.loads((tmp_path/'results.json').read_text())
    assert 'experimental_ranking' not in result
    assert result['ranking'] is None
    assert result['documentary_ranking_status'] == 'disabled_by_default_unequal_corpus_and_editorial_weights'
