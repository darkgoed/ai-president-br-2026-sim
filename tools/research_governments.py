"""Coleta oficial reproduzível: PNADC/PIB por território e contexto institucional.
Não atribui mudanças observadas a governantes, nem fornece coeficientes causais.
"""
from datetime import datetime, timezone
import gzip
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

SOURCES = [
    ('ibge-gdp-metadata', 'PIB a preços correntes — metadados oficiais (API alternativa à página HTML bloqueada)', 'https://servicodados.ibge.gov.br/api/v3/agregados/5938/metadados', ['Produto Interno Bruto', 'Mil Reais']),
    ('inep-ideb', 'Ideb — metodologia, não nota de governante', 'https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb', ['aprendizagem', 'fluxo', 'indicador']),
    ('tce-go-2025', 'Contas de Goiás de 2025 — parecer prévio', 'https://portal.tce.go.gov.br/-/sumario-disponibilizado-pelo-tce-go-trata-das-contas-do-governador-de-2025', ['parecer favorável', 'julgamento definitivo', 'Relatório Técnico']),
    ('tce-mg-2020', 'Contas de Minas de 2020 — ressalvas e pandemia', 'https://www.tce.mg.gov.br/TCEMG-emite-parecer-previo-pela-aprovacao-com-ressalvas-das-contas-de-2020-do-governador.html/Noticia/1111626070', ['ressalvas', 'pandemia', 'mínimos constitucionais']),
    ('tcu-2024', 'Contas federais de 2024 — relatório técnico', 'https://sites.tcu.gov.br/recursos/contas-do-presidente-2024/1%20Relat%C3%B3rio%20CG2024.pdf', ['Luiz Inácio Lula', 'metas fiscais', 'renúncias']),
    ('senado-flavio', 'Histórico de mandato legislativo', 'https://www25.senado.leg.br/web/senadores/senador/-/perfil/5894', ['Senador - RJ', '2019', '2027']),
]


def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'PresidenteIAResearch/1.0', 'Accept-Encoding': 'identity'}), timeout=60) as response:
        raw = response.read(40_000_001)
    if len(raw) > 40_000_000:
        raise ValueError('Limite de coleta de 40 MB excedido')
    return gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw


def record(url, raw):
    return {'url': url, 'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def collect():
    output = {'schema_version': 1, 'classification': 'historical_descriptive_not_causal',
              'retrieved_at': datetime.now(timezone.utc).isoformat(), 'series': [], 'sources': [], 'errors': []}
    # Mesmas pesquisas/variáveis/períodos para Brasil, Minas Gerais e Goiás.
    for aggregate, variable in [(6468, 4099), (6472, 5933), (5938, 37)]:
        metadata_url = f'https://servicodados.ibge.gov.br/api/v3/agregados/{aggregate}/metadados'
        try:
            metadata_raw = fetch(metadata_url)
            metadata = json.loads(metadata_raw)
            spec = next(v for v in metadata['variaveis'] if v['id'] == variable)
            for territory in ['N1[1]', 'N3[31,52]']:
                url = (f'https://servicodados.ibge.gov.br/api/v3/agregados/{aggregate}/periodos/-40/variaveis/{variable}'
                       f'?localidades={territory}')
                raw = fetch(url)
                data = json.loads(raw)
                for result in data[0]['resultados']:
                    for series in result['series']:
                        observations = []
                        for period, value in sorted(series['serie'].items()):
                            if value in ['-', '...', '..', 'X', '']:
                                continue
                            observations.append({'period': period, 'value': float(value)})
                        if not observations:
                            raise ValueError('Série sem observações numéricas')
                        location = series['localidade']
                        output['series'].append(dict(record(url, raw),
                            id=f'{aggregate}-{variable}-{location["id"]}', aggregate=aggregate, variable=variable,
                            label=spec['nome'], unit=spec['unidade'], location=location['nome'],
                            location_id=location['id'], frequency=metadata['periodicidade']['frequencia'],
                            metadata_url=metadata_url, metadata_sha256=hashlib.sha256(metadata_raw).hexdigest(),
                            observations=observations))
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            output['errors'].append({'id': str(aggregate), 'error': str(exc), 'url': metadata_url})
    for key, title, url, needles in SOURCES:
        try:
            raw = fetch(url)
            if raw.startswith(b'%PDF'):
                import pymupdf
                with pymupdf.open(stream=raw, filetype='pdf') as doc:
                    pages = [(i + 1, p.get_text()) for i, p in enumerate(doc)]
            else:
                try:
                    text = raw.decode('utf-8')
                except UnicodeDecodeError:
                    text = raw.decode('latin1')
                text = re.sub(r'<(script|style)\b[^>]*>.*?</\1>', '', text, flags=re.S | re.I)
                pages = [(None, unescape(re.sub('<[^>]+>', ' ', text)))]
            excerpts = []
            for needle in needles:
                for page, text in pages:
                    text = ' '.join(text.split())
                    hit = text.casefold().find(needle.casefold())
                    if hit >= 0:
                        # Preservar só o trecho institucional necessário; não perfis pessoais completos.
                        excerpts.append({'page': page, 'searched': needle, 'quote': text[max(0, hit-100):hit+450]})
                        break
            output['sources'].append(dict(record(url, raw), id=key, title=title,
                                          excerpts=excerpts, status='retrieved' if excerpts else 'retrieved_no_matching_excerpt'))
        except (OSError, ValueError, KeyError) as exc:
            output['errors'].append({'id': key, 'url': url, 'error': str(exc)})
    return output


def write_report(data):
    from src.history import summarize_history
    from src.ranking import load_dossiers
    history = summarize_history(data)
    def display(value):
        return f'{value:.2f}' if value is not None else 'não disponível'
    lines = ['# Pesquisa ampliada — histórico e programas', '',
             f"Coleta: {data['retrieved_at']}", '',
             '## Escopo e limite de inferência', '',
             'Coleta descritiva reproduzível de fontes primárias. Não é revisão exaustiva dos governos, avaliação causal ou recomendação de voto. Não se transportam taxas de estados para resultados nacionais.',
             'A página HTML das Contas Regionais bloqueou acesso (403); a definição de PIB foi consultada diretamente na API oficial de metadados IBGE. O serviço de extração web não estava operacional; as fontes abaixo foram obtidas por HTTP direto.',
             'Os 199 excertos já catalogados foram reconferidos com tools/verify_sources.py; o resultado da verificação desta rodada deve acompanhar a entrega.', '',
             '## Séries comparáveis dentro de cada definição', '',
             'As diferenças abaixo são territoriais e descritivas, não efeitos de presidentes/governadores. O período inclui choques e eventuais sucessores. Renda real depende da base de preços da edição; PIB aqui é nominal. Não somar mudanças de unidades diferentes.', '',
             '| Território | Variável | Período final | Valor | Base 2018 | Diferença na unidade original |',
             '|---|---|---|---:|---:|---:|']
    for row in history['summaries']:
        lines.append(f"| {row['location']} | {row['label']} ({row['unit']}) | {row['last_period']} | {display(row['latest'])} | {display(row['baseline'])} ({row['baseline_period']}) | {display(row['change_baseline'])} |")
    lines += ['', 'Fontes das séries (mesmos agregados e variáveis para Brasil, MG e GO):']
    lines.extend(f"- {s['location']} — {s['label']}: {s['url']} (SHA256 {s['sha256']})" for s in data['series'])
    lines += ['', '## Histórico institucional: o que as fontes permitem afirmar', '',
              'Parecer prévio propõe ao Legislativo uma conclusão sobre contas de um exercício. Não é julgamento definitivo das contas pelo Legislativo, sentença penal, índice de honestidade ou prova de impacto social.',
              'TCU 2024, TCE-GO 2025 e TCE-MG 2020 têm exercícios e contextos diferentes; NÃO foram convertidos em notas comparáveis. O caso de MG inclui pandemia. Mandato legislativo de Flávio Bolsonaro não equivale a gestão executiva; não se atribuem a ele resultados do governo de Jair Bolsonaro.', '']
    for source in data['sources']:
        lines += [f"### {source['title']}", '', source['url'],
                  f"Coleta {source['retrieved_at']}; SHA256 {source['sha256']}; status {source['status']}.", '']
        for excerpt in source['excerpts']:
            lines.append(f"> {excerpt['quote']}" + (f" (p. {excerpt['page']})" if excerpt['page'] else ''))
        lines.append('')
    lines += ['## Revisão dos compromissos por candidatura', '',
              'Quantidades abaixo descrevem o corpus auditado, não qualidade ou completude do programa integral. Falta de histórico executivo uniformemente verificado permanece desconhecida; não vira nota zero. Custos declarados por candidatura não foram validados de modo independente.', '']
    for dossier in load_dossiers():
        evidence = {e['id']: e for e in dossier['evidence']}
        lines += [f"### {dossier['supplied_name']}", '',
                  f"Plano: {dossier['program_url']} — membro {dossier['program_archive_member']}; SHA256 {dossier['program_sha256']}.",
                  f"Compromissos quantitativos catalogados: {len(dossier['quantitative_commitments'])}. Metas são declarações, não entregas previstas."]
        for commitment in dossier['quantitative_commitments']:
            description = commitment.get('commitment', commitment.get('description', 'Compromisso declarado'))
            horizon = commitment.get('deadline', commitment.get('horizon_years', commitment.get('target_year')))
            citations = ', '.join(f"{eid} p.{evidence[eid]['page']}" for eid in commitment['evidence_ids'])
            lines.append(f"- {description}; prazo catalogado: {horizon if horizon is not None else 'não identificado no trecho'}; {citations}.")
        lines.append('')
    impacts = json.loads((ROOT/'research/impacts.json').read_text())
    lines += ['## Evidência empírica contextual e transportabilidade', '',
              'Os estudos já revisados não fornecem coeficientes universais transferíveis para os doze programas. Foram relidos os limites catalogados; não se fabricaram coeficientes para gerar um vencedor.', '']
    for study in impacts['empirical_context']:
        lines += [f"- {study['id']}: {study['url']} — {study['limitations']}"]
    lines += ['', '## Ranking permitido por estes insumos', '',
              'Implementado separadamente: ranking experimental de especificação DETECTADA na seleção auditada, com seis critérios saturados por eixo, dez eixos e pesos editoriais transparentes. Zero significa ausência de detecção nesta seleção, não inexistência no plano completo ou efeito zero de governo.',
              '100.000 análises variam pesos Dirichlet(1), não reamostram governos reais. A simulação macro de 100.000 trajetórias é outro experimento e não fornece efeitos diferenciais das candidaturas.',
              'O protocolo e os mapeamentos dos compromissos estão em research/ranking_protocol.json. A seleção desigual de excertos é uma limitação relevante que os pesos não resolvem.', '',
              '## O que falta para ranking de desempenho governamental', '',
              'Custos líquidos independentes por medida, cronogramas, restrições legislativas e federativas, modelos causais validados, contrafactuais e séries de exposição comparáveis para todas as candidaturas. Sem isso, não se apresenta ranking documental como previsão de melhor presidente.', '']
    if data['errors']:
        lines += ['## Fontes indisponíveis', ''] + [f"- {e['id']}: {e['error']} ({e['url']})" for e in data['errors']]
    (ROOT/'research/ANALISE-AMPLIADA.md').write_text('\n'.join(lines), encoding='utf-8')


def main():
    data = collect()
    target = ROOT/'research/government_history.json'
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
    write_report(data)
    print(json.dumps({'target': str(target), 'series': len(data['series']),
                      'sources': len(data['sources']), 'errors': data['errors']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
