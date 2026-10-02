"""Checksums and conservative privacy scans; prints locations, never suspected secrets."""
import argparse,gzip,hashlib,json,re,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PATTERNS={
 'private_path':r'/(?:Users|home)/[^\s/]+/',
 'private_key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
 'github_credential':r'\b(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,})\b',
 'provider_credential':r'\bsk-(?:or-v1-)?[A-Za-z0-9_-]{28,}\b',
 'aws_credential':r'\bAKIA[A-Z0-9]{16}\b',
}
FORBIDDEN_NAMES={'.env','.DS_Store','known_hosts','ROADMAP.md','PLAN_AND_OUTCOME_JOURNAL.md'}
def files():
    if (ROOT/'.git').exists():
        names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
        return [ROOT/n for n in names if n]
    return [p for p in ROOT.rglob('*') if p.is_file() and not any(x in p.parts for x in ['outputs','.venv','__pycache__','.git'])]
def violations(content,label):
    return [(label,name) for name,rx in PATTERNS.items() if re.search(rx,content)]
def main():
    p=argparse.ArgumentParser();p.add_argument('--write-manifest',action='store_true');args=p.parse_args()
    chosen=files();bad=[]
    for f in chosen:
        name=f.relative_to(ROOT).as_posix()
        if f.stat().st_size>50*1024*1024:bad.append((name,'project_50MiB_file_limit'))
        if f.name in FORBIDDEN_NAMES or f.name.startswith('.env.') or 'Reviews' in f.parts:bad.append((name,'forbidden_name'))
        # The scan's test patterns are not credentials or leaked identities.
        if name=='src/verify_release.py':continue
        raw=f.read_bytes();bad+=violations(raw.decode('utf8',errors='ignore'),name)
        if f.suffix=='.gz':bad+=violations(gzip.decompress(raw).decode('utf8',errors='ignore'),name+' decompressed')
        if f.name=='manifest.json':
            m=json.loads(raw)
            if m.get('format')=='sanitized-evidence-gzip-shards-v1':
                from large_files import chunks
                tail=b''
                for block in chunks(f):
                    bad+=violations((tail+block).decode('utf8',errors='ignore'),name+' logical stream')
                    tail=block[-4096:]
        if f.suffix=='.pdf':
            import fitz
            d=fitz.open(stream=raw,filetype='pdf')
            bad+=violations(json.dumps(d.metadata)+'\n'+'\n'.join(p.get_text() for p in d),name+' content/metadata')
            if d.embfile_count():bad.append((name,'embedded_attachment'))
        if f.suffix=='.zip':
            with zipfile.ZipFile(f) as z:
                for info in z.infolist():
                    if info.filename.startswith('/') or '..' in Path(info.filename).parts:bad.append((name,'unsafe_archive_path'))
                    bad+=violations(info.filename+z.read(info).decode('utf8',errors='ignore'),name+'!'+info.filename)
    if (ROOT/'.git').exists() and subprocess.run(['git','rev-parse','--verify','HEAD'],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0:
        log=subprocess.check_output(['git','log','--all','--format=%an <%ae> %cn <%ce>%n%B'],cwd=ROOT,text=True)
        bad+=violations(log,'git authors/messages')
    if bad:
        for location,rule in bad:print('FAIL',location,rule)
        raise SystemExit(1)
    manifest=ROOT/'SHA256SUMS'
    if args.write_manifest:
        selected=[f for f in chosen if f.name!='SHA256SUMS' or f.parent!=ROOT]
        manifest.write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.relative_to(ROOT).as_posix()+'\n' for f in sorted(selected)))
    else:
        assert manifest.exists(),'Missing release manifest'
        for line in manifest.read_text().splitlines():
            expected,name=line.split('  ',1);f=ROOT/name
            assert f.is_file() and hashlib.sha256(f.read_bytes()).hexdigest()==expected,('Checksum mismatch',name)
        covered={line.split('  ',1)[1] for line in manifest.read_text().splitlines()}
        assert {f.relative_to(ROOT).as_posix() for f in chosen if f!=manifest}<=covered,'Unmanifested release files'
    print(f'PASS: {len(chosen)} release files, content/filename/PDF/archive scan and checksums.')
if __name__=='__main__':main()
