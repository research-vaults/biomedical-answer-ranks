"""Build the complete paper from its self-contained sources in a new directory."""
import argparse,os,shutil,subprocess
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--source',default=str(ROOT/'manuscript/current'));p.add_argument('--output',default='outputs/manuscript');a=p.parse_args()
    source=Path(a.source).resolve();out=Path(a.output).resolve()
    if out.exists():raise SystemExit('Choose a new --output directory; existing builds are preserved.')
    shutil.copytree(source,out)
    env=dict(os.environ,SOURCE_DATE_EPOCH='1788739200',FORCE_SOURCE_DATE='1',TZ='UTC')
    result=subprocess.run(['latexmk','-pdf','-interaction=nonstopmode','-halt-on-error','-file-line-error','-no-shell-escape','main.tex'],cwd=out,env=env,capture_output=True,text=True)
    (out/'build-output.txt').write_text(result.stdout+result.stderr)
    if result.returncode:raise SystemExit('LaTeX failed; inspect the isolated build log.')
    doc=fitz.open(out/'main.pdf');text='\n'.join(p.get_text() for p in doc)
    assert len(doc)>=16,'Unexpectedly incomplete document'
    normalized=' '.join(text.casefold().split())
    assert 'references' in normalized and 'donor ranks' in normalized,'Missing current bibliography or supplement'
    assert not doc.metadata.get('author'),'Unexpected author metadata'
    for marker in ['undefined references','Citation `']:
        assert marker not in (out/'main.log').read_text(errors='replace'),'Unresolved citation/reference'
    shutil.copyfile(out/'main.pdf',out/'full-paper.pdf')
    print(f'PASS: self-contained main, references and supplement; {len(doc)} pages.')
if __name__=='__main__':main()
