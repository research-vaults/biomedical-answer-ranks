#!/usr/bin/env python3
"""Complete the prespecified control/trap interaction, never a new primary."""
import collections,json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];F=ROOT/'data/fresh_confirmation'
def readl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def main():
 maps={r['pair_id']:r for r in readl(F/'FROZEN_MAP.jsonl')};pools={p['pool_id']:p for p in json.loads((F/'NATURAL_POOL_MANIFEST.json').read_text())['pools']};cases=sorted({p['case_id'] for p in pools.values()});calls={r['identity']:r for r in readl(F/'SELECTOR_CALLS.jsonl') if r.get('ok')};cells={}
 for s in readl(F/'SELECTOR_SCHEDULE.jsonl'):
  p=pools[s['pool_id']];byid={c['candidate_id']:c for c in p['candidates']};cid=calls[s['identity']]['parsed']['ranking'][0];visible=json.loads(s['payload']['messages'][1]['content'].split('CANDIDATES_JSON=')[1].split('\n\n')[0]);top=max(c['proposal_call_count'] for c in visible);ties=[c['candidate_id'] for c in visible if c['proposal_call_count']==top]
  for criterion in ['refinement','strict','exact_reference']:
   score=lambda c:maps[byid[c]['pair_id']][criterion]
   cells[criterion,s['view'],s['case_id'],s['branch'],s['allocation'],s['condition']]={'llm':score(cid),'frequency':sum(map(score,ties))/len(ties),'oracle':max(map(score,byid))}
 rng=np.random.default_rng(202609071422);boot=rng.integers(0,96,(50000,96))
 def est(a):
  a=np.array(a);b=a[boot].mean(1);return {'estimate':float(a.mean()),'ci95':np.quantile(b,[.025,.975]).tolist(),'n_pairs':96}
 out={}
 for criterion in ['refinement','strict','exact_reference']:
  out[criterion]={}
  for view in ['gemini_joint','llama8_joint']:
   branch={};absolute={}
   for b in ['control','trap']:
    branch[b]=np.array([sum(sign*tsign*(cells[criterion,view,c,b,a,t]['llm']-cells[criterion,view,c,b,a,t]['frequency']) for a,sign in [('uniform_mixed',1),('homogeneous_gemma',-1)] for t,tsign in [('true',1),('shuffled',-1)]) for c in cases])
    for a in ['uniform_mixed','homogeneous_gemma']:
     for method in ['llm','frequency','oracle']:absolute[b+'|'+a+'|'+method]=est([cells[criterion,view,c,b,a,'true'][method] for c in cases])
   out[criterion][view]={'J_control_minus_trap':est(branch['control']-branch['trap']),'J_by_branch':{b:est(a) for b,a in branch.items()},'TRUE_absolute':absolute,'scope':'Prespecified secondary regime contrast;not an additional primary or proof of a cognitive mechanism'}
 (F/'BRANCH_INTERACTIONS.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out['refinement'],indent=2),flush=True)
if __name__=='__main__':main()
