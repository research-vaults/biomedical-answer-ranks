"""Frozen common-pool analysis. Orders and branches are not independent cases."""
import collections,json
from pathlib import Path
import numpy as np
import common_pool_io as run
OUT=run.OUT
ARMS=['H_forward','H_reverse','M_forward','M_reverse','hidden']
def contrast(v):return v['M_forward']-v['M_reverse']-v['H_forward']+v['H_reverse']
def main():
 m=json.loads((OUT/'PREOUTPUT_MANIFEST.json').read_text());assert run.sha(Path(__file__))==m['analysis_sha256']
 units=json.loads((OUT/'UNITS.json').read_text());byunit={u['unit']:u for u in units}
 schedule=run.readl(OUT/'SCHEDULE.jsonl');records=run.readl(OUT/'CALLS.jsonl');good={}
 for r in records:
  if r.get('ok') and r['identity'] not in good:good[r['identity']]=r
 cells={};scores={};missing=collections.Counter()
 for it in schedule:
  u=byunit[it['unit']];r=good.get(it['identity']);cid=r['parsed']['selected_candidate_id'] if r else None
  if r:assert r['payload']==it['payload']
  else:missing[it['dataset'],it['view']]+=1
  cs={c['candidate_id']:c for c in u['candidates']};arm=it['arm']
  top=None if arm=='hidden' else min(cs,key=lambda c:u['ordinal'][arm[0]][c] if arm.endswith('forward') else -u['ordinal'][arm[0]][c])
  cells[it['unit'],it['view'],it['order'],arm]={'cid':cid,'top':top,'valid':int(r is not None)}
  for metric in next(iter(cs.values()))['scores']:
   score=lambda c:cs[c]['scores'][metric] if c else 0
   scores[it['unit'],it['view'],it['order'],arm,metric]={'llm':score(cid),'top_rank':score(top),'random':float(np.mean([score(c) for c in cs])),'oracle':max(score(c) for c in cs)}
 results={};vectors={}
 for ds in ['medeinst','medx']:
  us=[u for u in units if u['dataset']==ds];cases=sorted({u['case_id'] for u in us});groups={c:[u for u in us if u['case_id']==c] for c in cases};n=len(cases)
  rng=np.random.default_rng(202609071812 if ds=='medeinst' else 202609071813)
  strata=collections.defaultdict(list)
  for i,c in enumerate(cases):strata[groups[c][0]['stratum']].append(i)
  boot=np.concatenate([rng.choice(ix,(50000,len(ix)),replace=True) for ix in strata.values()],axis=1)
  def est(v):
   v=np.array(v,float);b=v[boot].mean(1)
   return {'estimate':float(v.mean()),'ci95':np.quantile(b,[.025,.975]).tolist(),'ci98_75':np.quantile(b,[.00625,.99375]).tolist(),'n_cases':n}
  def avg(fn):return np.array([np.mean([fn(u,o) for u in groups[c] for o in [0,1]]) for c in cases])
  for metric in us[0]['candidates'][0]['scores']:
   for view in run.MODELS:
    key=f'{ds}|{metric}|{view}';values={method:{arm:avg(lambda u,o:scores[u['unit'],view,o,arm,metric][method]) for arm in ARMS} for method in ['llm','top_rank','random','oracle']}
    d={method:contrast(values[method]) for method in ['llm','top_rank']};j=d['llm']-d['top_rank'];absolute={arm:{method:est(values[method][arm]) for method in values if not(arm=='hidden' and method=='top_rank')} for arm in ARMS}
    r={'J_norm':est(j),'D':{k:est(v) for k,v in d.items()},'absolute':absolute,'forward_M_minus_H':est(values['llm']['M_forward']-values['llm']['H_forward']),'missing_choices':missing[ds,view]};r['source_comparisons']={}
    for a in ['H','M']:
     f=values['llm'][a+'_forward'];hidden=values['llm']['hidden']
     def outcome(u,o,arm):return scores[u['unit'],view,o,arm,metric]['llm']
     fixes=avg(lambda u,o:int(outcome(u,o,a+'_forward')==1 and outcome(u,o,'hidden')==0));harms=avg(lambda u,o:int(outcome(u,o,a+'_forward')==0 and outcome(u,o,'hidden')==1))
     assert np.allclose(f-hidden,fixes-harms)
     r['source_comparisons'][a]={'forward_minus_hidden':est(f-hidden),'fixes':est(fixes),'harms':est(harms),'choice_switch_forward_vs_reverse':est(avg(lambda u,o:int(cells[u['unit'],view,o,a+'_forward']['cid']!=cells[u['unit'],view,o,a+'_reverse']['cid']))),'follow_best_forward':est(avg(lambda u,o:int(cells[u['unit'],view,o,a+'_forward']['cid']==cells[u['unit'],view,o,a+'_forward']['top']))),'follow_best_reverse':est(avg(lambda u,o:int(cells[u['unit'],view,o,a+'_reverse']['cid']==cells[u['unit'],view,o,a+'_reverse']['top'])))}
    byorder={}
    for o in [0,1]:
     ar={method:{arm:np.array([np.mean([scores[u['unit'],view,o,arm,metric][method] for u in groups[c]]) for c in cases]) for arm in ARMS} for method in ['llm','top_rank']};byorder[o]=contrast(ar['llm'])-contrast(ar['top_rank'])
    r['J_order1_minus_order0']=est(byorder[1]-byorder[0]);r['J_by_order']={str(o):est(v) for o,v in byorder.items()}
    complete=np.array([all(cells[u['unit'],view,o,a]['valid'] for u in groups[c] for o in [0,1] for a in ARMS[:4]) for c in cases]);r['complete_cases']=int(complete.sum());r['complete_case_J_point']=float(j[complete].mean()) if complete.any() else None
    # Four signed LLM terms; each failed cell can alter its own mean by at most1/(items*orders).
    critical=sum(not cells[u['unit'],view,o,a]['valid'] for u in us for o in [0,1] for a in ARMS[:4]);delta=critical/(len(us)*2);r['missing_outcome_envelope']=[float(j.mean()-delta),float(j.mean()+delta)]
    results[key]=r;vectors[key]={'case_ids':cases,'J_norm':j.tolist(),'D_llm':d['llm'].tolist(),'D_top_rank':d['top_rank'].tolist(),'absolute':{method:{a:v.tolist() for a,v in arms.items()} for method,arms in values.items()}}
 run.write(OUT/'RESULTS.json',results);run.write(OUT/'CASE_VECTORS.json',vectors)
 lines=['# Common-pool ordinal-support results','','Prospective controlled diagnostic on reused cases; not confirmation of original natural-count J. Four designated98.75% intervals; sensitivities and secondary contrasts retain their labels.','', '|Dataset/scoring/selector|J_norm|98.75% interval|H forward−hidden|M forward−hidden|','|---|---:|---|---:|---:|']
 for k,r in results.items():lines.append(f"|{k}|{r['J_norm']['estimate']:.4f}|{r['J_norm']['ci98_75']}|{r['source_comparisons']['H']['forward_minus_hidden']['estimate']:.4f}|{r['source_comparisons']['M']['forward_minus_hidden']['estimate']:.4f}|")
 lines+=['',f'Valid choices {len(good)}/{len(schedule)}. Missing outcomes remain zero with envelopes and complete-case sensitivity. Costs and raw payloads are in RUN_MANIFEST.json and CALLS.jsonl. Clinical-map uncertainty is not removed by these intervals.']
 (OUT/'RESULTS.md').write_text('\n'.join(lines)+'\n');print('\n'.join(lines))
if __name__=='__main__':
 assert contrast({'M_forward':1,'M_reverse':0,'H_forward':0,'H_reverse':1})==2
 main()
