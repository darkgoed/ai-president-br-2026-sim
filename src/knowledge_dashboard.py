"""Navegador offline da base integrada; filtros não calculam mérito político."""
from html import escape
import json
from pathlib import Path


LABELS = {'observed': 'Estatística reportada', 'derived_observation': 'Cálculo descritivo de dados observados — não causal', 'official_declaration': 'Declaração/proposta documentada',
          'official_identity': 'Identificação eleitoral', 'automated_mention': 'Menção automática — revisar',
          'document_page': 'Página integral do plano', 'contextual_analysis': 'Análise contextual — não impacto',
          'missing': 'Lacuna ou dado suprimido', 'simulated': 'Saída simulada — não fato futuro',
          'methodology': 'Método e proveniência', 'legacy_deprecated': 'Legado descontinuado'}


def write_dashboard(registry, report, output):
    output = Path(output)
    cursor = registry.connection.execute('''select r.id,r.kind,r.candidate_id,r.entity,r.label,r.period,r.unit,r.value,
        r.text,r.payload_json,r.pointer,s.path,s.url,s.sha256,s.verification
        from records r join sources s on s.id=r.source_id where r.kind != 'legacy_deprecated' order by r.id''')
    keys = [x[0] for x in cursor.description]
    records = [dict(zip(keys, row)) for row in cursor]
    payload = {'records': records, 'kinds': LABELS, 'candidates': report['coverage']['candidates']}
    # Script externo funciona também em file://, sem fetch ou serviço remoto.
    data = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')
    (output/'catalog-data.js').write_text('window.EVIDENCE_DATA='+data+';\n', encoding='utf-8')
    esc = lambda value: escape(str(value), quote=True)
    candidate_rows = ''.join(f'<tr><th>{esc(c["name"])}</th><td>{c["pages_fulltext"]}</td><td>{c["sampled_excerpts"]}</td><td>{c["catalogued_targets"]}</td><td>{c["missing_items"]}</td></tr>' for c in report['coverage']['candidates'])
    gaps = ''.join(f'<li>{esc(json.dumps(g, ensure_ascii=False))}</li>' for g in report['coverage']['missing'])
    policy = ''.join(f'<li>{esc(p)}</li>' for p in report['policy']['principles'])
    counts = ''.join(f'<li>{esc(LABELS[k])}: {n}</li>' for k,n in report['counts']['by_kind'].items())
    summary = ''
    simulation = report['simulation']
    if simulation:
        summary_rows = ''.join(f'<tr><th>{esc(s["label"])}</th><td>{esc(s["unit"])}</td><td>{s["final"]["median"]:.3f}</td><td>{s["final"]["q025"]:.3f} – {s["final"]["q975"]:.3f}</td></tr>' for s in simulation['summary'].values())
        backtest_rows = ''.join(f'<tr><th>{esc(k)}</th><td>{s.get("bootstrap_mae", "N/D")}</td><td>{s.get("baseline_mae", "N/D")}</td><td>{s.get("mae_skill_vs_no_change", "N/D")}</td></tr>' for k,s in simulation['backtest']['by_metric'].items())
        summary = (f'<h2>Simulação integrada por proveniência: {simulation["counts"].get("sampled_paths", simulation["counts"].get("unique_paths")):,} trajetórias preservadas</h2>'
            '<p>Calibradores: séries BCB/IBGE de dívida, desocupação, IBC-Br e IPCA. Demais evidências são contexto e não foram convertidas em efeitos. A inclusão na base não significa entrada em uma equação.</p>'
            f'<div class="scroll"><table><tr><th>Indicador</th><th>Unidade</th><th>Mediana final</th><th>Quantis artificiais 2,5–97,5%</th></tr>{summary_rows}</table></div>'
            '<div class="notice">O backtest anterior foi pior que manter o nível inicial para dívida e desocupação. O modelo não está validado para prever governos ou produzir vencedor. Um milhão de trajetórias não corrige esse problema.</div>'
            f'<details><summary>Backtest original — sem ocultar erros</summary><p>{esc(simulation["backtest"]["warning"])}</p>'
            f'<div class="scroll"><table><tr><th>Indicador</th><th>MAE modelo</th><th>MAE baseline</th><th>Skill (negativo = pior)</th></tr>{backtest_rows}</table></div></details>')
    html = f'''<!doctype html><html lang="pt-BR"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Presidente IA — base auditável integrada</title>
<style>body{{font:16px system-ui;background:#101722;color:#edf2f7;max-width:1200px;margin:auto;padding:24px;overflow-wrap:anywhere}}a{{color:#7dd3fc}}.notice,details,article{{background:#1d2939;padding:18px;border-radius:10px;margin:16px 0}}.notice{{border-left:4px solid #fbbf24}}.scroll{{overflow-x:auto}}table{{border-collapse:collapse;width:100%;min-width:650px}}td,th{{text-align:left;padding:12px;border-bottom:1px solid #394558}}h2{{margin-top:40px}}p,li{{line-height:1.55}}input,select,button{{font:inherit;padding:10px;background:#1d2939;color:#edf2f7;border:1px solid #718096;border-radius:6px;max-width:100%;box-sizing:border-box}}form{{display:flex;gap:12px;flex-wrap:wrap}}label{{display:flex;flex-direction:column;gap:6px}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:14px monospace}}button:disabled{{opacity:.45}}.muted{{color:#bdcddd}}</style>
<style>label{{min-width:0;max-width:100%}}select{{width:100%}}</style>
<h1>Presidente IA — base auditável integrada</h1>
<div class="notice">Sem impactos inventados e sem vencedor de governo. Dados observados, declarações, lacunas e simulações têm classificações diferentes. Documento oficial não torna uma promessa verdadeira ou executada. Não é possível garantir ausência de todo viés; escolhas, assimetrias e erros estão expostos.</div>
<p>Base: {report['counts']['records']:,} registros, {report['counts']['sources']} snapshots/fontes locais, {report['counts']['candidates']} candidaturas. Esses totais não representam estudos independentes. Bundle: {esc(report['bundle_id'])}.</p>
<h2>Pesquisar e comparar evidências</h2><p>Pesquisa local em páginas integrais, citações, números, datas e payloads. Resultados não são ordenados por mérito: ordem técnica por ID. Filtro “candidatura” mostra documentos vinculados, não atribui indicadores de territórios à pessoa.</p>
<form id="filters"><label>Texto<input id="query" type="search" placeholder="Ex.: saúde, custo, inflação" autocomplete="off"></label><label>Candidatura<select id="candidate"><option value="">Todas — inclui contexto nacional/territorial</option></select></label><label>Tipo de evidência<select id="kind"><option value="">Todos os tipos ativos</option></select></label><button type="submit">Pesquisar</button></form>
<p id="result-status" role="status" aria-live="polite"></p><div id="results"></div><p><button id="previous" type="button">Anterior</button> <button id="next" type="button">Próxima</button></p>
<noscript>Ative JavaScript para pesquisa offline ou consulte evidence.sqlite e records.jsonl via CLI.</noscript>
<h2>Cobertura uniforme de páginas, assimetria de catalogação anterior</h2><p>Páginas integrais foram incluídas para as doze candidaturas com a mesma regra. Isso não transforma extração automática em revisão semântica completa. As contagens abaixo NÃO são notas, não justificam superioridade e não são comparáveis como produtividade política.</p>
<div class="scroll"><table><tr><th>Candidatura</th><th>Páginas integrais</th><th>Excertos da seleção anterior</th><th>Metas catalogadas anteriormente</th><th>Lacunas declaradas</th></tr>{candidate_rows}</table></div>
{summary}
<h2>Política de evidências e descontinuação do ranking anterior</h2><ul>{policy}</ul><p>O ranking documental anterior é legado descontinuado por seleção desigual e pesos editoriais, não um ranking factual. Foi preservado para histórico, fora da consulta padrão. Não recalculamos critérios para favorecer outro candidato.</p><details><summary>Contagens por classificação</summary><ul>{counts}</ul></details>
<h2>Fontes pendentes e limites de completude</h2><ul>{gaps}</ul><p>{esc(report['coverage']['scope'])} Entrevistas, debates e discursos externos não foram transcritos nem checados integralmente nesta base. Falas sem fonte não são adicionadas como fatos. Mais páginas e registros não equivalem a menor erro causal.</p>
<h2>Auditoria e exportações</h2><p><a href="manifest.json">Manifesto e política</a> | <a href="evidence.sqlite">Base SQLite/FTS5</a> | <a href="records.jsonl">Registros JSONL</a> | <a href="sources.jsonl">Fontes e conteúdo JSONL</a></p>
<p>Reconstrução: python -m src.cli integrate --out results-integrated. Consulta CLI: python tools/query_evidence.py results-integrated/evidence.sqlite --text saúde. Simulação completa anterior: results-1m/ (não sobrescrita).</p>
<script src="catalog-data.js"></script><script src="catalog.js"></script></html>'''
    (output/'dashboard.html').write_text(html, encoding='utf-8')
    script = ''''use strict';
const data=window.EVIDENCE_DATA;
const $=id=>document.getElementById(id);
const pageSize=25;
let offset=0, filtered=[];
const norm=s=>String(s??'').normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase();
const candidateNames=Object.fromEntries(data.candidates.map(c=>[c.id,c.name]));
for(const c of data.candidates){const o=document.createElement('option');o.value=c.id;o.textContent=c.name;$('candidate').append(o);}
for(const [key,label] of Object.entries(data.kinds)){if(key==='legacy_deprecated')continue;const o=document.createElement('option');o.value=key;o.textContent=label;$('kind').append(o);}
const index=data.records.map(r=>norm([r.label,r.text,r.payload_json,r.entity,r.period].join(' ')));
function append(parent,tag,text){const node=document.createElement(tag);node.textContent=text;parent.append(node);return node;}
function render(){
 $('results').replaceChildren();
 $('result-status').textContent=`${filtered.length} registros encontrados. Exibindo ${filtered.length?offset+1:0}–${Math.min(offset+pageSize,filtered.length)}.`;
 for(const r of filtered.slice(offset,offset+pageSize)){
  const article=document.createElement('article');article.dataset.recordId=r.id;
  append(article,'h3',r.label);
  append(article,'p',`${data.kinds[r.kind]} | ${candidateNames[r.candidate_id]??r.entity??'Contexto / método'} | referência: ${r.period??'não informada'} | unidade: ${r.unit??'não estruturada — consultar original'}`);
  if(r.value!==null)append(article,'p',`Valor reportado: ${r.value}`);
  if(r.text)append(article,'p',r.text.length>1100?r.text.slice(0,1100)+'… (conteúdo completo abaixo)':r.text);
  const details=document.createElement('details');append(details,'summary','Payload completo e proveniência');
  append(details,'pre',JSON.stringify(JSON.parse(r.payload_json),null,2));
  append(details,'p',`Fonte: ${r.path} | ponteiro: ${r.pointer} | SHA256: ${r.sha256} | verificação: ${r.verification}`);
  let url=r.url;
  if(!url){const payload=JSON.parse(r.payload_json);if(payload&&typeof payload==='object')url=payload.url;}
  if(typeof url==='string'&&/^https?:\\/\\//i.test(url)){const a=append(details,'a','Abrir fonte original');a.href=url;a.target='_blank';a.rel='noopener noreferrer';}
  article.append(details);$('results').append(article);
 }
 $('previous').disabled=offset===0;$('next').disabled=offset+pageSize>=filtered.length;
}
function filter(){const q=norm($('query').value),candidate=$('candidate').value,kind=$('kind').value;
 filtered=data.records.filter((r,i)=>(!q||index[i].includes(q))&&(!candidate||r.candidate_id===candidate)&&(!kind||r.kind===kind));offset=0;render();}
$('filters').addEventListener('submit',e=>{e.preventDefault();filter();});
$('candidate').addEventListener('change',filter);$('kind').addEventListener('change',filter);
$('previous').addEventListener('click',()=>{offset=Math.max(0,offset-pageSize);render();});
$('next').addEventListener('click',()=>{offset+=pageSize;render();});
filter();
'''
    (output/'catalog.js').write_text(script, encoding='utf-8')
