"""Audita hashes, referências e separação de evidências da base integrada."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.knowledge import canonical, fingerprint


def verify(output):
    output = Path(output)
    manifest = json.loads((output/'manifest.json').read_text())
    db = sqlite3.connect((output/'evidence.sqlite').resolve().as_uri()+'?mode=ro', uri=True)
    try:
        assert db.execute('pragma integrity_check').fetchone()[0] == 'ok'
        assert not db.execute('pragma foreign_key_check').fetchall()
        for sid, path, sha, content in db.execute('select id,path,sha256,content_text from sources'):
            assert hashlib.sha256(content.encode()).hexdigest() == sha, path
            assert fingerprint({'path': path, 'sha256': sha}) == sid
        records = db.execute('select count(*) from records').fetchone()[0]
        assert records == manifest['counts']['records']
        assert records == db.execute('select count(*) from search').fetchone()[0]
        assert not db.execute("select id from records where candidate_id is not null and kind in ('observed','derived_observation','simulated')").fetchall()
        for rid, sid, pointer, payload in db.execute('select id,source_id,pointer,payload_json from records'):
            assert fingerprint({'source': sid, 'pointer': pointer}) == rid
            assert canonical(json.loads(payload)) == payload
        assert manifest['government_ranking'] is None
        assert manifest['policy']['invented_impacts_allowed'] is False
        assert manifest['bundle_id'] == fingerprint({'inputs': manifest['inputs'], 'policy': manifest['policy'], 'counts': manifest['counts']})
        for item in manifest['inputs']:
            raw = (ROOT/item['path']).read_bytes()
            assert len(raw) == item['bytes']
            assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['path']
        for name, sha in manifest.get('artifact_sha256', {}).items():
            assert hashlib.sha256((output/name).read_bytes()).hexdigest() == sha, name
        if manifest.get('publication_gate'):
            from src.public_validation import validate_dataset, validate_embedded_fiscal, validate_embedded_social
            from src.observed import load_snapshot
            from src.analysis_suite import build_analysis
            load_snapshot(ROOT/'data/observed.json')
            catalog = json.loads((ROOT/manifest['catalog_file']).read_text())
            for dataset in catalog['datasets']:
                validate_dataset(ROOT, dataset)
            expanded = json.loads((ROOT/'research/expanded_evidence.json').read_text())
            for report in expanded['fiscal_reports']:
                validate_embedded_fiscal(report)
            for series in expanded['social_indicators']:
                validate_embedded_social(series)
            expected_candidates = {p['id'] for p in json.loads((ROOT/'data/strategies.json').read_text())}
            assert {r[0] for r in db.execute('select id from candidates')} == expected_candidates
            with tempfile.TemporaryDirectory(prefix='verify-analysis-', dir=os.environ['TMPDIR']) as temp:
                regenerated = build_analysis(ROOT, Path(temp)/'analysis', manifest['simulation_directory'], manifest['catalog_file'])
                assert regenerated == json.loads((output/'analysis/analysis.json').read_text())
                for name in ['observed_comparisons.csv', 'simulated_metrics.csv', 'backtest_scores.csv', 'RELATORIO.md']:
                    assert (Path(temp)/'analysis'/name).read_bytes() == (output/'analysis'/name).read_bytes(), name
        for filename, table in [('records.jsonl', 'records'), ('sources.jsonl', 'sources')]:
            cursor = db.execute('select * from '+table+' order by id')
            keys = [x[0] for x in cursor.description]
            with (output/filename).open() as file:
                for row in cursor:
                    assert json.loads(next(file)) == dict(zip(keys, row))
                assert not file.read()
        result = {'status': 'pass', 'records': records, 'source_hashes_verified': True,
                  'normalized_responses_revalidated': bool(manifest.get('publication_gate')),
                  'derived_metrics_and_multihorizon_backtests_reproduced': bool(manifest.get('publication_gate')),
                  'input_hashes_verified': True, 'jsonl_matches_sqlite': True,
                  'candidate_observed_or_simulated_impacts': 0,
                  'limits': 'Integridade técnica não verifica a verdade das declarações nem prova ausência de viés.'}
        (output/'verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        db.close()


if __name__ == '__main__':
    verify(sys.argv[1] if len(sys.argv) > 1 else ROOT/'results-integrated')
