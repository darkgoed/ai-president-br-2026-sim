"""Integração de evidências sem notas, impactos ou seleção por preferência."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile

from .knowledge import Registry, canonical, fingerprint
from .public_validation import validate_dataset, validate_embedded_fiscal, validate_embedded_social

POLICY = {
    'version': 'evidence-only-v2-validated-transformations', 'invented_impacts_allowed': False,
    'candidate_causal_effects': None, 'government_ranking': None,
    'missing_is_zero': False, 'party_or_name_enters_simulation': False,
    'legacy_documentary_ranking_status': 'deprecated_unequal_excerpt_selection_not_government_evidence',
    'principles': [
        'Documento oficial prova o registro da declaração, não a verdade de tudo que foi declarado.',
        'Proposta não é execução; execução orçamentária não é impacto; associação temporal não é causalidade.',
        'Número sem unidade explícita permanece no payload original; não inventar unidade para completar tabela.',
        'Dados territoriais não são atribuídos a candidatos, partidos, familiares ou sucessores.',
        'Não soma fontes duplicadas como observações independentes nem contagens de trechos como mérito.',
        'Simulação e backtest são artefatos condicionais ao modelo, nunca fatos sobre governos futuros.',
        'Cobertura não é completude: falas externas, custos independentes e histórico comparável continuam lacunas.'
    ]
}


def build_registry(root, output, simulation_dir='results-1m', publication=False, catalog_file='research/public_catalog.json'):
    root, output = Path(root), Path(output)
    sim_path = (root/simulation_dir).resolve()
    if not sim_path.is_relative_to(root.resolve()):
        raise ValueError('Simulação fora da raiz do projeto')
    if not (root/catalog_file).resolve().is_relative_to(root.resolve()):
        raise ValueError('Catálogo fora da raiz do projeto')
    manifest = []
    expected_ids = set()
    if publication:
        required = ['data/strategies.json', 'research/program_manifest.json', catalog_file, 'research/expanded_evidence.json',
                    'data/observed.json', 'data/empirical_monthly.json', '.cache/programs.zip',
                    str(Path(simulation_dir)/'empirical_results.json')]
        if any(not (root/p).is_file() for p in required):
            raise ValueError('Gate de publicação: fontes obrigatórias ausentes')
        manifest = json.loads((root/'research/program_manifest.json').read_text())
        expected_ids = {p['id'] for p in json.loads((root/'data/strategies.json').read_text())}
        actual_ids = [json.loads(p.read_text())['official_candidate_id'] for p in (root/'research/candidates').glob('*.json')]
        if (len(expected_ids) != 12 or len(actual_ids) != 12 or set(actual_ids) != expected_ids
                or not expected_ids <= {m['candidate_id'] for m in manifest}):
            raise ValueError('Gate de publicação: conjunto de 12 candidaturas não confere')
    output.mkdir(parents=True, exist_ok=True)
    registry = Registry(output/'evidence.sqlite')
    manifests, gaps, coverage, archive_extras = [], [], [], []

    def load(relative):
        path = root/relative
        raw = path.read_bytes()
        data = json.loads(raw)
        source = registry.source(relative, raw)
        manifests.append({'path': relative, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
        return data, source

    def missing(relative):
        gaps.append({'source': relative, 'reason': 'not_collected_in_this_build'})

    dossiers = []
    for path in sorted((root/'research/candidates').glob('*.json')):
        data, source = load(str(path.relative_to(root)))
        candidate = data['official_candidate_id']
        registry.candidate(candidate, data['supplied_name'], data['verified_party'])
        dossiers.append(data)
        evidences = {e['id']: e for e in data['evidence']}
        for index, evidence in enumerate(data['evidence']):
            kind = 'official_identity' if evidence['classification'] == 'official_tse_dataset' else 'official_declaration'
            registry.add(kind, source, f'/evidence/{index}', evidence.get('claim', 'Trecho de documento'),
                         evidence, candidate_id=candidate, text=evidence['quote'])
        for axis, proposals in data['axes'].items():
            for index, proposal in enumerate(proposals):
                if not set(proposal['evidence_ids']) <= evidences.keys():
                    raise ValueError('Proposta com evidência ausente')
                registry.add('official_declaration', source, f'/axes/{axis}/{index}', f'{axis}: proposta catalogada',
                             proposal, candidate_id=candidate, text=proposal['statement'])
        for index, commitment in enumerate(data['quantitative_commitments']):
            if not set(commitment['evidence_ids']) <= evidences.keys():
                raise ValueError('Compromisso com evidência ausente')
            registry.add('official_declaration', source, f'/quantitative_commitments/{index}', 'Meta declarada, não entrega',
                         commitment, candidate_id=candidate, text=canonical(commitment))
        for field in ['administrative_history', 'legal_constraints', 'unknowns', 'searches']:
            for index, item in enumerate(data.get(field, [])):
                registry.add('missing' if field == 'unknowns' else 'contextual_analysis', source,
                             f'/{field}/{index}', field, item, candidate_id=candidate, text=canonical(item))
        coverage.append({'id': candidate, 'name': data['supplied_name'], 'party': data['verified_party'],
                         'sampled_excerpts': len(data['evidence']), 'catalogued_targets': len(data['quantitative_commitments']),
                         'missing_items': len(data['unknowns']), 'pages_fulltext': None})

    # Todas as páginas dos mesmos planos, com hashes conferidos antes da extração.
    archive_path = root/'.cache/programs.zip'
    if archive_path.exists():
        import pymupdf
        with zipfile.ZipFile(archive_path) as archive:
            for dossier in dossiers:
                pdf = archive.read(dossier['program_archive_member'])
                if hashlib.sha256(pdf).hexdigest() != dossier['program_sha256']:
                    raise ValueError('PDF alterado; interrompendo integração')
                with pymupdf.open(stream=pdf, filetype='pdf') as doc:
                    pages = [p.get_text() for p in doc]
                if publication:
                    import re
                    def norm(text):
                        return ' '.join(re.sub(r'(\w)-\s+(\w)', r'\1\2', text).split()).replace('ﬁ', 'fi').replace('ﬂ', 'fl')
                    spec = next(m for m in manifest if m['candidate_id'] == dossier['official_candidate_id'])
                    if spec['sha256'] != dossier['program_sha256'] or spec['pages'] != len(pages):
                        raise ValueError('PDF diverge do manifesto oficial arquivado')
                    for evidence in dossier['evidence']:
                        page = evidence.get('page')
                        if page is not None:
                            quote = norm(evidence['quote']).rstrip('…').rstrip('.')
                            if not 1 <= page <= len(pages) or quote not in norm(pages[page-1]):
                                raise ValueError('Citação não confere na página original: '+evidence['id'])
                    candidate_coverage = next(c for c in coverage if c['id'] == dossier['official_candidate_id'])
                    candidate_coverage['verified_program_quote_ids'] = [e['id'] for e in dossier['evidence'] if e.get('page') is not None]
                    candidate_coverage['verified_program_quote_count'] = len(candidate_coverage['verified_program_quote_ids'])
                    candidate_coverage['blank_extracted_pages'] = sum(not p.strip() for p in pages)
                    candidate_coverage['extracted_characters'] = sum(len(p) for p in pages)
                raw = canonical({'archive_member': dossier['program_archive_member'],
                                 'pdf_sha256': dossier['program_sha256'], 'pages': pages}).encode()
                source = registry.source('tse-pdf-text:'+dossier['program_archive_member'], raw,
                    url=dossier['program_url'], verification='pdf_hash_matches_dossier_then_text_extracted')
                for index, page in enumerate(pages):
                    registry.add('document_page', source, f'/pages/{index}', f'Plano integral — página {index+1}',
                                 {'page': index+1, 'quote': page, 'pdf_sha256': dossier['program_sha256']},
                                 candidate_id=dossier['official_candidate_id'], text=page)
                next(c for c in coverage if c['id'] == dossier['official_candidate_id'])['pages_fulltext'] = len(pages)
            # Não ocultar documentos do arquivo oficial fora dos perfis do modelo.
            for spec in manifest:
                if spec['candidate_id'] in expected_ids:
                    continue
                pdf = archive.read(spec['archive_member'])
                if hashlib.sha256(pdf).hexdigest() != spec['sha256']:
                    raise ValueError('Documento adicional diverge do manifesto')
                with pymupdf.open(stream=pdf, filetype='pdf') as doc:
                    extra_pages = [p.get_text() for p in doc]
                if len(extra_pages) != spec['pages']:
                    raise ValueError('Paginação adicional diverge do manifesto')
                raw = canonical({'archive_member': spec['archive_member'], 'pdf_sha256': spec['sha256'], 'pages': extra_pages}).encode()
                extra_source = registry.source('tse-pdf-text:'+spec['archive_member'], raw,
                    url=spec['url'], verification='pdf_hash_matches_archive_manifest_then_text_extracted')
                for i, page in enumerate(extra_pages):
                    registry.add('document_page', extra_source, f'/pages/{i}',
                        'Documento adicional do arquivo — página '+str(i+1),
                        {'page': i+1, 'quote': page, 'pdf_sha256': spec['sha256'], 'archive_candidate_id': spec['candidate_id'],
                         'scope': 'outside_configured_candidate_profiles_not_a_new_government_forecast'},
                        entity='Documento do arquivo: '+spec['candidate_id'], text=page)
                archive_extras.append({'archive_candidate_id': spec['candidate_id'], 'pages': len(extra_pages), 'sha256': spec['sha256']})
    else:
        missing('.cache/programs.zip')

    # Séries observadas: a mesma política de importação para todos os territórios.
    def series_records(series, source, prefix, payload_key='observations', unit=None, label=None, entity=None, kind='observed'):
        for index, row in enumerate(series.get(payload_key, [])):
            value = row.get('value')
            explicit_unit = row.get('unit', unit if unit is not None else series.get('unit'))
            registry.add('missing' if value is None else kind, source, f'{prefix}/{payload_key}/{index}',
                         label or series.get('label', series.get('id', 'Série observada')), row,
                         entity=row.get('entity', entity or series.get('location', 'Brasil')),
                         period=row.get('period', row.get('date', row.get('year'))), unit=explicit_unit,
                         value=value if explicit_unit else None,
                         text=canonical({k: v for k, v in series.items() if k not in {'observations', 'chunks', 'raw_json'}}))

    for relative in ['data/observed.json', 'data/empirical_monthly.json', 'research/government_history.json']:
        if not (root/relative).exists():
            missing(relative)
            continue
        data, source = load(relative)
        if relative == 'data/observed.json':
            from .observed import validate_snapshot
            validate_snapshot(data)
        elif relative == 'data/empirical_monthly.json':
            from .empirical_data import validate_snapshot
            validate_snapshot(data)
        for index, series in enumerate(data['series']):
            series_records(series, source, f'/series/{index}',
                           kind='contextual_analysis' if relative == 'research/government_history.json' else 'observed')
        for index, error in enumerate(data.get('errors', [])):
            registry.add('missing', source, f'/errors/{index}', 'Fonte indisponível', error, text=canonical(error))
            gaps.append(error)
        for index, institution in enumerate(data.get('sources', [])):
            registry.add('contextual_analysis', source, f'/sources/{index}', institution.get('title', 'Fonte institucional'),
                         institution, text=canonical(institution))

    for relative, public in [('research/expanded_evidence.json', False), (catalog_file, True)]:
        if not (root/relative).exists():
            missing(relative)
            continue
        data, source = load(relative)
        if public:
            for index, dataset in enumerate(data['datasets']):
                # Valida também os bytes remotos arquivados, não apenas o JSON normalizado.
                raw = validate_dataset(root, dataset)
                response_id = registry.source(dataset['response_path'], raw, dataset['url'], dataset['retrieved_at'], 'response_sha256_verified')
                registry.add('methodology', source, f'/datasets/{index}/metadata', dataset['label'],
                             {k:v for k,v in dataset.items() if k != 'observations'}, text=dataset['label'])
                if dataset['provider'] == 'Tesouro/Siconfi':
                    for j, row in enumerate(dataset['observations']):
                        registry.add('observed', response_id, f'/items/{j}', row['conta'], row,
                                     entity=row['instituicao'], period=str(row['exercicio']),
                                     text=row['coluna']+' '+row['cod_conta'])
                else:
                    series_records(dataset, source, f'/datasets/{index}')
        else:
            for index, report in enumerate(data['fiscal_reports']):
                validate_embedded_fiscal(report)
                raw = report['raw_json'].encode()
                if hashlib.sha256(raw).hexdigest() != report['sha256']:
                    raise ValueError('Hash do RREO alterado')
                report_id = registry.source(f'{relative}#fiscal_reports/{index}', raw, report['url'], report['retrieved_at'], 'response_sha256_verified')
                for j, row in enumerate(report['items']):
                    registry.add('observed', report_id, f'/items/{j}', row['conta'], row,
                                 entity=row['instituicao'], period=str(row['exercicio']), text=row['coluna']+' '+row['cod_conta'])
            for index, series in enumerate(data['social_indicators']):
                validate_embedded_social(series)
                series_records(series, source, f'/social_indicators/{index}')
            for index, program in enumerate(data['programs']):
                for j, axis in enumerate(program['axes']):
                    registry.add('automated_mention', source, f'/programs/{index}/axes/{j}',
                                 'Menções para revisão: '+axis['axis'], axis, candidate_id=program['id'], text=canonical(axis))
            for index, institution in enumerate(data['sources']):
                registry.add('contextual_analysis', source, f'/sources/{index}', 'Fonte consultada: '+institution['id'],
                             institution, text=canonical(institution))
        for index, error in enumerate(data.get('errors', [])):
            registry.add('missing', source, f'/errors/{index}', 'Fonte pendente', error, text=canonical(error))
            gaps.append(error)

    # Análises qualitativas preservadas como tais; não são efeitos medidos.
    relative = 'research/impacts.json'
    if (root/relative).exists():
        impacts, source = load(relative)
        for i, dossier in enumerate(impacts['dossiers']):
            for j, proposal in enumerate(dossier['proposals']):
                if proposal['quantified_population_effect'] is not None:
                    raise ValueError('Impacto sem identificação: não admitido na base integrada')
                registry.add('contextual_analysis', source, f'/dossiers/{i}/proposals/{j}',
                             'Canal conceitual, não efeito: '+proposal['axis'], proposal,
                             candidate_id=dossier['candidate_id'], text=canonical(proposal))
        for index, study in enumerate(impacts['empirical_context']):
            registry.add('contextual_analysis', source, f'/empirical_context/{index}', 'Evidência contextual: '+study['id'], study, text=canonical(study))

    for relative in ['data/strategies.json', 'research/electoral_sources.json', 'research/empirical_sources.json',
                     'research/method_sources.json', 'research/audit_checks.json', 'research/program_manifest.json']:
        if (root/relative).exists():
            data, source = load(relative)
            registry.add('methodology', source, '', relative, data, text=canonical(data))
    # Preservar a existência do erro metodológico anterior, sem recalcular vencedores.
    legacy = root/'results-100k/ranking.json'
    if legacy.exists():
        data, source = load('results-100k/ranking.json')
        registry.add('legacy_deprecated', source, '', 'Ranking documental anterior — não usar como evidência de melhor governo',
                     {'status': POLICY['legacy_documentary_ranking_status'], 'original': data},
                     text='Seleção desigual de trechos; pesos editoriais; classificação não validada para governos.')

    # Integração dos dois experimentos como simulações, sem misturá-los a observações.
    metrics_path = root/'results-100k/metrics.csv'
    if metrics_path.exists():
        raw = metrics_path.read_bytes()
        source = registry.source('results-100k/metrics.csv', raw, verification='historical_artifact_hash_not_real_world_validation')
        for index, metric in enumerate(csv.DictReader(raw.decode().splitlines())):
            registry.add('simulated', source, f'/csv/{index+2}', 'Stress artificial: '+metric['label'], metric,
                         unit=metric['unit'], value=float(metric['value']), text=metric['definition'])

    simulation = None
    relative = str(Path(simulation_dir)/'empirical_results.json')
    if (root/relative).exists():
        simulation, source = load(relative)
        if simulation['candidate_effects_identified'] or simulation['government_ranking'] is not None:
            raise ValueError('Resultado não compatível com política sem impactos inventados')
        for metric, summary in simulation['summary'].items():
            registry.add('simulated', source, f'/summary/{metric}', 'Bootstrap histórico: '+summary['label'], summary,
                         unit=summary['unit'], value=summary['final']['median'], text=canonical(summary))
        for index, annual in enumerate(simulation['annual']):
            registry.add('simulated', source, f'/annual/{index}', 'Bootstrap histórico: ano '+str(annual['year']), annual, text=canonical(annual))
        registry.add('methodology', source, '/backtest', 'Backtest — inclui falhas contra baseline', simulation['backtest'], text=canonical(simulation['backtest']))
    else:
        missing(relative)
    if publication:
        from .analysis_suite import build_analysis
        analysis = build_analysis(root, output/'analysis', simulation_dir, catalog_file=catalog_file)
        analysis_path = str((output/'analysis/analysis.json').resolve().relative_to(root.resolve()))
        _, analysis_source = load(analysis_path)
        for index, group in enumerate(analysis['series_groups']):
            registry.add('contextual_analysis', analysis_source, f'/series_groups/{index}',
                         'Estatística temporal descritiva: '+group['label'], group,
                         entity=group['entity'], text=canonical(group))
            for j, comparison in enumerate(group['comparisons']):
                registry.add('derived_observation', analysis_source, f'/series_groups/{index}/comparisons/{j}',
                             'Variação no mesmo período do ano anterior: '+group['label'], comparison,
                             entity=group['entity'], period=comparison['period'], unit=comparison['unit'],
                             value=comparison['difference'], text=canonical({'source': group['source'], 'comparison': comparison}))
        for index, metric in enumerate(analysis['simulated_metrics']):
            registry.add('simulated', analysis_source, f'/simulated_metrics/{index}', metric['label'], metric,
                         unit=metric['unit'], value=metric['summary']['median'], text=canonical(metric))
        registry.add('methodology', analysis_source, '/multi_horizon_backtest',
                     'Backtest 12, 24 e 48 meses; baselines e intervalos', analysis['multi_horizon_backtest'],
                     text=canonical(analysis['multi_horizon_backtest']))
    report = {'schema_version': 2, 'created_at': datetime.now(timezone.utc).isoformat(),
              'publication_gate': publication, 'simulation_directory': simulation_dir, 'catalog_file': catalog_file,
              'policy': POLICY, 'government_ranking': None, 'counts': registry.counts(),
              'coverage': {'candidates': coverage, 'known_unequal_excerpt_selection': True,
                           'additional_archive_documents': archive_extras,
                           'scope': 'Todas as fontes estruturadas listadas neste manifesto e páginas dos 12 planos; não é todo conhecimento político existente.',
                           'missing': gaps, 'duplicated_sources_are_not_independent_observations': True},
              'simulation': simulation, 'inputs': manifests}
    report['coverage']['historical_snapshot_verification'] = 'government_history lacks raw responses; retained as context, not newly validated observations'
    report['bundle_id'] = fingerprint({'inputs': manifests, 'policy': POLICY, 'counts': report['counts']})
    registry.connection.commit()
    if registry.connection.execute('pragma foreign_key_check').fetchall():
        raise ValueError('Referências quebradas na base')
    # JSONL preserva a mesma base em formato amigável a diff e auditoria Git.
    with (output/'records.jsonl').open('w') as f:
        cursor = registry.connection.execute('select * from records order by id')
        keys = [d[0] for d in cursor.description]
        for row in cursor:
            f.write(canonical(dict(zip(keys, row)))+'\n')
    with (output/'sources.jsonl').open('w') as f:
        cursor = registry.connection.execute('select * from sources order by id')
        keys = [d[0] for d in cursor.description]
        for row in cursor:
            f.write(canonical(dict(zip(keys, row)))+'\n')
    from .knowledge_dashboard import write_dashboard
    write_dashboard(registry, report, output)
    registry.close()
    artifacts = ['evidence.sqlite', 'records.jsonl', 'sources.jsonl', 'dashboard.html', 'catalog-data.js', 'catalog.js']
    if publication:
        artifacts += ['analysis/analysis.json', 'analysis/RELATORIO.md', 'analysis/observed_comparisons.csv',
                      'analysis/simulated_metrics.csv', 'analysis/backtest_scores.csv']
    report['artifact_sha256'] = {name: hashlib.sha256((output/name).read_bytes()).hexdigest() for name in artifacts}
    (output/'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    return report
