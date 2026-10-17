import pytest


def test_fulltext_scan_uses_every_page_and_retains_negation_for_review():
    from src.evidence import scan_pages
    pages = ['Saúde: não há meta de 50 hospitais até 2030.', 'Educação com avaliação anual e auditoria.']
    result = scan_pages(pages)
    assert result['pages_scanned'] == 2
    assert result['classification'] == 'automated_fulltext_mentions_not_validated_commitments'
    health = next(x for x in result['axes'] if x['axis'] == 'saude')
    assert health['mentions']['numeric']['count'] > 0
    assert health['mentions']['deadline']['examples'][0]['page'] == 1
    assert 'não há' in health['mentions']['numeric']['examples'][0]['quote']
    assert result['used_in_government_ranking'] is False
