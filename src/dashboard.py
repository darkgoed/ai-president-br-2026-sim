"""Relatório HTML local, sem rede, scripts ou dependências adicionais."""
from html import escape


def dashboard(result):
    def esc(value):
        return escape(str(value), quote=True)

    def number(value):
        return f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')

    def percent(value):
        return '&lt;0,01%' if 0 < value < .01 else esc(number(value)) + '%'

    def card(label, value, unit, detail, chart=''):
        return f'<article><h3>{esc(label)}</h3><strong>{esc(number(value))}</strong> <span>{esc(unit)}</span><p>{esc(detail)}</p>{chart}</article>'

    def sparkline(values, title):
        low, high = min(values), max(values)
        points = ' '.join(f'{10 + i * 280 / max(1, len(values)-1):.2f},{70 - (v-low) * 60 / (high-low or 1):.2f}' for i, v in enumerate(values))
        return f'<svg viewBox="0 0 300 85" style="display:block;width:100%;height:auto" role="img" aria-label="{esc(title)}"><title>{esc(title)} — mínimo {esc(number(low))}, máximo {esc(number(high))}</title><polyline points="{points}" fill="none" stroke="#7dd3fc" stroke-width="2.5"/></svg>'

    reference = result['reference']
    source = result.get('initial_debt_source')
    baseline = (f"Dívida inicial observada: {number(source['value'])}% PIB, referência {esc(source['date'])}, SGS {source['sgs_id']}."
                if source else 'Dívida inicial hipotética, conforme configuração do benchmark.')
    metrics = reference.get('metrics', {})
    cards = ''.join(card(m['label'], m['value'], m['unit'], m['definition']) for m in metrics.get('indicators', []) if not m['id'].startswith('year_'))
    annual_indicators = [m for m in metrics.get('indicators', []) if m['id'].startswith('year_')]
    annual_cards = ''.join(card(m['label'], m['value'], m['unit'], m['definition']) for m in annual_indicators)
    observed = result.get('observed', {})
    real_cards = ''
    for series in observed.get('series', []):
        last = series['observations'][-1]
        stats = series['statistics']
        detail = '<details><summary>Histórico, variações e fonte</summary>'
        detail += f"<p>Coleta: {esc(observed['retrieved_at'])}. Janela: {esc(stats['first_date'])} a {esc(stats['last_date'])}; {stats['n']} observações.</p>"
        for key, label in [('previous', 'Valor anterior'), ('change', 'Variação na unidade original'),
                           ('mean', 'Média na janela'), ('min', 'Mínimo na janela'), ('max', 'Máximo na janela')]:
            value = stats.get(key)
            detail += f'<p>{esc(label)}: {esc(number(value)) if value is not None else "Indisponível"} {esc(series["unit"])}</p>'
        detail += f'<p><a href="{esc(series["url"])}">Dados oficiais</a> | SHA256: {esc(series["sha256"])}</p></details>'
        real_cards += card(series['label'], last['value'], series['unit'],
                           f"Referência: {last['date']} | Fonte: {series['producer']} via BCB/SGS {series['sgs_id']}",
                           sparkline([r['value'] for r in series['observations']], series['label'] + ' — histórico na janela, escala própria') + detail)
    if not real_cards:
        real_cards = '<p>Sem snapshot oficial nesta execução. Execute refresh-data e simule novamente. Nenhum valor foi inventado.</p>'
    errors = ''.join(f'<li>{esc(x["id"])}: {esc(x["error"])}</li>' for x in observed.get('errors', []))
    annual = metrics.get('annual', [])
    chart = sparkline([result['parameters']['initial_debt'] * 100] + [r['debt_mean_pct_gdp'] for r in annual], 'Dívida média hipotética em % PIB, do ano zero ao fim do horizonte') if annual else ''
    table = ''.join(f'<tr><td>{r["year"]}</td><td>{number(r["debt_mean_pct_gdp"])}</td><td>{number(r["debt_q10_pct_gdp"])} – {number(r["debt_q90_pct_gdp"])}</td><td>{number(r["change_mean_pp"])}</td><td>{number(r["interest_cost_mean_pct_gdp"])}</td><td>{number(r["stabilizing_primary_mean_pct_gdp"])}</td></tr>' for r in annual)
    scenario_rows = ''.join(f'<tr><td>{esc(key)}</td><td>{stats["n"]}</td><td>{number(stats["mean"])}</td><td>{number(stats["q025"])} – {number(stats["q975"])}</td></tr>' for key, stats in reference['by_scenario'].items())
    diagnostics_section = ''
    diagnostic = result.get('diagnostics')
    if diagnostic:
        def precision(value):
            return 'Não estimado' if value is None else (str(value) if isinstance(value, int) else f'{value:.5f}'.replace('.', ','))

        diagnostic_rows = ''.join(f'<tr><th scope="row">{esc(i["label"])}</th><td>{precision(i["value"])}</td><td>{esc(i["unit"])}</td></tr>' for i in diagnostic['indicators'])
        convergence_rows = ''.join(f'<tr><td>{c["runs"]}</td><td>{precision(c["mean_pct_gdp"])}</td><td>{precision(c["mc_se_pp_gdp"])}</td><td>{precision(c["delta_from_full_pp"])}</td></tr>' for c in diagnostic['macro']['convergence'])
        source_rows = ''.join(f'<tr><td>{esc(s["id"])}</td><td>{esc(s["frequency"])}</td><td>{esc(s["last_reference_date"])}</td><td>{precision(s["days_since_reference_date"])}</td><td>{esc(s["status"])}</td></tr>' for s in diagnostic['data_quality']['series'])
        method_section = ''
        method = diagnostic['ranking']
        if method:
            names = {c['id']: c['name'] for c in result['experimental_ranking']['candidates']}
            fragility_rows = ''.join(f'<tr><th scope="row">{esc(c["name"])}</th><td>{c["baseline_position"]}</td><td>{c["best_position"]}–{c["worst_position"]}</td><td>{c["max_position_shift"]}</td></tr>' for c in method['candidate_fragility'])
            variant_rows = ''.join(f'<tr><td>{esc(v["removed_dimension"])}</td><td>{esc(v["removed"])}</td><td>{esc(", ".join(names[i] for i in v["leaders"]))}</td></tr>' for v in method['variants'])
            method_section = (f'<h3>Dependência do método do ranking</h3><p>{esc(method["warning"])}</p>'
                f'<div class="scroll"><table><tr><th>Candidatura</th><th>Posição original</th><th>Faixa nas retiradas</th><th>Maior deslocamento</th></tr>{fragility_rows}</table></div>'
                f'<details><summary>Resultados de cada retirada metodológica</summary><div class="scroll"><table><tr><th>Tipo</th><th>Removido</th><th>Conjunto líder</th></tr>{variant_rows}</table></div></details>')
        small_sample = '<p>Atenção: há famílias pequenas; a aproximação normal pode ser inadequada.</p>' if diagnostic['macro']['normal_approximation_small_strata'] else ''
        diagnostics_section = (f'<section id="diagnosticos"><h2>Fragilidade e erro numérico</h2><p>Diagnóstico em {esc(diagnostic["as_of"])}.</p>'
            f'<div class="notice">{esc(diagnostic["validation"]["warning"])} Não há percentual validado de chance de erro real.</div>'
            f'<div class="scroll"><table><tr><th>Diagnóstico</th><th>Valor</th><th>Unidade</th></tr>{diagnostic_rows}</table></div>'
            f'<p>{esc(diagnostic["macro"]["warning"])}</p>{small_sample}'
            f'<h3>Convergência numérica — prefixos da mesma execução</h3><div class="scroll"><table><tr><th>Trajetórias</th><th>Média (% PIB)</th><th>Erro-padrão (p.p. PIB)</th><th>Diferença para execução completa (p.p.)</th></tr>{convergence_rows}</table></div>'
            f'{method_section}<details><summary>Datas de referência e lacunas das fontes</summary><p>{esc(diagnostic["data_quality"]["warning"])}</p>'
            f'<div class="scroll"><table><tr><th>Série</th><th>Frequência</th><th>Referência</th><th>Dias desde referência</th><th>Status</th></tr>{source_rows}</table></div></details>'
            '<p><a href="diagnostics.json">Diagnóstico completo JSON</a> | <a href="diagnostics.csv">Indicadores diagnósticos CSV</a></p></section>')
    ranking_section = ''
    ranking = result.get('experimental_ranking')
    if ranking:
        ranking_rows = ''.join(
            f'<tr><td>{r["position_equal_weights"]}</td><th scope="row">{esc(r["name"])}</th>'
            f'<td>{number(r["score_equal_weights"])}</td><td>{r["best_rank"]}–{r["worst_rank"]}</td>'
            f'<td>{percent(r["first_place_fractional_pct"])}</td></tr>' for r in ranking['candidates'])
        audit = ''
        for candidate in ranking['candidates']:
            axis_rows = ''.join(f'<tr><th scope="row">{esc(axis)}</th><td>{number(value)}</td></tr>' for axis, value in candidate['axes'].items())
            indicator_rows = ''
            for indicator in candidate['indicators']:
                status = 'Não revisado' if indicator['detected'] is None else ('Detectado' if indicator['detected'] else 'Não detectado nesta seleção')
                indicator_rows += f'<tr><td>{esc(indicator["axis"])}</td><td>{esc(indicator["label"])}</td><td>{status}</td><td>{esc(", ".join(indicator["evidence_ids"]))}</td></tr>'
            quotes = ''.join(f'<p><b>{esc(e["id"])}, página {e["page"]}:</b> {esc(e["quote"])}</p>' for e in candidate['evidence'])
            audit += (f'<details><summary>{esc(candidate["name"])} — eixos, critérios e evidências</summary>'
                      f'<p>Documento: {esc(candidate["archive_member"])}. SHA256: {esc(candidate["program_sha256"])}. '
                      f'<a href="{esc(candidate["program_url"])}">Planos depositados no TSE</a>.</p>'
                      f'<p>Notas documentais por eixo (não são desempenho social):</p><div class="scroll"><table>{axis_rows}</table></div>'
                      f'<div class="scroll"><table><tr><th>Eixo</th><th>Critério</th><th>Detecção</th><th>Excertos</th></tr>{indicator_rows}</table></div>{quotes}</details>')
        limits = ''.join(f'<li>{esc(x)}</li>' for x in ranking['protocol']['limitations'])
        criteria = ''.join(f'<li>{esc(x["label"])}: {esc(x["definition"])}</li>' for x in ranking['protocol']['criteria'])
        ranking_section = (f'<section id="ranking"><h2>{esc(ranking["title"])}</h2>'
            '<div class="notice">LEGADO DESCONTINUADO: classificação preservada para auditoria histórica. Seleção desigual de trechos e pesos editoriais impedem interpretá-la como ranking factual ou evidência de melhor governo. Novas análises não a geram por padrão.</div>'
            '<div class="notice">Este ranking mede especificação detectada nos excertos selecionados, NÃO quem governará melhor. '
            'Não mede impacto, viabilidade, honestidade, qualidade política ou recomendação de voto. '
            'Ausência de detecção não significa ausência no programa completo nem efeito zero.</div>'
            f'<p>{ranking["counts"]["weight_analyses"]:,} análises de pesos, {ranking["counts"]["candidate_weight_evaluations"]:,} avaliações candidato/pesos. '
            'São separadas das trajetórias macroeconômicas. Nota exibida: pesos iguais por eixo e critério. '
            'Faixa de posição e primeiro lugar fracionado: sensibilidade a pesos Dirichlet(1), não probabilidades reais. Empates compartilham posição e crédito.</p>'
            f'<div class="scroll"><table><tr><th>Posição</th><th>Candidatura</th><th>Nota documental /100</th><th>Posições sob pesos</th><th>1º fracionado nos pesos</th></tr>{ranking_rows}</table></div>'
            f'<details><summary>Método e limitações — leia antes de interpretar</summary><ul>{criteria}</ul><ul>{limits}</ul></details>'
            f'{audit}<p><a href="ranking.csv">Ranking CSV</a> | <a href="ranking.json">Ranking auditável JSON</a> | <a href="ranking_indicators.csv">Critérios e evidências CSV</a></p></section>')
    history_section = ''
    history = result.get('history')
    if history:
        history_cards = ''
        for row, series in zip(history['summaries'], history['series']):
            label = f'{row["location"]}: {row["label"]}'
            detail = f'Período {row["last_period"]}; {row["n"]} observações; frequência {row["frequency"]}. Média {number(row["mean"])}; mínimo {number(row["min"])}; máximo {number(row["max"])}.'
            if row['change_year_ago'] is not None:
                detail += f' Diferença para o mesmo período do ano anterior: {number(row["change_year_ago"])} na unidade original (p.p. para taxas).'
            history_cards += card(label, row['latest'], row['unit'], detail,
                                  sparkline([v['value'] for v in series['observations']], label) + f'<p><a href="{esc(row["url"])}">Série oficial IBGE</a></p>')
        citations = ''.join(f'<li><a href="{esc(s["url"])}">{esc(s["title"])}</a> — {esc(s["status"])}</li>' for s in history['sources'])
        history_errors = ''.join(f'<li>Fonte indisponível: {esc(e["id"])} — {esc(e["error"])}</li>' for e in history['errors'])
        history_section = (f'<section id="historico"><h2>Histórico observado — Brasil, Minas Gerais e Goiás</h2>'
            f'<div class="notice">{esc(history["warning"])} Histórico territorial NÃO entra no ranking. '
            'Não há histórico executivo comparável validado para todas as candidaturas; lacunas permanecem desconhecidas.</div>'
            '<p>Períodos trimestrais no formato AAAATT (202602 = 2º trimestre de 2026). PIB anual a preços correntes, em mil reais; não confundir com crescimento real. '
            'Os dados atravessam diferentes administrações e eventuais sucessores. Parecer prévio de tribunal não é julgamento definitivo nem sentença criminal. '
            'Fontes de contas de anos diferentes contextualizam, mas não formam uma nota comparável.</p>'
            f'<div class="grid">{history_cards}</div><h3>Fontes institucionais consultadas</h3><ul>{citations}{history_errors}</ul>'
            '<p><a href="history.csv">Histórico CSV</a>; coleta reproduzível: tools/research_governments.py.</p></section>')
    return f'''<!doctype html>
<html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Presidente IA — indicadores e cenários</title>
<style>body{{font:16px system-ui,sans-serif;background:#101722;color:#edf2f7;max-width:1200px;margin:auto;padding:24px}}h1,h2{{line-height:1.2}}h2{{margin-top:40px}}a{{color:#7dd3fc}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:12px}}article,details,.notice{{background:#1d2939;padding:18px;border-radius:10px;overflow-wrap:anywhere}}h3{{font-size:15px;margin:0 0 12px}}strong{{font-size:29px}}p,span{{color:#c7d3e0}}details{{margin-bottom:12px}}table{{border-collapse:collapse;width:100%;min-width:650px}}td,th{{padding:12px;text-align:left;border-bottom:1px solid #394558}}.scroll{{overflow-x:auto}}.notice{{border-left:4px solid #fbbf24}}code{{overflow-wrap:anywhere}}</style>
<h1>Presidente IA: Brasil em números</h1>
<p>Dados observados + laboratório de cenários + análise documental experimental.</p>
<div class="notice">Estimativa de cenário não é previsão de governo. {baseline} Não calibrados: juros efetivos, crescimento nominal e primário. Os outros dados oficiais apenas contextualizam o Brasil. Frequências simuladas não são probabilidades reais.</div>
{diagnostics_section}
{ranking_section}
{history_section}
<h2>Brasil observado — dados oficiais</h2><p>Cada indicador tem sua própria data, frequência e unidade. PIB mensal do BCB é estimativa; IBC-Br não é PIB; Selic não é custo efetivo da dívida; desemprego PNADC corresponde a trimestre móvel. Janela de até 20 observações (não necessariamente 20 meses). Valores anteriores e revisões não implicam causalidade política.</p><div class="grid">{real_cards}</div><ul>{errors}</ul>
<h2>Laboratório — métricas hipotéticas</h2><p>{result['counts']['unique_reference_trajectories']} trajetórias comuns; horizonte de {reference['horizon_years']} anos. Os mesmos cenários são aplicados a todos os perfis; não estimam entregas de candidatos.</p><div class="grid">{cards}</div>
<details><summary>{len(annual_indicators)} indicadores adicionais por ano</summary><div class="grid">{annual_cards}</div></details>
<h2>Ano a ano</h2>{chart}<p>Linha: dívida média hipotética; valores e dispersão na tabela abaixo. Os gráficos dos indicadores usam escalas próprias e não comparam magnitudes entre séries.</p><div class="scroll"><table><tr><th>Ano</th><th>Dívida média (% PIB)</th><th>Percentis 10–90</th><th>Variação (p.p.)</th><th>Juros (% PIB)</th><th>Primário estabilizador (% PIB)</th></tr>{table}</table></div>
<h2>Famílias de stress</h2><p>Alocação balanceada artificial, não probabilidade de cada crise.</p><div class="scroll"><table><tr><th>Cenário</th><th>Trajetórias</th><th>Dívida final média (% PIB)</th><th>Percentis 2,5–97,5</th></tr>{scenario_rows}</table></div>
<h2>Reproduzir e conferir</h2><p>Seed: {result['parameters']['seed']}. Run ID: <code>{esc(result['run_id'])}</code>.</p><p>Dados completos: <a href="results.json">JSON</a> | <a href="metrics.csv">Métricas CSV</a> | <a href="observed.csv">Dados oficiais CSV</a> | <a href="trajectories.csv">Trajetórias CSV</a> | <a href="report.txt">Relatório</a>.</p>
<p>Efeitos em saúde, educação, segurança e renda por candidato continuam desconhecidos. Ausência de dados não significa zero nem empate.</p></html>'''
