"""Coleta complementar: planos integrais, execução Siconfi e indicadores sociais.
Sem classificação por preferência política, credenciais ou alterações externas.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from urllib.parse import urlencode
import zipfile
import pymupdf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.research_governments import fetch, record
from src.evidence import scan_pages
from src.ranking import load_dossiers


def collect():
    output = {'retrieved_at': datetime.now(timezone.utc).isoformat(),
              'classification': 'context_and_automated_evidence_not_causal_parameters',
              'programs': [], 'fiscal_reports': [], 'social_indicators': [], 'sources': [], 'errors': []}
    cache = ROOT/'.cache/programs.zip'
    sources = json.loads((ROOT/'research/electoral_sources.json').read_text())
    expected = next(s for s in sources if s['id'] == 'programs')
    raw_archive = cache.read_bytes()
    if hashlib.sha256(raw_archive).hexdigest() != expected['sha256']:
        raise ValueError('Hash do arquivo TSE não confere com corte auditado')
    with zipfile.ZipFile(cache) as archive:
        for dossier in load_dossiers():
            raw = archive.read(dossier['program_archive_member'])
            if hashlib.sha256(raw).hexdigest() != dossier['program_sha256']:
                raise ValueError('Hash do PDF não confere')
            with pymupdf.open(stream=raw, filetype='pdf') as document:
                result = scan_pages([p.get_text() for p in document])
            output['programs'].append(dict(result, id=dossier['official_candidate_id'],
                name=dossier['supplied_name'], url=dossier['program_url'],
                archive_member=dossier['program_archive_member'], sha256=dossier['program_sha256']))
    for entity in [1, 31, 52]:
        for year in [2018, 2022, 2025]:
            url = 'https://apidatalake.tesouro.gov.br/ords/cdwhprd/siconfi/tt/rreo?' + urlencode({
                'an_exercicio': year, 'nr_periodo': 6, 'co_tipo_demonstrativo': 'RREO',
                'no_anexo': 'RREO-Anexo 14', 'id_ente': entity})
            try:
                raw = fetch(url)
                data = json.loads(raw)
                if data.get('hasMore') or data.get('count') != len(data.get('items', [])) or not data.get('items'):
                    raise ValueError('Resposta incompleta, paginada ou vazia: não usar como relatório completo')
                output['fiscal_reports'].append(dict(record(url, raw), entity=entity, year=year,
                                                     count=data['count'], items=data['items'], raw_json=raw.decode()))
            except (OSError, ValueError, KeyError) as exc:
                output['errors'].append({'id': f'siconfi-{entity}-{year}', 'url': url, 'error': str(exc)})
    for indicator in ['SP.DYN.IMRT.IN', 'SE.SEC.CMPT.LO.ZS', 'SH.XPD.CHEX.GD.ZS']:
        url = f'https://api.worldbank.org/v2/country/BRA/indicator/{indicator}?format=json&per_page=100&date=2000:2025'
        try:
            raw = fetch(url)
            data = json.loads(raw)
            if data[0]['pages'] != 1 or data[0]['total'] != len(data[1]):
                raise ValueError('Resposta de indicadores sociais incompleta')
            output['social_indicators'].append(dict(record(url, raw), id=indicator,
                label=data[1][0]['indicator']['value'], metadata=data[0],
                observations=[{'year': int(r['date']), 'value': r['value']} for r in data[1]], raw_json=raw.decode()))
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            output['errors'].append({'id': indicator, 'url': url, 'error': str(exc)})
    for key, url in [
        ('ifi', 'https://www12.senado.leg.br/ifi/pdf/raf113_jun2026.pdf'),
        ('inep', 'https://www.gov.br/inep/pt-br/acesso-a-informacao/dados-abertos/indicadores-educacionais'),
        ('datasus', 'https://datasus.saude.gov.br/informacoes-de-saude-tabnet/'),
        ('camara', 'https://dadosabertos.camara.leg.br/api/v2/referencias/proposicoes/codSituacao'),
        ('senado', 'https://legis.senado.leg.br/dadosabertos/senador/5894')]:
        try:
            raw = fetch(url)
            detail = ''
            if raw.startswith(b'%PDF'):
                with pymupdf.open(stream=raw, filetype='pdf') as doc:
                    for page, text in enumerate((p.get_text() for p in doc), 1):
                        if '2,1%' in text and 'prim' in text.lower():
                            hit = text.find('2,1%')
                            detail = {'page': page, 'quote': ' '.join(text[max(0, hit-200):hit+600].split())}
                            break
            output['sources'].append(dict(record(url, raw), id=key, status='retrieved', excerpt=detail,
                use='context_only_not_candidate_coefficient'))
        except (OSError, ValueError) as exc:
            output['errors'].append({'id': key, 'url': url, 'error': str(exc)})
    return output


if __name__ == '__main__':
    data = collect()
    target = ROOT/'research/expanded_evidence.json'
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'target': str(target), 'programs': len(data['programs']),
                      'pages_scanned': sum(p['pages_scanned'] for p in data['programs']),
                      'fiscal_reports': len(data['fiscal_reports']), 'social_indicators': len(data['social_indicators']),
                      'sources': len(data['sources']), 'errors': data['errors']}, ensure_ascii=False, indent=2))
