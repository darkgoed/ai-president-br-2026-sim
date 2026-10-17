"""Ampliação uniforme e pública: todas as UFs, sem seleção por candidatura.
Snapshots de respostas guardados para inspeção; nenhuma imputação de impacto.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools.research_governments import fetch, record
from src.public_data import normalize_ibge

IBGE = [(6468, 4099), (6468, 4103), (6472, 5933), (6472, 5941), (4092, 1641), (5938, 37)]
SOCIAL = ['SP.DYN.IMRT.IN', 'SP.DYN.LE00.IN', 'SH.DYN.MORT', 'SH.STA.MMRT',
          'SH.XPD.CHEX.GD.ZS', 'SH.IMM.IDPT', 'SH.IMM.MEAS', 'SE.SEC.CMPT.LO.ZS',
          'SE.PRM.CMPT.ZS', 'SI.POV.GINI', 'SI.POV.NAHC', 'SL.UEM.TOTL.ZS',
          'EN.ATM.CO2E.PC', 'EG.ELC.ACCS.ZS', 'SH.H2O.BASW.ZS', 'SH.STA.BASS.ZS']


def collect(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {'classification': 'reported_public_statistics_not_government_effects',
              'retrieved_at': datetime.now(timezone.utc).isoformat(),
              'selection_rule': 'IBGE Brasil+all27UF; Siconfi all27UF+Uniao 2025 RREO14; WB predefined indicators, no candidate-dependent selection',
              'datasets': [], 'errors': []}

    def response(url, name):
        time.sleep(.2)
        raw = fetch(url)
        path = output/(name+'.json')
        path.write_bytes(raw)
        return json.loads(raw), dict(record(url, raw), response_path=str(path.relative_to(ROOT)))

    for aggregate, variable in IBGE:
        try:
            metadata_url = f'https://servicodados.ibge.gov.br/api/v3/agregados/{aggregate}/metadados'
            metadata, meta = response(metadata_url, f'ibge-{aggregate}-metadata')
            spec = next(v for v in metadata['variaveis'] if v['id'] == variable)
            for locality in ['N1[1]', 'N3[all]']:
                url = f'https://servicodados.ibge.gov.br/api/v3/agregados/{aggregate}/periodos/-40/variaveis/{variable}?localidades={locality}'
                if aggregate == 4092:
                    url += '&classificacao=629[32385,32386,32387,32446,32447]'
                data, source = response(url, f'ibge-{aggregate}-{variable}-'+('br' if locality.startswith('N1') else 'ufs'))
                rows = normalize_ibge(data, aggregate, variable)
                if {r['entity_id'] for r in rows} and locality == 'N3[all]' and len({r['entity_id'] for r in rows}) != 27:
                    raise ValueError('Cobertura estadual diferente das 27 UFs; não declarar cobertura integral')
                report['datasets'].append(dict(source, id=f'ibge-{aggregate}-{variable}-{locality}',
                    provider='IBGE', label=spec['nome'], unit=spec['unidade'], frequency=metadata['periodicidade']['frequencia'],
                    metadata=meta, observations=rows, usage='context_only_not_causal_calibration'))
        except (OSError, ValueError, KeyError, StopIteration) as exc:
            report['errors'].append({'id': f'ibge-{aggregate}-{variable}', 'error': str(exc)})
    for entity in [1, 11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53]:
        url = 'https://apidatalake.tesouro.gov.br/ords/cdwhprd/siconfi/tt/rreo?' + urlencode({
            'an_exercicio': 2025, 'nr_periodo': 6, 'co_tipo_demonstrativo': 'RREO', 'no_anexo': 'RREO-Anexo 14', 'id_ente': entity})
        try:
            data, source = response(url, f'siconfi-{entity}-2025')
            if data.get('hasMore') or data.get('count') != len(data.get('items', [])) or not data.get('items'):
                raise ValueError('Relatório paginado, vazio ou contagem inconsistente')
            report['datasets'].append(dict(source, id=f'siconfi-{entity}-2025', provider='Tesouro/Siconfi',
                label='RREO-Anexo 14', entity_id=str(entity), period='2025-B6', observations=data['items'],
                usage='context_only_not_causal_calibration'))
        except (OSError, ValueError, KeyError) as exc:
            report['errors'].append({'id': f'siconfi-{entity}-2025', 'url': url, 'error': str(exc)})
    for indicator in SOCIAL:
        try:
            metadata, meta = response(f'https://api.worldbank.org/v2/indicator/{indicator}?format=json', f'wb-{indicator}-metadata')
            if metadata[0]['total'] != 1 or metadata[1][0]['id'] != indicator:
                raise ValueError('Metadado ausente ou indicador divergente')
            spec = metadata[1][0]
            url = f'https://api.worldbank.org/v2/country/BRA/indicator/{indicator}?format=json&date=2000:2025&per_page=100'
            data, source = response(url, f'wb-{indicator}-br')
            if data[0]['pages'] != 1 or data[0]['total'] != len(data[1]):
                raise ValueError('Resposta de indicadores incompleta')
            report['datasets'].append(dict(source, id=f'wb-{indicator}', provider='Banco Mundial / '+spec.get('sourceOrganization', ''),
                label=spec['name'], definition=spec.get('sourceNote'), unit=spec.get('unit') or None,
                metadata=meta, observations=[{'period': r['date'], 'value': r['value'], 'entity': 'Brasil', 'entity_id': 'BRA'} for r in data[1]],
                usage='context_only_not_causal_calibration', missing_unit_note='Se unidade estruturada vazia, consultar nome/definição original; não inferir unidade'))
        except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            report['errors'].append({'id': f'wb-{indicator}', 'error': str(exc)})
    (ROOT/'research/public_catalog.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'datasets': len(report['datasets']), 'observations': sum(len(s['observations']) for s in report['datasets']),
                      'errors': report['errors']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    collect(ROOT/'research/public-responses')
