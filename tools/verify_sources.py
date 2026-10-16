"""Revalida pesquisa em fontes primárias, com cache local não versionado.

python tools/verify_sources.py
Requer requirements-dev.txt. Fontes remotas podem mudar após o corte: alterações
são reportadas, não silenciosamente substituídas nos resultados publicados.
"""
from pathlib import Path
import hashlib
import io
import json
import re
import sys
import zipfile
from urllib.request import Request, urlopen
import pymupdf

ROOT = Path(__file__).resolve().parents[1]


def norm(text):
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', str(text))
    return ' '.join(text.split()).replace('ﬁ', 'fi').replace('ﬂ', 'fl')


def main():
    cache = ROOT/'.cache'
    cache.mkdir(exist_ok=True)
    sources = json.loads((ROOT/'research/electoral_sources.json').read_text())
    source = next(s for s in sources if s['id']=='programs')
    archive = cache/'programs.zip'
    if not archive.exists():
        with urlopen(Request(source['url'], headers={'User-Agent': 'PresidentSimulationResearch/1.0'}), timeout=90) as response:
            raw = response.read(40_000_001)
        if len(raw)>40_000_000:
            raise ValueError('archive exceeds 40 MB collection budget')
        archive.write_bytes(raw)
    raw = archive.read_bytes()
    archive_matches_cutoff = hashlib.sha256(raw).hexdigest()==source['sha256']
    manifest = json.loads((ROOT/'research/program_manifest.json').read_text())
    known = {m['candidate_id']:m for m in manifest}
    verified, errors, changes = 0, [], []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        for path in sorted((ROOT/'research/candidates').glob('*.json')):
            dossier = json.loads(path.read_text())
            candidate = dossier['official_candidate_id']
            spec = known[candidate]
            pdf = z.read(spec['archive_member'])
            if hashlib.sha256(pdf).hexdigest()!=spec['sha256']:
                changes.append(candidate)
                continue
            doc = pymupdf.open(stream=pdf, filetype='pdf')
            for evidence in dossier['evidence']:
                page = evidence.get('page')
                if page is None:
                    continue
                quote = norm(evidence['quote'])
                if quote.endswith('…'):
                    quote=quote.rstrip('…').rstrip('.')
                if quote not in norm(doc[page-1].get_text()):
                    errors.append(evidence['id'])
                else:
                    verified += 1
    report = {'archive_matches_cutoff':archive_matches_cutoff,
              'changed_candidate_documents':changes,
              'verified_program_excerpts':verified,'quote_mismatches':errors,
              'status':'pass' if not errors and not changes else 'fail_or_source_changed'}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status']=='pass' else 1


if __name__=='__main__':
    sys.exit(main())
