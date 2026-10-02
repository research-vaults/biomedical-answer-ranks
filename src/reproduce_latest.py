"""Run the ten current stored-output capsules; no inference or network calls."""
import argparse, concurrent.futures, hashlib, json, os, pathlib, subprocess, sys, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
COMMANDS={
 'representation_replay':[['replay.py']],
 'ballot_patterns_replay':[['analyze.py','--base','inputs','--out','outputs']],
 'composition_replay':[['replay.py']],
 'task_strata_replay':[['replay.py','--data','data','--out','outputs']],
 'rank_information_replay':[['replay.py','analyze','--data','data','--out','outputs']],
 'ballot_diagnostics_v1':[['replay.py','--data','data','--out','outputs'],['null.py','--data','data','--out','outputs']],
 'eleven_review_replay':[['replay.py','--data','data','--out','outputs']],
 'practical_cutoff_replay':[['replay.py','--data','data','--out','outputs']],
 'tie_policy_replay':[['replay.py','--data','data','--source','RankBasedSC.py','--out','outputs']],
 'budget_transfer_replay':[['replay.py','--data','data','--out','outputs']],
}
def extract(z,dest):
 for n in z.namelist():
  if pathlib.PurePosixPath(n).is_absolute() or '..' in pathlib.PurePosixPath(n).parts:raise ValueError('Unsafe archive member')
 z.extractall(dest)
def manifest(root):
 for f in root.rglob('SHA256SUMS'):
  for line in f.read_text().splitlines():
   if not line.strip():continue
   expected,name=line.split(maxsplit=1);name=name.lstrip('*')
   p=f.parent/name
   assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==expected,('checksum',f.name,name)
def compare(a,b,path=''):
 if isinstance(a,dict):
  assert a.keys()==b.keys(),path
  for k in a:
   if k not in {'code_sha256','scorer_sha256'}:compare(a[k],b[k],path+'/'+k)
 elif isinstance(a,list):
  assert len(a)==len(b),path
  for i,(x,y) in enumerate(zip(a,b)):compare(x,y,path+'/'+str(i))
 elif isinstance(a,(int,float)) and not isinstance(a,bool):assert abs(a-b)<=1e-10,(path,a,b)
 else:assert a==b,path
def run_one(name,out):
 d=out/name
 with zipfile.ZipFile(out/(name+'.zip')) as z:extract(z,d)
 manifest(d)
 env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
 for i,cmd in enumerate(COMMANDS[name]):
  p=subprocess.run([sys.executable,*cmd],cwd=d,env=env,capture_output=True,text=True)
  (d/f'execution-{i}.log').write_text(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError(name+' failed; see its execution log')
 checked=0
 for e in (d/'expected').glob('*'):
  if not e.is_file():continue
  actual=d/'outputs'/e.name
  if not actual.exists():raise AssertionError((name,'missing output',e.name))
  if e.suffix=='.json':compare(json.loads(e.read_text()),json.loads(actual.read_text()))
  else:assert e.read_bytes()==actual.read_bytes(),(name,e.name)
  checked+=1
 if name!='representation_replay':assert checked>0,name
 print('PASS',name,'expected files:',checked,flush=True)
 return {'capsule':name,'status':'PASS','expected_files_compared':checked,'note':'representation suite uses eight internal comparisons' if not checked else ''}
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--jobs',type=int,default=2);a=p.parse_args()
 out=pathlib.Path(a.output).resolve();out.mkdir(parents=True,exist_ok=False)
 with zipfile.ZipFile(ROOT/'data/current/supplementary-material.zip') as z:extract(z,out)
 manifest(out)
 with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(a.jobs,4))) as pool:
  results=list(pool.map(lambda n:run_one(n,out),COMMANDS))
 (out/'VERIFICATION.json').write_text(json.dumps({'status':'PASS','network_calls':0,'capsules':results,'comparison_tolerance':1e-10,'provenance_hash_exceptions':['code_sha256','scorer_sha256']},indent=2)+'\n')
 print('PASS: all ten current capsules; no new model outputs.')
if __name__=='__main__':main()
