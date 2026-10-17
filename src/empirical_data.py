"""Históricos SGS integrais e auditáveis para bootstrap empírico conjunto."""
from datetime import date, datetime, timezone
import gzip
import hashlib
import json
import math
from urllib.parse import urlparse
from .observed import download

DRIVERS = [
    ('debt', 13762, 'Dívida bruta do governo geral', '% PIB', 'BCB'),
    ('unemployment', 24369, 'Desocupação PNADC — trimestre móvel', '%', 'IBGE via BCB'),
    ('activity', 24364, 'IBC-Br com ajuste sazonal', 'índice', 'BCB'),
    ('inflation', 433, 'IPCA mensal', '% no mês', 'IBGE via BCB'),
]


def parse_sgs_history(raw, as_of):
    rows = json.loads(raw)
    if not isinstance(rows, list):
        raise ValueError('Histórico SGS fora do formato esperado')
    observations = []
    seen = set()
    for row in rows:
        stamp = datetime.strptime(row['data'], '%d/%m/%Y').date()
        value = float(row['valor'])
        period = stamp.strftime('%Y-%m')
        if not math.isfinite(value) or stamp > as_of or period in seen:
            raise ValueError('Valor não finito, referência futura ou mês duplicado')
        seen.add(period)
        observations.append({'period': period, 'value': value})
    return sorted(observations, key=lambda row: row['period'])


def collect_history(fetcher=None, as_of=None):
    fetcher = fetcher or download
    as_of = as_of or datetime.now(timezone.utc).date()
    snapshot = {'schema_version': 1, 'status': 'incomplete',
                'classification': 'observed_joint_monthly_history_not_policy_effects',
                'as_of': as_of.isoformat(), 'retrieved_at': datetime.now(timezone.utc).isoformat(),
                'series': [], 'errors': []}
    for key, sgs, label, unit, producer in DRIVERS:
        chunks, observations = [], []
        try:
            for year in range(2006, as_of.year + 1, 10):
                start = date(year, 1, 1)
                end = min(date(year + 9, 12, 31), as_of)
                url = (f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{sgs}/dados?formato=json'
                       f'&dataInicial={start:%d/%m/%Y}&dataFinal={end:%d/%m/%Y}')
                raw = fetcher(url)
                raw = gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw
                observations.extend(parse_sgs_history(raw, as_of))
                chunks.append({'url': url, 'sha256': hashlib.sha256(raw).hexdigest(),
                               'raw_json': raw.decode('utf-8')})
            observations.sort(key=lambda row: row['period'])
            if not observations or len({r['period'] for r in observations}) != len(observations):
                raise ValueError('Histórico vazio ou duplicado entre consultas')
            snapshot['series'].append({'id': key, 'sgs_id': sgs, 'label': label, 'unit': unit,
                                       'producer': producer, 'chunks': chunks, 'observations': observations})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            snapshot['errors'].append({'id': key, 'error': str(exc)})
    if not snapshot['errors'] and len(snapshot['series']) == len(DRIVERS):
        snapshot['status'] = 'complete'
    return snapshot


def validate_snapshot(snapshot):
    if snapshot['status'] != 'complete' or snapshot['errors']:
        raise ValueError('Histórico incompleto: não pode calibrar o simulador')
    expected = {key: (sgs, label, unit, producer) for key, sgs, label, unit, producer in DRIVERS}
    if snapshot.get('classification') != 'observed_joint_monthly_history_not_policy_effects':
        raise ValueError('Classificação do histórico inválida')
    if len(snapshot['series']) != len(expected) or {s['id'] for s in snapshot['series']} != expected.keys():
        raise ValueError('Conjunto de séries calibradoras inválido')
    as_of = date.fromisoformat(snapshot['as_of'])
    for series in snapshot['series']:
        if (series['sgs_id'], series['label'], series['unit'], series['producer']) != expected[series['id']]:
            raise ValueError('ID ou unidade da série não confere')
        decoded = []
        for chunk in series['chunks']:
            url = urlparse(chunk['url'])
            if url.scheme != 'https' or url.netloc != 'api.bcb.gov.br' or url.path != f'/dados/serie/bcdata.sgs.{series["sgs_id"]}/dados':
                raise ValueError('URL não corresponde à identidade da série SGS')
            raw = chunk['raw_json'].encode('utf-8')
            if hashlib.sha256(raw).hexdigest() != chunk['sha256']:
                raise ValueError('hash da resposta oficial não confere')
            decoded.extend(parse_sgs_history(raw, as_of))
        decoded.sort(key=lambda row: row['period'])
        if decoded != series['observations'] or len({r['period'] for r in decoded}) != len(decoded):
            raise ValueError('Observações divergem das respostas oficiais')
