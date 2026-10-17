"""Validação offline da transformação, não apenas do hash do arquivo local."""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

from .public_data import normalize_ibge


def _same(a, b):
    # Igualdade Python aceita True == 1; payloads de evidência não podem aceitar.
    return json.dumps(a, sort_keys=True, ensure_ascii=False, allow_nan=False) == json.dumps(b, sort_keys=True, ensure_ascii=False, allow_nan=False)


def checked_response(root, source):
    root = Path(root).resolve()
    path = (root/source['response_path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Resposta fora da raiz do snapshot')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != source['sha256']:
        raise ValueError('Hash da resposta original não confere')
    if source.get('bytes', len(raw)) != len(raw):
        raise ValueError('Tamanho da resposta original não confere')
    return raw, json.loads(raw)


def fiscal_items(data, url):
    query = parse_qs(urlparse(url).query)
    if data.get('hasMore') is not False or not data.get('items') or data.get('count') != len(data['items']):
        raise ValueError('Resposta fiscal original vazia, paginada ou incompleta')
    for row in data['items']:
        if (str(row['cod_ibge']) != query['id_ente'][0]
                or str(row['exercicio']) != query['an_exercicio'][0]
                or str(row['periodo']) != query['nr_periodo'][0]):
            raise ValueError('Ente, exercício ou período diverge da consulta original')
    return data['items']


def world_bank_rows(data, indicator):
    if not isinstance(data, list) or len(data) != 2 or data[0].get('pages') != 1 or data[0].get('total') != len(data[1]):
        raise ValueError('Resposta original Banco Mundial incompleta')
    if any(r['indicator']['id'] != indicator or r['countryiso3code'] != 'BRA' for r in data[1]):
        raise ValueError('Indicador ou território divergente da resposta original')
    return [{'period': r['date'], 'value': r['value'], 'entity': 'Brasil', 'entity_id': 'BRA'} for r in data[1]]


def validate_dataset(root, dataset):
    raw, data = checked_response(root, dataset)
    url = urlparse(dataset['url'])
    provider = dataset['provider']
    if provider == 'IBGE':
        match = re.fullmatch(r'/api/v3/agregados/(\d+)/periodos/[^/]+/variaveis/(\d+)', url.path)
        if url.netloc != 'servicodados.ibge.gov.br' or not match:
            raise ValueError('Identidade da consulta original IBGE inválida')
        aggregate, variable = map(int, match.groups())
        _, metadata = checked_response(root, dataset['metadata'])
        spec = next(v for v in metadata['variaveis'] if v['id'] == variable)
        if (dataset['label'], dataset['unit'], dataset['frequency']) != (spec['nome'], spec['unidade'], metadata['periodicidade']['frequencia']):
            raise ValueError('Metadados IBGE divergem da definição original')
        expected = normalize_ibge(data, aggregate, variable)
    elif provider == 'Tesouro/Siconfi':
        if url.netloc != 'apidatalake.tesouro.gov.br':
            raise ValueError('Identidade da consulta Siconfi inválida')
        expected = fiscal_items(data, dataset['url'])
    elif provider.startswith('Banco Mundial / '):
        indicator = dataset['id'].removeprefix('wb-')
        if url.netloc != 'api.worldbank.org' or not url.path.endswith('/indicator/'+indicator):
            raise ValueError('Identidade da consulta Banco Mundial inválida')
        _, metadata = checked_response(root, dataset['metadata'])
        if metadata[0].get('total') != 1 or metadata[1][0]['id'] != indicator:
            raise ValueError('Metadados de indicador original ausentes')
        spec = metadata[1][0]
        if (dataset['label'], dataset['definition'], dataset['unit']) != (spec['name'], spec.get('sourceNote'), spec.get('unit') or None):
            raise ValueError('Definição Banco Mundial diverge do original')
        expected = world_bank_rows(data, indicator)
    else:
        raise ValueError('Provedor sem transformação validada')
    if not _same(expected, dataset['observations']):
        raise ValueError('Observações normalizadas divergem da resposta original')
    return raw


def validate_embedded_fiscal(report):
    raw = report['raw_json'].encode()
    if hashlib.sha256(raw).hexdigest() != report['sha256']:
        raise ValueError('Hash da resposta fiscal original não confere')
    if not _same(fiscal_items(json.loads(raw), report['url']), report['items']):
        raise ValueError('Itens fiscais divergem da resposta original')


def validate_embedded_social(series):
    raw = series['raw_json'].encode()
    if hashlib.sha256(raw).hexdigest() != series['sha256']:
        raise ValueError('Hash da resposta social original não confere')
    rows = world_bank_rows(json.loads(raw), series['id'])
    expected = [{'year': int(r['period']), 'value': r['value']} for r in rows]
    if not _same(expected, series['observations']):
        raise ValueError('Observações sociais divergem da resposta original')
