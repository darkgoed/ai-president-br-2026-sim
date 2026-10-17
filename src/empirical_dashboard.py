"""Painel leve do modo empírico, distinto do ranking documental anterior."""
import csv
from html import escape
import json
from pathlib import Path


def export_empirical(result, backtest, output, evidence=None):
    output = Path(output)
    evidence = evidence or {'programs': [], 'fiscal_reports': [], 'social_indicators': [], 'sources': [], 'errors': []}
    result['backtest'] = backtest
    result['evidence_summary'] = {'full_programs_scanned': len(evidence['programs']),
        'pages_scanned': sum(p['pages_scanned'] for p in evidence['programs']),
        'fiscal_reports': len(evidence['fiscal_reports']), 'social_indicators': len(evidence['social_indicators']),
        'source_errors': evidence['errors'],
        'use': 'context_and_review_queue_not_causal_coefficients'}
    (output/'empirical_results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    (output/'backtest.json').write_text(json.dumps(backtest, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    (output/'evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    with (output/'summary.csv').open('w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['id', 'label', 'unit', 'mean', 'median', 'q025', 'q975', 'numerical_mc_se'])
        for row in result['summary'].values():
            writer.writerow([row['id'], row['label'], row['unit'], *[row['final'][k] for k in ['mean', 'median', 'q025', 'q975']], row['numerical_mc_se']])
    esc = lambda value: escape(str(value), quote=True)
    def num(value):
        return 'Não disponível' if value is None else f'{value:,.3f}'.replace(',', '_').replace('.', ',').replace('_', '.')
    summary_rows = ''.join(f'<tr><th>{esc(s["label"])}</th><td>{esc(s["unit"])}</td><td>{num(s["final"]["median"])}</td><td>{num(s["final"]["q025"])}</td><td>{num(s["final"]["q975"])}</td><td>{num(s["numerical_mc_se"])}</td></tr>' for s in result['summary'].values())
    annual_rows = ''.join(f'<tr><td>{a["year"]}</td>' + ''.join(f'<td>{num(s["median"])}</td>' for s in a['metrics'].values()) + '</tr>' for a in result['annual'])
    backtest_rows = ''.join(f'<tr><th>{esc(key)}</th><td>{num(s.get("bootstrap_mae"))}</td><td>{num(s.get("baseline_mae"))}</td><td>{num(s.get("mae_skill_vs_no_change"))}</td><td>{num(s.get("coverage_95_pct"))}</td></tr>' for key, s in backtest['by_metric'].items())
    program_cards = ''
    for program in evidence['programs']:
        axis_rows = ''
        examples = ''
        for axis in program['axes']:
            axis_rows += f'<tr><td>{esc(axis["axis"])}</td><td>{len(axis["topic_pages"])}</td>' + ''.join(f'<td>{m["count"]}</td>' for m in axis['mentions'].values()) + '</tr>'
            for marker, mentions in axis['mentions'].items():
                for e in mentions['examples']:
                    examples += f'<p><b>{esc(axis["axis"])} / {esc(marker)}, p.{e["page"]}</b>: {esc(e["quote"])}</p>'
        program_cards += (f'<details><summary>{esc(program["name"])} — {program["pages_scanned"]} páginas examinadas</summary>'
            f'<p>{esc(program["warning"])}</p><p><a href="{esc(program["url"])}">Fonte TSE</a>; membro {esc(program["archive_member"])}; SHA256 {esc(program["sha256"])}</p>'
            f'<div class="scroll"><table><tr><th>Eixo</th><th>Páginas temáticas</th><th>Números</th><th>Prazos</th><th>Recursos</th><th>Instrumentos</th><th>Monitoramento</th></tr>{axis_rows}</table></div><details><summary>Trechos para revisão semântica — não são promessas confirmadas</summary>{examples}</details></details>')
    fiscal_rows = ''
    codes = ['ReceitasRealizadasDemonstrativoSimplificadoBalancoOrcamentario', 'DespesasEmpenhadasDemonstrativoSimplificadoBalancoOrcamentario', 'DespesasLiquidadasDemonstrativoSimplificadoBalancoOrcamentario', 'DespesasPagasDemonstrativoSimplificadoBalancoOrcamentario']
    for report in evidence['fiscal_reports']:
        for row in report['items']:
            if row['cod_conta'] in codes:
                fiscal_rows += f'<tr><td>{esc(row["instituicao"])}</td><td>{report["year"]}</td><td>{esc(row["conta"])}</td><td>{num(row["valor"])}</td><td><a href="{esc(report["url"])}">RREO</a></td></tr>'
    social_rows = ''
    for series in evidence['social_indicators']:
        valid = sorted((r for r in series['observations'] if r['value'] is not None), key=lambda r: r['year'])
        if valid:
            last = valid[-1]
            social_rows += f'<tr><td>{esc(series["label"])}</td><td>{last["year"]}</td><td>{num(last["value"])}</td><td><a href="{esc(series["url"])}">Fonte Banco Mundial</a></td></tr>'
    source_rows = ''.join(f'<li>{esc(s["id"])}: <a href="{esc(s["url"])}">fonte consultada</a> — uso contextual, não coeficiente causal.</li>' for s in evidence['sources'])
    error_rows = ''.join(f'<li>{esc(e["id"])}: {esc(e["error"])}</li>' for e in evidence['errors'])
    limits = ''.join(f'<li>{esc(x)}</li>' for x in result['limitations'])
    worse = [result['summary'][key]['label'] for key, stats in backtest['by_metric'].items()
             if stats.get('mae_skill_vs_no_change') is not None and stats['mae_skill_vs_no_change'] < 0]
    backtest_alert = ('<div class="notice">No backtest desta execução, o modelo foi pior que manter o nível inicial para: '
                      + esc(', '.join(worse)) + '. Mais simulações não corrigem essa falha preditiva.</div>') if worse else ''
    html = f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Presidente IA — simulação empírica</title>
<style>body{{font:16px system-ui;background:#101722;color:#edf2f7;max-width:1200px;margin:auto;padding:24px;overflow-wrap:anywhere}}a{{color:#7dd3fc}}.notice,details{{background:#1d2939;padding:18px;border-radius:10px;margin:16px 0;overflow-wrap:anywhere}}.notice{{border-left:4px solid #fbbf24}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;min-width:650px}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #394558}}h2{{margin-top:40px}}p,li{{line-height:1.55}}</style>
<h1>Presidente IA — {result['counts'].get('sampled_paths', result['counts'].get('unique_paths')):,} trajetórias históricas reamostradas</h1>
<div class="notice">Não é ranking de governos. Este modo usa histórico observado conjunto para dívida, desocupação, atividade e preços. Não atribui promessas, resultados de familiares ou pontuação documental a efeitos econômicos de candidatos.</div>
<p>Histórico comum: {esc(result['history_start'])} a {esc(result['initial_reference'])}; {result['counts']['historical_months']} meses e {result['counts']['available_annual_blocks']} blocos históricos sobrepostos de 12 meses. Horizonte: quatro anos. Seed: {result['parameters']['seed']}. Blocos sorteados com reposição em lotes; não são novos estudos ou dados independentes.</p>
<h2>Distribuição condicional ao bootstrap — fim do horizonte</h2><div class="scroll"><table><tr><th>Indicador</th><th>Unidade</th><th>Mediana</th><th>Percentil 2,5</th><th>Percentil 97,5</th><th>Erro numérico da média</th></tr>{summary_rows}</table></div>
<p>Preços começam em 100 no mês-base. Percentis descrevem o laboratório, não confiança validada em governos. IBC-Br é índice de atividade, não PIB. Erro numérico não inclui erro estrutural.</p>
<h2>Trajetória mediana — valores em cada ano, não uma trajetória individual</h2><div class="scroll"><table><tr><th>Ano</th><th>Dívida (% PIB)</th><th>Desocupação (%)</th><th>IBC-Br (índice)</th><th>Preços (base 100)</th></tr>{annual_rows}</table></div>
<h2>Backtest histórico e baseline ingênuo</h2>{backtest_alert}<p>{esc(backtest['warning'])}</p><p>Cortes avaliados: {backtest['counts']['origins']}; horizonte de teste: 12 meses; {backtest['counts']['paths_per_origin']} trajetórias por corte. Baseline: repetir o nível inicial (preços = 100, inflação futura zero).</p><div class="scroll"><table><tr><th>Indicador</th><th>MAE bootstrap</th><th>MAE baseline</th><th>Skill MAE (negativo = pior)</th><th>Cobertura de faixa 95% (%)</th></tr>{backtest_rows}</table></div>
<h2>Planos completos — busca uniforme, sem vencedor automático</h2><p>Foram examinados {len(evidence['programs'])} planos, {sum(p['pages_scanned'] for p in evidence['programs'])} páginas. Menção a números ou prazo pode ser diagnóstico, negação ou citação: não foi convertida em promessa validada, efeito ou nota. O ranking anterior continua sendo exploratório e baseado em seleção desigual; não é reutilizado aqui.</p>{program_cards}
<h2>Execução orçamentária observada — Siconfi</h2><p>Valores nominais em R$, não corrigidos pela inflação. Entes, competências e escalas diferem; não somar anos nem usar total nominal como nota. Empenho não equivale a pagamento nem entrega social. Fonte reportada pelo ente ao Tesouro, sujeita a revisões.</p><div class="scroll"><table><tr><th>Ente</th><th>Ano</th><th>Conta</th><th>R$ nominais</th><th>Fonte</th></tr>{fiscal_rows}</table></div>
<h2>Indicadores sociais adicionais — contexto, não calibração causal</h2><p>Banco Mundial republica estatísticas/estimativas de produtores internacionais; ausências permanecem null. Não substituímos a fonte DATASUS por números inventados. Não entram nas quatro equações deste bootstrap.</p><div class="scroll"><table><tr><th>Indicador (unidade no nome)</th><th>Ano</th><th>Valor</th><th>Fonte</th></tr>{social_rows}</table></div>
<h2>Fontes consultadas e limitações</h2><ul>{source_rows}</ul><h3>Fontes pendentes ou indisponíveis</h3><ul>{error_rows}</ul><ul>{limits}</ul>
<p>Coleta de Câmara/Senado confirma acesso/contexto, não constitui auditoria integral da atuação parlamentar. O portal Inep/DATASUS consultado não significa microdados incorporados. Falta de dados executivos comparáveis não vira nota zero.</p>
<h2>Reproduzir e auditar</h2><p>Run ID: {esc(result['run_id'])}</p><p><a href="empirical_results.json">Resultados JSON</a> | <a href="summary.csv">Resumo CSV</a> | <a href="backtest.json">Backtest</a> | <a href="evidence.json">Evidências</a> | <a href="paths.npy">Todas as trajetórias NumPy</a> | <a href="block_indices.npy">Blocos sorteados</a></p></html>'''
    (output/'dashboard.html').write_text(html, encoding='utf-8')
