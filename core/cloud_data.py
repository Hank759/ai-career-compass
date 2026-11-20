"""Restore the bundled read-only public-data snapshot on first cloud startup."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading

_LOCK=threading.Lock()
ROOT=Path(__file__).resolve().parents[1]

def ensure_database():
    target=ROOT/'data/processed/career_compass_v1.sqlite'
    if target.exists():return target
    with _LOCK:
        if target.exists():return target
        source=ROOT/'data/cloud'
        manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
        target.parent.mkdir(parents=True,exist_ok=True)
        fd,name=tempfile.mkstemp(prefix='database-',suffix='.tmp',dir=target.parent)
        os.close(fd)
        temp=Path(name)
        archive=temp.with_suffix('.gz')
        try:
            with archive.open('wb') as dest:
                for part in manifest['parts']:
                    path=(source/part).resolve()
                    if not path.is_relative_to(source.resolve()):raise ValueError('Invalid data part path')
                    with path.open('rb') as f:
                        for block in iter(lambda:f.read(1024*1024),b''):dest.write(block)
            h=hashlib.sha256()
            with gzip.open(archive,'rb') as src,temp.open('wb') as dest:
                for block in iter(lambda:src.read(1024*1024),b''):
                    dest.write(block);h.update(block)
            if h.hexdigest()!=manifest['database_sha256']:raise ValueError('Bundled database checksum mismatch')
            os.replace(temp,target)
        finally:
            temp.unlink(missing_ok=True);archive.unlink(missing_ok=True)
    return target
