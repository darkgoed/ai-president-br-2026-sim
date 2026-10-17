"""Registro único de evidências tipadas. Nenhum impacto/nota de governo."""
import hashlib
import json
import math
from pathlib import Path
import sqlite3

KINDS = {'observed', 'official_declaration', 'official_identity', 'automated_mention',
         'document_page', 'contextual_analysis', 'derived_observation', 'missing', 'simulated', 'methodology', 'legacy_deprecated'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


class Registry:
    def __init__(self, path):
        self.path = Path(path)
        if self.path.exists():
            raise ValueError('Base existente: use novo destino, sem sobrescrever histórico')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute('pragma foreign_keys=ON')
        self.connection.executescript('''
            CREATE TABLE candidates(id TEXT PRIMARY KEY, name TEXT NOT NULL, party TEXT NOT NULL);
            CREATE TABLE sources(id TEXT PRIMARY KEY, path TEXT NOT NULL, sha256 TEXT NOT NULL,
                url TEXT, retrieved_at TEXT, verification TEXT NOT NULL, content_text TEXT NOT NULL);
            CREATE TABLE records(id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                source_id TEXT NOT NULL REFERENCES sources(id), pointer TEXT NOT NULL,
                candidate_id TEXT REFERENCES candidates(id), entity TEXT, label TEXT NOT NULL,
                period TEXT, unit TEXT, value REAL, text TEXT NOT NULL, payload_json TEXT NOT NULL,
                UNIQUE(source_id,pointer));
            CREATE INDEX records_candidate ON records(candidate_id);
            CREATE INDEX records_kind ON records(kind);
            CREATE VIRTUAL TABLE search USING fts5(record_id UNINDEXED,label,text,tokenize='unicode61 remove_diacritics 2');
        ''')

    def candidate(self, candidate_id, name, party):
        self.connection.execute('insert into candidates values(?,?,?)', (candidate_id, name, party))

    @classmethod
    def open_readonly(cls, path):
        registry = cls.__new__(cls)
        registry.path = Path(path).resolve()
        if not registry.path.is_file():
            raise ValueError('Base integrada não encontrada')
        registry.connection = sqlite3.connect(registry.path.as_uri()+'?mode=ro', uri=True)
        return registry

    def source(self, path, raw, url=None, retrieved_at=None, verification='local_snapshot_hash'):
        sha = hashlib.sha256(raw).hexdigest()
        source_id = fingerprint({'path': str(path), 'sha256': sha})
        self.connection.execute('insert or ignore into sources values(?,?,?,?,?,?,?)',
            (source_id, str(path), sha, url, retrieved_at, verification, raw.decode('utf-8', errors='replace')))
        return source_id

    def add(self, kind, source_id, pointer, label, payload, candidate_id=None,
            entity=None, period=None, unit=None, value=None, text=''):
        if kind not in KINDS:
            raise ValueError('Classificação desconhecida')
        if candidate_id is not None and kind in {'observed', 'derived_observation', 'simulated'}:
            raise ValueError('Indicador contextual não pode virar impacto observado/simulado de candidato')
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
            raise ValueError('Valor numérico não finito ou inválido')
        if value is not None and unit is None:
            raise ValueError('Observação numérica exige unidade explícita, não inferida')
        payload_json = canonical(payload)
        record_id = fingerprint({'source': source_id, 'pointer': pointer})
        # Não deduplicar fontes diferentes como se fossem observações independentes.
        self.connection.execute('insert into records values(?,?,?,?,?,?,?,?,?,?,?,?)',
            (record_id, kind, source_id, pointer, candidate_id, entity, label,
             str(period) if period is not None else None, unit, value, text, payload_json))
        self.connection.execute('insert into search values(?,?,?)', (record_id, label, text+' '+payload_json))
        return record_id

    def query(self, term='', candidate_id=None, kind=None, limit=50, offset=0):
        if type(limit) is not int or not 1 <= limit <= 100 or type(offset) is not int or offset < 0:
            raise ValueError('Paginação inválida')
        clauses, params = [], []
        if term:
            # Pesquisar literal, sem aceitar operadores FTS ou SQL do usuário.
            clauses.append('r.id in (select record_id from search where search match ?)')
            params.append('"'+term.replace('"', '""')+'"')
        if candidate_id:
            clauses.append('r.candidate_id=?')
            params.append(candidate_id)
        if kind:
            if kind not in KINDS:
                raise ValueError('Filtro desconhecido')
            clauses.append('r.kind=?')
            params.append(kind)
        where = (' where '+' and '.join(clauses)) if clauses else ''
        total = self.connection.execute('select count(*) from records r'+where, params).fetchone()[0]
        cursor = self.connection.execute('''select r.id,r.kind,r.candidate_id,r.entity,r.label,r.period,r.unit,r.value,
            r.text,r.payload_json,s.path,s.url,s.sha256,r.pointer from records r join sources s on s.id=r.source_id'''
            +where+' order by r.id limit ? offset ?', params+[limit,offset])
        keys = [d[0] for d in cursor.description]
        return {'total': total, 'offset': offset, 'limit': limit,
                'records': [dict(zip(keys, row)) for row in cursor.fetchall()]}

    def counts(self):
        return {'records': self.connection.execute('select count(*) from records').fetchone()[0],
                'sources': self.connection.execute('select count(*) from sources').fetchone()[0],
                'candidates': self.connection.execute('select count(*) from candidates').fetchone()[0],
                'by_kind': dict(self.connection.execute('select kind,count(*) from records group by kind'))}

    def close(self):
        self.connection.commit()
        self.connection.close()
