"""Índice de navegação v2: aplica o MESMO léxico por dimensão a todas as páginas de todos os planos.

Não é nota. Serve para localizar as páginas que o avaliador lê inteiras (dimensões temáticas) e as linhas com
valores, anos-meta e instrumentos (dimensões transversais). Contagem de termos não é mérito.

  .venv/bin/python tools/navigate_plans_v2.py <candidate_id> <dimensão> [--top 3] [--max-chars 6000]
  .venv/bin/python tools/navigate_plans_v2.py --index   # grava research/plan_navigation_v2.json (todas as contagens)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / '.cache/programs.zip'
MANIFEST = ROOT / 'research/program_manifest.json'

LEXICON = {
    'economia': r'emprego|desemprego|renda|salári|indústri|crescimento econ|investimento|juros|inflação|trabalhador|tribut|imposto|PIB|produtividade',
    'saude': r'saúde|SUS\b|hospita|médic|atenção primária|atenção básica|fila|vacina|medicament',
    'educacao': r'educa|escola|ensino|professor|alfabetiz|creche|universidade|aluno|estudante',
    'seguranca': r'segurança pública|crime|criminal|políci|violência|facç|prisional|presídi|homicíd|tráfico',
    'ambiente': r'ambient|clima|climát|desmatamento|sustentáv|renováve|carbono|Amazônia|biodiversidade|saneamento',
    'fiscal': r'R\$ ?\d|bilh|trilh|milhões|custo|financiamento|orçament|fiscal|arrecada|receita|despesa|dívida|superávit|déficit|primário|arcabouço|teto de gastos',
    'execucao': r'\bmeta|até 20\d\d|em 20(2[7-9]|3\d)|prazo|cronograma|indicador|monitora|avaliação de|transparência|\bPEC\b|projeto de lei|medida provisória|decreto|prestação de contas',
}
# termos fortes (sinal de custo/fonte/regra e de meta/prazo/instrumento/monitoramento) para a varredura --lines
STRONG = {
    'fiscal': r'R\$ ?\d|\d+(,\d+)? ?(bilh|trilh)|custo|financiad|financiamento|fonte de recursos|arcabouço|teto de gastos|responsabilidade fiscal|resultado primário|superávit|déficit|dívida pública|equilíbrio fiscal|imposto sobre|taxação',
    'execucao': r'\bmetas?\b|até 20[23]\d|em 20(2[7-9]|3\d)|primeiro ano|100 dias|cronograma|prazo|indicador|monitora|avaliação (de|independente)|painel|\bPEC\b|projeto de lei|proposta de emenda|medida provisória|decreto|lei complementar',
}
STRONG.update({k: v for k, v in LEXICON.items() if k not in STRONG})


def pages(candidate_id: str) -> list[str]:
    import pymupdf  # noqa: PLC0415
    man = {m['candidate_id']: m for m in json.loads(MANIFEST.read_text())}[candidate_id]
    blob = zipfile.ZipFile(ARCHIVE).read(man['archive_member'])
    if hashlib.sha256(blob).hexdigest() != man['sha256']:
        raise SystemExit(f'{candidate_id}: sha256 do PDF não confere com o manifesto')
    return [p.get_text() for p in pymupdf.open(stream=blob, filetype='pdf')]


def hits(text: str, dim: str) -> int:
    return len(re.findall(LEXICON[dim], text, flags=re.I))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('candidate', nargs='?')
    ap.add_argument('dim', nargs='?', choices=sorted(LEXICON))
    ap.add_argument('--top', type=int, default=3)
    ap.add_argument('--max-chars', type=int, default=6000)
    ap.add_argument('--lines', action='store_true', help='só linhas com termos do léxico, no plano inteiro')
    ap.add_argument('--index', action='store_true')
    a = ap.parse_args()
    if a.index:
        out = {'lexicon': LEXICON, 'per_candidate': {}}
        for m in json.loads(MANIFEST.read_text()):
            ps = pages(m['candidate_id'])
            out['per_candidate'][m['candidate_id']] = {d: [hits(p, d) for p in ps] for d in LEXICON}
        (ROOT / 'research/plan_navigation_v2.json').write_text(json.dumps(out, ensure_ascii=False) + '\n')
        print('ok research/plan_navigation_v2.json')
        return 0
    ps = pages(a.candidate)
    if a.lines:  # janelas de ±160 caracteres em volta de termos FORTES, texto normalizado, plano inteiro
        strong = STRONG[a.dim]
        n = 0
        for i, p in enumerate(ps, 1):
            t = ' '.join(p.split())
            last = -10**9
            for m in re.finditer(strong, t, flags=re.I):
                if m.start() - last < 320:  # janela anterior já cobre este termo
                    continue
                last = m.start()
                w = t[max(0, m.start() - 160):m.end() + 160]
                print(f'[p{i}] …{w}…')
                n += len(w)
                if n > a.max_chars:
                    print('[...corte por max-chars]')
                    return 0
        return 0
    ranked = sorted(range(len(ps)), key=lambda i: (-hits(ps[i], a.dim), i))[:a.top]
    print(f'{a.candidate} {a.dim}: páginas com mais termos = {[i + 1 for i in ranked]} '
          f'(total no plano {sum(hits(p, a.dim) for p in ps)}, {len(ps)} págs)')
    budget = a.max_chars
    for i in sorted(ranked):
        txt = ' '.join(ps[i].split())
        print(f'\n=== p{i + 1} ===\n{txt[:budget]}')
        budget -= len(txt[:budget])
        if budget <= 0:
            break
    return 0


if __name__ == '__main__':
    sys.exit(main())
