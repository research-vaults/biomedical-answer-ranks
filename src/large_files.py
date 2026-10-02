"""Deterministic, checksummed gzip shards for sanitized evidence (no LFS needed)."""
import argparse,gzip,hashlib,json,os,tempfile
from pathlib import Path
CHUNK_BYTES=4*1024*1024
FORMAT='sanitized-evidence-gzip-shards-v1'
def digest(b):return hashlib.sha256(b).hexdigest()
def pack(source,destination):
    source=Path(source);destination=Path(destination)
    destination.mkdir(parents=True,exist_ok=False)
    parts=[];whole=hashlib.sha256();total=0
    with source.open('rb') as f:
        while block:=f.read(CHUNK_BYTES):
            whole.update(block);total+=len(block);name=f'part-{len(parts):06}.gz'
            payload=gzip.compress(block,compresslevel=9,mtime=0)
            (destination/name).write_bytes(payload)
            parts.append({'file':name,'compressed_bytes':len(payload),'compressed_sha256':digest(payload),'logical_bytes':len(block),'logical_sha256':digest(block)})
    m={'format':FORMAT,'logical_name':source.name,'logical_bytes':total,'logical_sha256':whole.hexdigest(),'chunk_bytes':CHUNK_BYTES,'parts':parts,'privacy_note':'Compression is not anonymization; scan the logical content before and after packing.'}
    (destination/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    return m
def chunks(manifest):
    manifest=Path(manifest);m=json.loads(manifest.read_text());assert m['format']==FORMAT
    whole=hashlib.sha256();total=0
    for i,part in enumerate(m['parts']):
        assert part['file']==f'part-{i:06}.gz','Unsafe or unordered shard path'
        raw=(manifest.parent/part['file']).read_bytes()
        assert len(raw)==part['compressed_bytes'] and digest(raw)==part['compressed_sha256'],'Compressed checksum mismatch'
        block=gzip.decompress(raw)
        assert len(block)==part['logical_bytes'] and digest(block)==part['logical_sha256'],'Logical shard mismatch'
        whole.update(block);total+=len(block);yield block
    assert total==m['logical_bytes'] and whole.hexdigest()==m['logical_sha256'],'Logical file mismatch'
def unpack(manifest,destination):
    destination=Path(destination)
    if destination.exists():raise FileExistsError('Refusing to overwrite an existing output')
    destination.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.verified-evidence-',dir=destination.parent)
    temp=Path(name)
    try:
        with os.fdopen(fd,'wb') as out:
            for block in chunks(manifest):out.write(block)
        # Exclusive publication preserves an output created concurrently.
        os.link(temp,destination)
    finally:
        temp.unlink(missing_ok=True)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['pack','verify','unpack']);p.add_argument('input');p.add_argument('output',nargs='?');a=p.parse_args()
    if a.mode=='verify':
        for _ in chunks(a.input):pass
    elif a.output is None:p.error('output is required')
    elif a.mode=='pack':pack(a.input,a.output)
    else:unpack(a.input,a.output)
    print('PASS',a.mode)
if __name__=='__main__':main()
