"""Pesquisa literal e paginada na base integrada, aberta somente para leitura."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.knowledge import Registry, KINDS

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('--text', default='')
    parser.add_argument('--candidate')
    parser.add_argument('--kind', choices=sorted(KINDS))
    parser.add_argument('--limit', type=int, default=25)
    parser.add_argument('--offset', type=int, default=0)
    args = parser.parse_args()
    registry = Registry.open_readonly(args.database)
    try:
        print(json.dumps(registry.query(args.text, args.candidate, args.kind, args.limit, args.offset), ensure_ascii=False, indent=2))
    finally:
        registry.close()
