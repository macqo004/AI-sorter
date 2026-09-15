from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3

SUPPORTED = {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.pns'}

def detect(header: bytes) -> str:
    if header.startswith(b'\x89PNG\r\n\x1a\n'): return 'PNG'
    if header.startswith(b'\xff\xd8\xff'): return 'JPEG'
    if header.startswith((b'GIF87a', b'GIF89a')): return 'GIF'
    if header.startswith(b'BM'): return 'BMP'
    if len(header) >= 12 and header[:4] == b'RIFF' and header[8:12] == b'WEBP': return 'WEBP'
    return 'UNKNOWN'

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('project_db')
    ap.add_argument('root')
    ap.add_argument('--limit', type=int, default=20)
    args = ap.parse_args()
    root = str(Path(args.root).resolve()).rstrip('\\/')
    pattern = root + '\\%'
    db = sqlite3.connect(args.project_db)
    rows = db.execute("SELECT absolute_path FROM file_location WHERE location_status='ACTIVE' AND (absolute_path=? OR absolute_path LIKE ?) ORDER BY absolute_path", (root, pattern)).fetchall()
    counts = {}
    shown = 0
    for (raw,) in rows:
        p = Path(raw)
        ext = p.suffix.lower()
        if ext not in SUPPORTED: continue
        try:
            with p.open('rb') as f: header=f.read(32)
            fmt=detect(header)
            expected={'.jpg':'JPEG','.jpeg':'JPEG','.png':'PNG','.webp':'WEBP','.gif':'GIF','.bmp':'BMP','.pns':'PNG'}[ext]
            key='MATCH' if fmt == expected else f'MISMATCH {expected}->{fmt}'
        except Exception as e:
            key=f'{type(e).__name__}: {e}'
        counts[key]=counts.get(key,0)+1
        if key != 'MATCH' and shown < args.limit:
            print(raw)
            print('  extension:', ext)
            print('  result:', key)
            shown += 1
    print('\nSummary:')
    for k,v in sorted(counts.items(), key=lambda x:(x[0] != 'MATCH', -x[1], x[0])): print(f'{k}: {v}')
    db.close()
    return 0

if __name__ == '__main__': raise SystemExit(main())
