"""Coleta auditável de séries públicas BCB/SGS; não estima efeitos políticos."""
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from statistics import mean
from urllib.request import Request, urlopen

# IDs, unidades e produtores conferidos nos metadados oficiais SGS.
CATALOG = [
    ('ipca_month', 433, 'IPCA mensal', '% no mês', 'IBGE', 'mensal'),
    ('ipca_12m', 13522, 'IPCA acumulado em 12 meses', '% em 12 meses', 'IBGE', 'mensal'),
    ('selic_target', 432, 'Meta Selic', '% a.a.', 'Copom', 'diária'),
    ('usd_brl', 1, 'Dólar comercial — venda', 'R$/US$', 'Sisbacen/PTAX', 'diária'),
    ('gross_debt_gdp', 13762, 'Dívida bruta do governo geral', '% PIB', 'BCB-DSTAT', 'mensal'),
    ('gross_debt_brl', 13761, 'Dívida bruta do governo geral em reais', 'R$ milhões', 'BCB-DSTAT', 'mensal'),
    ('unemployment', 24369, 'Desocupação PNADC — trimestre móvel', '%', 'IBGE', 'mensal'),
    ('activity', 24364, 'IBC-Br com ajuste sazonal', 'índice', 'BCB-Depec', 'mensal'),
    ('monthly_gdp', 4380, 'PIB mensal a preços correntes — estimativa BCB', 'R$ milhões', 'BCB-Depec', 'mensal'),
    ('selic_month', 4390, 'Selic acumulada no mês', '% no mês', 'BCB-Demab', 'mensal'),
    ('credit_interest', 20714, 'Taxa média de juros — novas operações de crédito', '% a.a.', 'BCB-DSTAT', 'mensal'),
    ('delinquency', 21082, 'Inadimplência de crédito acima de 90 dias', '%', 'BCB-DSTAT', 'mensal'),
]


def download(url) -> bytes:
    for attempt in range(2):
        try:
            with urlopen(Request(url, headers={'User-Agent': 'PresidenteIA/1.0 (public-data)'}), timeout=30) as response:
                return response.read()
        except OSError:
            if attempt:
                raise
    raise OSError('Coleta indisponível após duas tentativas')


def parse_observations(raw, today):
    rows = json.loads(raw)
    if not isinstance(rows, list) or not rows:
        raise ValueError('Resposta vazia ou fora do formato SGS')
    observations = []
    seen = set()
    for row in rows:
        timestamp = datetime.strptime(row['data'], '%d/%m/%Y').date()
        value = float(row['valor'])
        if not math.isfinite(value) or timestamp > today or timestamp in seen:
            raise ValueError('Valor não finito, data futura ou duplicada')
        seen.add(timestamp)
        observations.append({'date': timestamp.isoformat(), 'value': value})
    return sorted(observations, key=lambda row: row['date'])[-20:]


def fetch_snapshot(fetcher=None, today=None):
    fetcher = fetcher or download
    today = today or datetime.now(timezone.utc).date()
    snapshot = {'schema_version': 1, 'classification': 'observed_not_policy_effect',
                'retrieved_at': datetime.now(timezone.utc).isoformat(), 'as_of': today.isoformat(),
                'window': 'latest_20_observations_not_necessarily_months',
                'series': [], 'errors': []}
    for key, sgs, label, unit, producer, frequency in CATALOG:
        url = f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{sgs}/dados/ultimos/20?formato=json'
        # A meta Selic pode incluir datas futuras já cadastradas. Consulte só
        # datas até a coleta, em vez de tratar esses registros como observados.
        if key == 'selic_target':
            start = today - timedelta(days=45)
            url = (f'https://api.bcb.gov.br/dados/serie/bcdata.sgs.{sgs}/dados?formato=json'
                   f'&dataInicial={start:%d/%m/%Y}&dataFinal={today:%d/%m/%Y}')
        try:
            raw = fetcher(url)
            observations = parse_observations(raw, today)
            values = [row['value'] for row in observations]
            previous = values[-2] if len(values) > 1 else None
            snapshot['series'].append({
                'id': key, 'sgs_id': sgs, 'label': label, 'unit': unit, 'producer': producer,
                'frequency': frequency, 'url': url,
                'metadata_url': f'https://www3.bcb.gov.br/sgspub/consultarmetadados/consultarMetadadosSeries.do?method=consultarMetadadosSeriesInternet&hdOidSerieSelecionada={sgs}',
                'sha256': hashlib.sha256(raw).hexdigest(), 'raw_json': raw.decode('utf-8'),
                'observations': observations,
                'statistics': {'n': len(values), 'first_date': observations[0]['date'],
                               'last_date': observations[-1]['date'], 'previous': previous,
                               'change': values[-1] - previous if previous is not None else None,
                               'mean': mean(values), 'min': min(values), 'max': max(values)}})
        except (OSError, ValueError, KeyError, TypeError) as exc:
            snapshot['errors'].append({'id': key, 'url': url, 'error': str(exc)})
    return snapshot


def load_snapshot(path):
    """Offline: confira integridade e datas; mantenha a data original da coleta."""
    snapshot = json.loads(path.read_text(encoding='utf-8'))
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot):
    """Valida identidade e transformação; coletas parciais exigem erros explícitos."""
    if snapshot['classification'] != 'observed_not_policy_effect':
        raise ValueError('Classificação inválida do snapshot')
    expected = {key: (sgs, label, unit, producer, frequency)
                for key, sgs, label, unit, producer, frequency in CATALOG}
    seen = set()
    for series in snapshot['series']:
        key = series['id']
        if key in seen or key not in expected:
            raise ValueError('Série duplicada ou identidade desconhecida')
        seen.add(key)
        identity = tuple(series.get(k) for k in ['sgs_id', 'label', 'unit', 'producer', 'frequency'])
        if identity != expected[key]:
            raise ValueError('Metadados de identidade da série não conferem com catálogo')
        from urllib.parse import urlparse
        url = urlparse(series['url'])
        base_path = f'/dados/serie/bcdata.sgs.{series["sgs_id"]}/dados'
        if url.scheme != 'https' or url.netloc != 'api.bcb.gov.br' or url.path not in {base_path, base_path+'/ultimos/20'}:
            raise ValueError('URL não corresponde à identidade SGS')
        raw = series['raw_json'].encode('utf-8')
        if hashlib.sha256(raw).hexdigest() != series['sha256']:
            raise ValueError('Hash do snapshot oficial não confere')
        if parse_observations(raw, date.fromisoformat(snapshot['as_of'])) != series['observations']:
            raise ValueError('Observações não conferem com resposta original')
        rows = series['observations']
        values = [r['value'] for r in rows]
        previous = values[-2] if len(values) > 1 else None
        expected_statistics = {'n': len(values), 'first_date': rows[0]['date'], 'last_date': rows[-1]['date'],
                               'previous': previous, 'change': values[-1]-previous if previous is not None else None,
                               'mean': mean(values), 'min': min(values), 'max': max(values)}
        if series['statistics'] != expected_statistics:
            raise ValueError('Estatísticas divergem das observações verificadas')
    failed = {e['id'] for e in snapshot.get('errors', [])}
    if set(expected)-seen != failed or seen & failed:
        raise ValueError('Coleta parcial exige lacunas explicitamente registradas')
