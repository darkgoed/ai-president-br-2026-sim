"""Busca uniforme em todas as páginas; menção não vira compromisso nem efeito."""
import re

AXES = {
    'economia': r'econom|produtiv|investimento|ind[uú]stria',
    'fiscal': r'fiscal|or[cç]ament|tribut|d[ií]vida|imposto',
    'seguranca': r'seguran[cç]a|pol[ií]cia|prisional|homic[ií]dio',
    'saude': r'sa[uú]de|hospital|hospitais|aten[cç][aã]o b[aá]sica|\bSUS\b',
    'educacao': r'educa[cç][aã]o|escola|alfabet|ensino',
    'emprego': r'emprego|trabalho|salarial|sal[aá]rio|jornada',
    'social': r'pobreza|social|desigualdade|renda|benef[ií]cio',
    'infraestrutura': r'infraestrutura|rodovia|ferrovia|moradia|saneamento|habita[cç]',
    'ambiente': r'ambient|desmatamento|clima|floresta|emiss[oõ]es',
    'governanca': r'governan[cç]a|transpar[eê]ncia|corrup[cç][aã]o|administra[cç][aã]o',
}
MARKERS = {
    'numeric': r'\d[\d.,]*\s*(?:%|milh[oõ]es|milh[aã]o|bilh[oõ]es|bilh[aã]o|hospitais|vagas|escolas)|(?:R\$|US\$)\s*\d',
    'deadline': r'at[eé]\s*(?:o ano de\s*)?20\d{2}|em\s+\d+\s+anos?|prazo de|primeiros?\s+\d+\s+dias',
    'funding': r'financia|or[cç]ament|fonte de recurso|custeio|custo|compensa[cç][aã]o',
    'implementation': r'\b(?:lei|decreto|PEC|programa|concess[aã]o|conv[eê]nio|regulamenta[cç][aã]o)\b',
    'monitoring': r'indicador|monitoramento|avalia[cç][aã]o|auditoria|transpar[eê]ncia',
}


def scan_pages(pages):
    if not pages or any(not isinstance(p, str) for p in pages):
        raise ValueError('Páginas textuais ausentes')
    axes = []
    for axis, topic in AXES.items():
        mentions = {key: {'count': 0, 'examples': []} for key in MARKERS}
        topic_pages = []
        for page, text in enumerate(pages, 1):
            text = ' '.join(text.split())
            if re.search(topic, text, re.I):
                topic_pages.append(page)
            for marker, pattern in MARKERS.items():
                for match in re.finditer(pattern, text, re.I):
                    window = text[max(0, match.start()-180):min(len(text), match.end()+240)]
                    if re.search(topic, window, re.I):
                        mentions[marker]['count'] += 1
                        if len(mentions[marker]['examples']) < 4:
                            mentions[marker]['examples'].append({'page': page, 'quote': window})
        axes.append({'axis': axis, 'topic_pages': topic_pages, 'mentions': mentions})
    return {'classification': 'automated_fulltext_mentions_not_validated_commitments',
            'pages_scanned': len(pages), 'axes': axes, 'used_in_government_ranking': False,
            'warning': 'Mesmo procedimento em todas as páginas. Heurísticas podem detectar diagnósticos, negações, citações ou metas de terceiros. Exige revisão humana/semântica; não é contagem de promessas confirmadas nem nota de governo. Tamanho de documento e repetição não devem virar pontos.'}
