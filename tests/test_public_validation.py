"""Verifica que hash válido sozinho nunca autentica observação/metadado alterado."""
from copy import deepcopy
import hashlib
import json
import pytest
from src.public_validation import validate_dataset


@pytest.fixture
def world_bank(tmp_path):
    def response(name, data):
        raw = json.dumps(data).encode()
        (tmp_path/name).write_bytes(raw)
        return {'response_path': name, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    indicator = 'SP.DYN.IMRT.IN'
    metadata = response('metadata.json', [{'total': 1}, [{'id': indicator, 'name': 'Fixture indicator', 'sourceNote': 'Fixture definition', 'unit': ''}]])
    source = response('response.json', [{'pages': 1, 'total': 2}, [
        {'indicator': {'id': indicator}, 'countryiso3code': 'BRA', 'date': '2020', 'value': 1},
        {'indicator': {'id': indicator}, 'countryiso3code': 'BRA', 'date': '2021', 'value': None}]])
    dataset = dict(source, id='wb-'+indicator, provider='Banco Mundial / Fixture',
                   url='https://api.worldbank.org/v2/country/BRA/indicator/'+indicator,
                   label='Fixture indicator', definition='Fixture definition', unit=None, metadata=metadata,
                   observations=[{'period': '2020', 'value': 1, 'entity': 'Brasil', 'entity_id': 'BRA'},
                                 {'period': '2021', 'value': None, 'entity': 'Brasil', 'entity_id': 'BRA'}])
    return tmp_path, dataset


def test_valid_normalized_snapshot_is_accepted(world_bank):
    root, dataset = world_bank
    assert validate_dataset(root, dataset) == (root/'response.json').read_bytes()


@pytest.mark.parametrize('mutation', ['value', 'truncate', 'boolean', 'unit', 'label', 'territory'])
def test_payload_tampering_is_rejected_even_when_raw_hash_stays_valid(world_bank, mutation):
    root, dataset = world_bank
    changed = deepcopy(dataset)
    if mutation == 'value':
        changed['observations'][0]['value'] = 999
    elif mutation == 'truncate':
        changed['observations'].pop()
    elif mutation == 'boolean':
        changed['observations'][0]['value'] = True
    elif mutation in {'unit', 'label'}:
        changed[mutation] = 'Unverified interpretation'
    else:
        changed['observations'][0]['entity_id'] = 'ARG'
    with pytest.raises(ValueError, match='original'):
        validate_dataset(root, changed)
