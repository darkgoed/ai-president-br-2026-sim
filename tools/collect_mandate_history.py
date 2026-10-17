"""Histórico de candidaturas/eleições dos 12 perfis em TODOS os arquivos oficiais consulta_cand do TSE (1994–2024).

Mesma regra para todos os participantes, fixada antes da coleta:
  * universo de arquivos: consulta_cand_<ano>.zip, anos pares 1994–2024 (gerais e municipais), CDN oficial do TSE;
  * chave primária: número do título eleitoral do registro de 2026 (dado pessoal: usado só em memória, nunca gravado);
  * chave secundária, só quando o título não é divulgado na linha histórica: nome civil exato + data de nascimento;
  * resultado: cargo, ano, UF/UE, situação de totalização (ex.: ELEITO) e SQ_CANDIDATO público de cada linha.

"Eleito" no TSE prova resultado de totalização, não exercício integral do mandato, renúncia, licença ou desempenho.

  .venv/bin/python tools/collect_mandate_history.py [--cache .cache/tse-consulta-cand]
Saída: research/mandate_history_v1.json (sem título eleitoral, CPF, e-mail ou outros dados pessoais).
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import unicodedata
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
YEARS = list(range(1994, 2025, 2))
URL = 'https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_{year}.zip'
REGISTER_2026 = URL.format(year=2026)
VOTES_URL = 'https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_candidato_munzona/votacao_candidato_munzona_{year}.zip'
ELECTED = {'ELEITO', 'ELEITO POR QP', 'ELEITO POR MÉDIA', 'MÉDIA'}
EXECUTIVE = {'PRESIDENTE', 'GOVERNADOR', 'PREFEITO'}
VICE_EXECUTIVE = {'VICE-PRESIDENTE', 'VICE-GOVERNADOR', 'VICE-PREFEITO'}
KEEP = ['ANO_ELEICAO', 'NR_TURNO', 'DS_ELEICAO', 'SG_UF', 'SG_UE', 'NM_UE', 'NR_CANDIDATO', 'DS_CARGO', 'SQ_CANDIDATO', 'NM_URNA_CANDIDATO',
        'SG_PARTIDO', 'DS_SITUACAO_CANDIDATURA', 'DS_SIT_TOT_TURNO']
csv.field_size_limit(10_000_000)


def norm_name(name: str) -> str:
    """Maiúsculas, sem acento e espaço simples: arquivos antigos do TSE gravam nomes sem acentuação."""
    s = unicodedata.normalize('NFKD', (name or '').strip().upper())
    return ' '.join(''.join(c for c in s if not unicodedata.combining(c)).split())


def download(url: str, target: Path) -> dict:
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix('.part')
        with urlopen(Request(url, headers={'User-Agent': 'PresidenteIAResearch/1.0'}), timeout=120) as response, tmp.open('wb') as fh:
            while chunk := response.read(1 << 20):
                fh.write(chunk)
        tmp.rename(target)
    digest = hashlib.sha256()
    with target.open('rb') as fh:
        while chunk := fh.read(1 << 20):
            digest.update(chunk)
    return {'url': url, 'sha256': digest.hexdigest(), 'bytes': target.stat().st_size,
            'checked_at': datetime.now(timezone.utc).isoformat()}


def rows(path: Path, prefer_national: bool = True):
    """Linhas dos CSVs do zip. Usa o arquivo consolidado *_BRASIL.csv quando existe, para não duplicar linhas."""
    with zipfile.ZipFile(path) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        national = [n for n in names if n.upper().endswith('_BRASIL.CSV')]
        chosen = national if (prefer_national and national) else names
        for name in chosen:
            with zf.open(name) as raw:
                for row in csv.DictReader(io.TextIOWrapper(raw, encoding='latin-1', newline=''), delimiter=';'):
                    yield name, row


def participants(cache: Path) -> tuple[dict, dict]:
    ids = {s['id'] for s in json.loads((ROOT / 'data/strategies.json').read_text())}
    src = download(REGISTER_2026, cache / 'consulta_cand_2026.zip')
    found = {}
    for _, row in rows(cache / 'consulta_cand_2026.zip'):
        if row['DS_CARGO'] == 'PRESIDENTE' and row['SQ_CANDIDATO'] in ids:
            found[row['SQ_CANDIDATO']] = {'title': row['NR_TITULO_ELEITORAL_CANDIDATO'].strip().lstrip('0'),
                                          'name': norm_name(row['NM_CANDIDATO']), 'birth': row['DT_NASCIMENTO'].strip()}
    missing = ids - set(found)
    if missing:
        raise SystemExit(f'perfis sem linha no registro 2026: {sorted(missing)}')
    return found, src


def collect(cache: Path) -> dict:
    people, register_source = participants(cache)
    by_title = {p['title']: sid for sid, p in people.items() if p['title'].isdigit()}
    by_name = {(p['name'], p['birth']): sid for sid, p in people.items()}
    by_name_only = {p['name']: sid for sid, p in people.items()}
    out = {'schema_version': 1, 'classification': 'official_electoral_records_not_performance',
           'retrieved_at': datetime.now(timezone.utc).isoformat(),
           'rule': {'years': YEARS, 'url_template': URL, 'primary_key': 'título eleitoral do registro 2026 (não gravado)',
                    'fallback_key': 'nome civil (maiúsculas, sem acento) + data de nascimento, só quando a linha histórica não divulga o título',
                    'coverage_gap': 'linhas sem título e sem nascimento não são identificáveis; contadas em rows_without_title_or_birth',
                    'elected_statuses': sorted(ELECTED), 'executive_offices': sorted(EXECUTIVE),
                    'vice_executive_offices': sorted(VICE_EXECUTIVE),
                    'limits': 'Totalização eleitoral não prova exercício integral, renúncia, licença, competência ou desempenho.'},
           'register_2026_source': register_source, 'sources': [], 'errors': [], 'name_birth_with_other_title': [], 'name_only_unverifiable': [],
           'participants': {sid: {'records': []} for sid in sorted(people)}}
    seen = set()
    for year in YEARS:
        url = URL.format(year=year)
        try:
            src = download(url, cache / f'consulta_cand_{year}.zip')
        except OSError as exc:
            out['errors'].append({'year': year, 'url': url, 'error': str(exc)})
            continue
        stats = {'rows': 0, 'files': set(), 'title_undisclosed_rows': 0, 'unmatchable_rows': 0}
        for name, row in rows(cache / f'consulta_cand_{year}.zip'):
            stats['rows'] += 1
            stats['files'].add(name)
            title = (row.get('NR_TITULO_ELEITORAL_CANDIDATO') or '').strip().lstrip('0')
            sid, rule = None, None
            if title.isdigit() and title:
                sid, rule = by_title.get(title), 'titulo'
                if not sid:
                    other = by_name.get((norm_name(row.get('NM_CANDIDATO')), (row.get('DT_NASCIMENTO') or '').strip()))
                    if other:  # mesmo nome civil e nascimento com outro título: registrado para revisão, não fundido
                        out['name_birth_with_other_title'].append({'candidate_id': other, 'year': row.get('ANO_ELEICAO'),
                                                                   'cargo': row.get('DS_CARGO'), 'sq_candidato': row.get('SQ_CANDIDATO')})
            else:
                stats['title_undisclosed_rows'] += 1
                birth = (row.get('DT_NASCIMENTO') or '').strip()
                if not birth or birth.startswith('#') or birth == '-4':
                    stats['unmatchable_rows'] += 1  # sem título e sem nascimento: não dá para identificar com segurança
                    hit = by_name_only.get(norm_name(row.get('NM_CANDIDATO')))
                    if hit:  # homônimo possível: registrado para revisão, nunca atribuído
                        out['name_only_unverifiable'].append({'candidate_id': hit, 'year': row.get('ANO_ELEICAO'),
                                                              'cargo': row.get('DS_CARGO'), 'uf': row.get('SG_UF'),
                                                              'status': row.get('DS_SIT_TOT_TURNO'), 'sq_candidato': row.get('SQ_CANDIDATO')})
                sid, rule = by_name.get((norm_name(row.get('NM_CANDIDATO')), birth)), 'nome+nascimento'
            if not sid:
                continue
            rec = {k: (row.get(k) or '').strip() for k in KEEP}
            key = (sid, rec['ANO_ELEICAO'], rec['NR_TURNO'], rec['DS_CARGO'], rec['SQ_CANDIDATO'])
            if key in seen:
                continue
            seen.add(key)
            rec.update(match_rule=rule, source_sha256=src['sha256'], source_member=name)
            out['participants'][sid]['records'].append(rec)
        out['sources'].append(dict(src, year=year, rows_scanned=stats['rows'], members=sorted(stats['files']),
                                   rows_without_title=stats['title_undisclosed_rows'],
                                   rows_without_title_or_birth=stats['unmatchable_rows']))
    resolve_unreported(out, cache)
    for sid, entry in out['participants'].items():
        recs = sorted(entry['records'], key=lambda r: (r['ANO_ELEICAO'], r['NR_TURNO'], r['DS_CARGO']))
        entry['records'] = recs
        won = [r for r in recs if r['DS_SIT_TOT_TURNO'] in ELECTED]
        entry['elected'] = sorted({(r['ANO_ELEICAO'], r['DS_CARGO'], r['SG_UF']) for r in won})
        entry['elected_executive'] = sorted({(r['ANO_ELEICAO'], r['DS_CARGO'], r['SG_UF']) for r in won if r['DS_CARGO'] in EXECUTIVE})
        entry['elected_vice_executive'] = sorted({(r['ANO_ELEICAO'], r['DS_CARGO'], r['SG_UF']) for r in won if r['DS_CARGO'] in VICE_EXECUTIVE})
        entry['match_rules_used'] = sorted({r['match_rule'] for r in recs})
    return out


def resolve_unreported(out: dict, cache: Path) -> None:
    """Mesma regra para todos quando a linha APTO não traz situação de totalização (#NULO no arquivo do TSE):
      1. vice: herda a situação do titular da mesma chapa (mesmo ano, UE e número) no próprio consulta_cand;
      2. titular de cargo majoritário: soma QT_VOTOS_NOMINAIS do arquivo oficial votacao_candidato_munzona do ano; no
         último turno em que aparece, é ELEITO só se teve mais votos que todos os concorrentes do mesmo cargo/UE/turno
         e esse turno é o 2º (ou não houve 2º turno e passou de 50% dos votos nominais).
    O valor original fica em consulta_cand_status e a derivação em status_derivation; sem dado, continua #NULO."""
    pending = [r for e in out['participants'].values() for r in e['records']
               if r['DS_SIT_TOT_TURNO'].strip('#') in {'NULO', ''} and r['DS_SITUACAO_CANDIDATURA'] == 'APTO']
    out['vote_sources'] = []
    heads = {'VICE-PRESIDENTE': 'PRESIDENTE', 'VICE-GOVERNADOR': 'GOVERNADOR', 'VICE-PREFEITO': 'PREFEITO'}
    by_year: dict = {}
    for rec in pending:
        by_year.setdefault(rec['ANO_ELEICAO'], []).append(rec)
    for year, recs in sorted(by_year.items()):
        head_keys = {(r['SG_UE'], r['NR_CANDIDATO'], heads[r['DS_CARGO']]) for r in recs if r['DS_CARGO'] in heads}
        head_rows: dict = {}
        if head_keys:
            for _, row in rows(cache / f'consulta_cand_{year}.zip'):
                k = ((row.get('SG_UE') or '').strip(), (row.get('NR_CANDIDATO') or '').strip(), (row.get('DS_CARGO') or '').strip())
                if k in head_keys and (row.get('DS_SITUACAO_CANDIDATURA') or '').strip() == 'APTO':
                    head_rows.setdefault(k, []).append({c: (row.get(c) or '').strip() for c in KEEP})
        majoritarian = [r for r in recs if r['DS_CARGO'] in EXECUTIVE]
        for k, hr in head_rows.items():
            for h in hr:
                if h['DS_SIT_TOT_TURNO'].strip('#') in {'NULO', ''}:
                    majoritarian.append(h)
        votes: dict = {}
        src = None
        if majoritarian:
            url = VOTES_URL.format(year=year)
            try:
                src = download(url, cache / f'votacao_candidato_munzona_{year}.zip')
            except OSError as exc:
                out['errors'].append({'year': year, 'url': url, 'error': str(exc)})
            if src:
                races = {(r['DS_CARGO'], r['SG_UE']) for r in majoritarian}
                for _, row in rows(cache / f'votacao_candidato_munzona_{year}.zip'):
                    race = ((row.get('DS_CARGO') or '').strip().upper(), (row.get('SG_UE') or '').strip())
                    if race in races:
                        key = (race, (row.get('NR_TURNO') or '').strip())
                        bucket = votes.setdefault(key, {})
                        sq = (row.get('SQ_CANDIDATO') or '').strip()
                        bucket[sq] = bucket.get(sq, 0) + int(row.get('QT_VOTOS_NOMINAIS') or 0)
                out['vote_sources'].append(dict(src, year=year, races=sorted(map(list, races))))

        def from_votes(rec):
            race = (rec['DS_CARGO'], rec['SG_UE'])
            turns = sorted(t for (rc, t), b in votes.items() if rc == race and rec['SQ_CANDIDATO'] in b)
            if not turns:
                return None, None
            turn = turns[-1]
            bucket = votes[(race, turn)]
            mine, others = bucket[rec['SQ_CANDIDATO']], [v for s, v in bucket.items() if s != rec['SQ_CANDIDATO']]
            total = sum(bucket.values())
            later = any(rc == race and t > turn for (rc, t) in votes)
            if later:
                status = 'NÃO ELEITO'
            elif turn == '2' or (turn == '1' and total and mine * 2 > total):
                status = 'ELEITO' if all(mine > v for v in others) else 'NÃO ELEITO'
            elif turn == '1' and not later and total:
                status = 'NÃO ELEITO' if any(v * 2 > total for v in others) else None
            else:
                status = None
            return status, {'rule': 'votos nominais do arquivo oficial de votação', 'turn': turn,
                            'candidate_votes': mine, 'race_votes': total, 'competitors': len(others),
                            'url': VOTES_URL.format(year=year), 'sha256': src['sha256'] if src else None}

        for rec in recs:
            rec['consulta_cand_status'] = rec['DS_SIT_TOT_TURNO']
            if rec['DS_CARGO'] in heads:
                hr = head_rows.get((rec['SG_UE'], rec['NR_CANDIDATO'], heads[rec['DS_CARGO']]), [])
                statuses = set()
                for h in hr:
                    st = h['DS_SIT_TOT_TURNO']
                    if st.strip('#') in {'NULO', ''}:
                        st, _ = from_votes(h)
                    if st:
                        statuses.add(st)
                final = 'ELEITO' if 'ELEITO' in statuses else ('NÃO ELEITO' if statuses else None)
                derivation = {'rule': 'situação do titular da mesma chapa', 'head_sq': sorted({h['SQ_CANDIDATO'] for h in hr}),
                              'head_statuses': sorted(statuses)}
            else:
                final, derivation = from_votes(rec)
            if final:
                rec['DS_SIT_TOT_TURNO'] = final
            rec['status_derivation'] = derivation or {'rule': 'sem dado oficial para derivar', 'status_kept': rec['DS_SIT_TOT_TURNO']}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=str(ROOT / '.cache/tse-consulta-cand'))
    ap.add_argument('--out', default=str(ROOT / 'research/mandate_history_v1.json'))
    args = ap.parse_args()
    data = collect(Path(args.cache))
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    for sid, entry in data['participants'].items():
        print(sid, len(entry['records']), 'registros;', 'executivo eleito:', entry['elected_executive'] or '—')
    print('erros:', data['errors'] or 'nenhum')
    return 0


if __name__ == '__main__':
    sys.exit(main())
