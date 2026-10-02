"""Extract and run all five current stored-output checks without network access."""
import argparse, pathlib, subprocess, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='outputs/current-replay');a=p.parse_args()
    out=pathlib.Path(a.output).resolve()
    if out.exists():raise SystemExit('Use a new output directory; existing results are preserved.')
    with zipfile.ZipFile(ROOT/'data/representation-replay.zip') as z:
        assert all(not n.startswith('/') and '..' not in pathlib.Path(n).parts for n in z.namelist())
        z.extractall(out)
    run=subprocess.run([sys.executable,'replay.py'],cwd=out,capture_output=True,text=True)
    (out/'execution.log').write_text(run.stdout+run.stderr)
    print(run.stdout);print(run.stderr,file=sys.stderr)
    if run.returncode:raise SystemExit(run.returncode)
    print('PASS: five current stored-output checks; no inference calls.')
if __name__=='__main__':main()
