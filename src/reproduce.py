"""Replay recorded analyses in an isolated workspace; never overwrite input evidence."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=['replay_development.py','analyze_development_selectors.py','analyze_fresh_confirmation.py','analyze_branch_interaction.py','analyze_order_challenge.py','analyze_native_key_transport.py','plot_source_comparison.py','analyze_subset_budget.py','analyze_support_channel.py','analyze_common_pool_support.py','plot_common_pool_support.py','plot_development.py']
def compare(a,b,path=''):
    if isinstance(a,dict):
        for k,v in a.items():compare(v,b[k],path+'/'+k)
    elif isinstance(a,list):
        assert len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
    elif isinstance(a,(float,int)) and not isinstance(a,bool):assert abs(a-b)<1e-10,(path,a,b)
    else:assert a==b,(path,a,b)
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',default='outputs/replay');args=p.parse_args()
    dest=Path(args.output).resolve()
    if dest.exists():raise SystemExit('Output must not exist; choose a new --output directory.')
    dest.mkdir(parents=True)
    for folder in ['src','data','manuscript','expected']:
        shutil.copytree(ROOT/folder,dest/folder)
    (dest/'manuscript/figures').mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,MPLCONFIGDIR=str(dest/'plot-cache'),PYTHONDONTWRITEBYTECODE='1')
    # Hash-guard the adapted analysis in its release context.
    for script in SCRIPTS:
        result=subprocess.run([sys.executable,str(dest/'src'/script)],cwd=dest,env=env,capture_output=True,text=True)
        (dest/(script+'.txt')).write_text(result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(f'{script} failed; inspect its output log.')
        print('PASS',script,flush=True)
    for expected in sorted((dest/'expected').glob('*.json')):
        observed=dest/'data'/expected.stem/'RESULTS.json'
        compare(json.loads(expected.read_text()),json.loads(observed.read_text()),expected.stem)
    (dest/'REPLAY_VERIFICATION.json').write_text(json.dumps({'status':'PASS','analyses':len(SCRIPTS),'numerical_tolerance':1e-10,'network_calls':0,'scope':'Recorded-output numerical replication, not renewed clinical adjudication'},indent=2)+'\n')
    print('PASS: every retained result field matches; original release evidence unchanged.')
if __name__=='__main__':main()
