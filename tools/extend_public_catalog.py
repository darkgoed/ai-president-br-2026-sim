"""Amplia catálogo sem sobrescrever snapshots: lista uniforme, metadados primários.
Uso: python tools/extend_public_catalog.py --out research/public-extension-v2
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.observed import download
from src.public_validation import validate_dataset, world_bank_rows

# IDs são consultados no catálogo oficial antes de aceitar qualquer dado.
# Falha de metadados vira lacuna; não se substitui por indicador parecido.
INDICATORS = ['SE.XPD.TOTL.GD.ZS', 'NY.GDP.PCAP.KD', 'NY.GDP.MKTP.KD.ZG',
              'FP.CPI.TOTL.ZG', 'SL.TLF.CACT.ZS', 'SL.TLF.CACT.FE.ZS',
              'SL.EMP.TOTL.SP.ZS', 'SL.UEM.1524.ZS', 'SI.POV.DDAY',
              'SH.UHC.SRVS.CV.XD', 'SH.TBS.INCD', 'EG.FEC.RNEW.ZS',
              'AG.LND.FRST.ZS', 'BX.KLT.DINV.WD.GD.ZS']


def extend(output):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT) or output.exists():
        raise ValueError('Use destino novo dentro do projeto; histórico não será sobrescrito')
    base_path = ROOT/'research/public_catalog.json'
    catalog = json.loads(base_path.read_text())
    for dataset in catalog['datasets']:
        validate_dataset(ROOT, dataset)
    output.mkdir(parents=True)
    citation_tool = Path.home()/'.hermes/profiles/daybreak/skills/research/grounded-citations/scripts/sources.py'
    if not citation_tool.is_file():
        raise ValueError('Ledger de citações indisponível')

    def response(url, name):
        time.sleep(.3)
        raw = download(url)
        path = output/(name+'.json')
        path.write_bytes(raw)
        subprocess.run([sys.executable, str(citation_tool), '--ledger', str(output/'citations.json'), 'add', url],
                       check=True, stdout=subprocess.DEVNULL)
        return json.loads(raw), {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'response_path': str(path.relative_to(ROOT))}

    added = []
    for indicator in INDICATORS:
        if any(d['id'] == 'wb-'+indicator for d in catalog['datasets']):
            continue
        try:
            metadata, meta = response(f'https://api.worldbank.org/v2/indicator/{indicator}?format=json', 'wb-'+indicator+'-metadata')
            if not isinstance(metadata, list) or len(metadata) != 2 or metadata[0].get('total') != 1 or metadata[1][0]['id'] != indicator:
                raise ValueError('Indicador não confirmado nos metadados oficiais')
            spec = metadata[1][0]
            data, source = response(f'https://api.worldbank.org/v2/country/BRA/indicator/{indicator}?format=json&date=2000:2025&per_page=100', 'wb-'+indicator+'-br')
            observations = world_bank_rows(data, indicator)
            dataset = dict(source, id='wb-'+indicator, provider='Banco Mundial / '+spec.get('sourceOrganization', ''),
                label=spec['name'], definition=spec.get('sourceNote'), unit=spec.get('unit') or None,
                metadata=meta, observations=observations, usage='context_only_not_causal_calibration',
                missing_unit_note='Não inferir unidade; definição primária preservada integralmente.')
            validate_dataset(ROOT, dataset)
            catalog['datasets'].append(dataset)
            added.append({'id': dataset['id'], 'label': dataset['label'], 'rows': len(observations), 'source': source})
        except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
            catalog['errors'].append({'id': 'wb-'+indicator, 'error': str(error)})
    catalog['extension'] = {'version': 2, 'base_sha256': hashlib.sha256(base_path.read_bytes()).hexdigest(),
        'selection_rule': 'Lista fixada antes da coleta, BRA, 2000:2025, independente de candidatura; nenhuma substituição por conveniência.',
        'requested_indicators': INDICATORS, 'added': added, 'retrieved_at': datetime.now(timezone.utc).isoformat()}
    target = output/'public_catalog.json'
    target.write_text(json.dumps(catalog, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'catalog': str(target), 'added_datasets': len(added), 'total_datasets': len(catalog['datasets']),
        'total_observations': sum(len(d['observations']) for d in catalog['datasets']), 'errors': catalog['errors']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    extend(ROOT/args.out)
