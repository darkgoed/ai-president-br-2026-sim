from datetime import date
import pytest


def test_ibge_normalizer_preserves_suppression_units_and_classifications():
    from src.public_data import normalize_ibge
    data = [{'id': '4099', 'variavel': 'Desocupação', 'unidade': '%', 'resultados': [
        {'classificacoes': [{'id': '2', 'nome': 'Grupo', 'categoria': {'5': 'Total'}}],
         'series': [{'localidade': {'id': '31', 'nome': 'Minas Gerais', 'nivel': {'id': 'N3'}},
                     'serie': {'202601': '-', '202602': '3.8'}}]}]}]
    rows = normalize_ibge(data, aggregate=6468, expected_variable=4099)
    assert rows[0]['value'] is None and rows[0]['source_value'] == '-'
    assert rows[1]['value'] == 3.8 and rows[1]['unit'] == '%'
    assert rows[1]['entity_id'] == '31'
    assert rows[1]['classifications'][0]['categoria'] == {'5': 'Total'}
    assert rows[1]['candidate_id'] is None
    with pytest.raises(ValueError, match='variável'):
        normalize_ibge(data, aggregate=6468, expected_variable=5933)
