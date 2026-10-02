#!/usr/bin/env python3
import collections,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'data/fresh_confirmation';O=ROOT/'data/order_challenge'
def readl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def main():
 cases=sorted(json.loads((O/'PREOUTCOME_CASES.json').read_text())['case_ids']);idx={c:i for i,c in enumerate(cases)};assert len(cases)==24
 maps={r['pair_id']:r for r in readl(F/'FROZEN_MAP.jsonl')};pools={p['pool_id']:p for p in json.loads((F/'NATURAL_POOL_MANIFEST.json').read_text())['pools']};good={r['identity']:r for path in [F/'SELECTOR_CALLS.jsonl',O/'SELECTOR_CALLS.jsonl'] for r in readl(path) if r.get('ok')};values=collections.defaultdict(dict)
 schedule=[dict(x,variant='original') for x in readl(F/'SELECTOR_SCHEDULE.jsonl') if x['case_id'] in idx]+readl(O/'SELECTOR_SCHEDULE.jsonl');missing=0
 for item in schedule:
  p=pools[item['pool_id']];byid={c['candidate_id']:c for c in p['candidates']};v=json.loads(item['payload']['messages'][1]['content'].split('CANDIDATES_JSON=')[1].split('\n\n')[0]);r=good.get(item['identity']);cid=r['parsed']['ranking'][0] if r else None;missing+=not bool(r)
  if r:assert r['payload']==item['payload']
  maximum=max(c['proposal_call_count'] for c in v);ties=[c['candidate_id'] for c in v if c['proposal_call_count']==maximum]
  for s in ['refinement','strict','exact_reference']:
   score=lambda c:maps[byid[c]['pair_id']][s]
   val=(score(cid) if cid else 0)-sum(map(score,ties))/len(ties)
   values[s,item['view'],item['variant']][p['case_id'],p['branch'],p['allocation'],item['condition']]=val
 rng=np.random.default_rng(202609071423);boot=rng.integers(0,24,size=(50000,24))
 def est(a):
  a=np.array(a);b=a[boot].mean(1);return {'estimate':float(a.mean()),'ci95':np.quantile(b,[.025,.975]).tolist(),'n_pairs':24}
 results={}
 for s in ['refinement','strict','exact_reference']:
  results[s]={}
  for view in ['gemini_joint','llama8_joint']:
   arrays={}
   for variant in ['original','alternate_order','alternate_shuffle']:
    cells=values[s,view,variant];original=values[s,view,'original'];a=[]
    for case in cases:
     z=0
     for b in ['control','trap']:
      for allocation,sign in [('uniform_mixed',1),('homogeneous_gemma',-1)]:
       for t,tsign in [('true',1),('shuffled',-1)]:
        source=original if variant=='alternate_shuffle' and t=='true' else cells
        z+=sign*tsign*source[case,b,allocation,t]/2
     a.append(z)
    arrays[variant]=np.array(a)
   results[s][view]={**{k:est(a) for k,a in arrays.items()},**{k+'_minus_original':est(a-arrays['original']) for k,a in arrays.items() if k!='original'}}
 out={'status':'COMPLETE_RETAIN_ALL','missing_choices':missing,'results':results,'interpretation':'24-pair conditional robustness, not fresh independent confirmation; pointwise intervals; original TRUE reused for alternate shuffle'};(O/'RESULTS.json').write_text(json.dumps(out,indent=2)+'\n')
 lines=['# Frozen order/shuffle challenge','',out['interpretation'],'','|Scoring|Selector|Original J|Alternate-order J|Paired order change,95%CI|Alternate-shuffle J|Paired shuffle change,95%CI|','|---|---|---:|---:|---|---:|---|']
 for s,vs in results.items():
  for v,r in vs.items():lines.append(f"|{s}|{v}|{r['original']['estimate']:.4f}|{r['alternate_order']['estimate']:.4f}|{r['alternate_order_minus_original']}|{r['alternate_shuffle']['estimate']:.4f}|{r['alternate_shuffle_minus_original']}|")
 (O/'RESULTS.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines),flush=True)
if __name__=='__main__':main()
