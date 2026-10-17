"""Coleta BCB integral para o modo empírico; nunca completa fontes com hipóteses."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.empirical_data import collect_history, validate_snapshot

if __name__ == '__main__':
    snapshot = collect_history()
    if snapshot['status'] != 'complete':
        print(json.dumps(snapshot['errors'], ensure_ascii=False, indent=2))
        raise SystemExit('Coleta incompleta; nenhum snapshot anterior foi sobrescrito')
    validate_snapshot(snapshot)
    target = ROOT/'data/empirical_monthly.json'
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'target': str(target), 'status': snapshot['status'],
                      'series': [{'id': s['id'], 'n': len(s['observations']),
                                  'first': s['observations'][0]['period'], 'last': s['observations'][-1]['period']}
                                 for s in snapshot['series']]}, ensure_ascii=False, indent=2))
