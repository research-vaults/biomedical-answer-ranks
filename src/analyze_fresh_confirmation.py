#!/usr/bin/env python3
"""Registered fresh-pair contrasts, rule consequences and shared-label bounds."""
import collections, hashlib, json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'data/fresh_confirmation'
def readl(p):return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 manifest=json.loads((OUT/'SELECTOR_MANIFEST.json').read_text());assert sha(OUT/'FROZEN_MAP.jsonl')==manifest['map_sha256']
 pools={p['pool_id']:p for p in json.loads((OUT/'NATURAL_POOL_MANIFEST.json').read_text())['pools']};maps={r['pair_id']:r for r in readl(OUT/'FROZEN_MAP.jsonl')}
 schedule=readl(OUT/'SELECTOR_SCHEDULE.jsonl');good={r['identity']:r for r in readl(OUT/'SELECTOR_CALLS.jsonl') if r.get('ok')};cases=sorted({p['case_id'] for p in pools.values()}); assert len(cases)==96
 rng=np.random.default_rng(202609071422);boot=rng.integers(0,96,size=(50000,96));index={c:i for i,c in enumerate(cases)}
 def estimate(v):
  v=np.array(v); b=v[boot].mean(1)
  return {'estimate':float(v.mean()),'ci95':np.quantile(b,[.025,.975]).tolist(),'ci97_5':np.quantile(b,[.0125,.9875]).tolist(),'n_pairs':96}
 cells=collections.defaultdict(dict); co=collections.defaultdict(lambda:collections.defaultdict(float)); missing=collections.Counter();displacements=[]
 for item in schedule:
  p=pools[item['pool_id']];byid={c['candidate_id']:c for c in p['candidates']};visible=json.loads(item['payload']['messages'][1]['content'].split('CANDIDATES_JSON=')[1].split('\n\n')[0]);r=good.get(item['identity'])
  if r:assert r['payload']==item['payload'];cid=r['parsed']['ranking'][0]
  else:cid=None;missing[item['view']]+=1
  maxima=max(c['proposal_call_count'] for c in visible);ties=[c['candidate_id'] for c in visible if c['proposal_call_count']==maxima]
  rr={c['candidate_id']:sum(1/r for r in c['proposal_ranks_one_based']) for c in visible};rt=max(rr.values());rrties=[c for c,s in rr.items() if abs(s-rt)<1e-12]
  w=(1 if p['allocation']!='homogeneous_gemma' else -1)*(1 if item['condition']=='true' else -1)/192
  if cid: co[item['view']][byid[cid]['pair_id']]+=w
  for c in ties:co[item['view']][byid[c]['pair_id']]-=w/len(ties)
  for scoring in ['refinement','strict','exact_reference']:
   score=lambda c:maps[byid[c]['pair_id']][scoring]
   cells[scoring,item['view'],p['case_id'],p['branch'],p['allocation'],item['condition']]={'llm':score(cid) if cid else 0,'frequency':sum(map(score,ties))/len(ties),'rr':sum(map(score,rrties))/len(rrties),'frequency_fixed':score(sorted(ties)[0]),'rr_fixed':score(sorted(rrties)[0]),'random':sum(map(score,byid))/len(byid),'oracle':max(map(score,byid)),'valid':int(cid is not None)}
  if item['condition']=='shuffled' and item['view']=='gemini_joint':
   actual={c['candidate_id']:(c['frequency'],sorted(min(o['rank_in_call']+1 for o in c['all_occurrences'] if o['source_identity']==identity) for identity in {o['source_identity'] for o in c['all_occurrences']})) for c in p['candidates']}
   displacements.append({'pool_id':p['pool_id'],'allocation':p['allocation'],'candidate_count':len(visible),'mean_absolute_count_displacement':float(np.mean([abs(c['proposal_call_count']-actual[c['candidate_id']][0]) for c in visible])),'unchanged_support_fraction':sum((c['proposal_call_count'],c['proposal_ranks_one_based'])==actual[c['candidate_id']] for c in visible)/len(visible)})
 failed_generation=[r for r in readl(OUT/'GENERATOR_CANONICAL.jsonl') if r.get('failed_call_empty')];failed_cases={r['item']['case_id'] for r in failed_generation};failed_branches={(r['item']['case_id'],r['item']['branch']) for r in failed_generation}
 results={};vectors={};allocs=['homogeneous_gemma','uniform_mixed'];branches=['control','trap'];methods=['llm','frequency','rr','frequency_fixed','rr_fixed','random','oracle']
 for scoring in ['refinement','strict','exact_reference']:
  results[scoring]={}
  for view in ['gemini_joint','llama8_joint']:
   def arr(allocation,condition,method,branch=None):return np.array([np.mean([cells[scoring,view,c,b,allocation,condition][method] for b in ([branch] if branch else branches)]) for c in cases])
   D={m:arr(allocs[1],'true',m)-arr(allocs[1],'shuffled',m)-arr(allocs[0],'true',m)+arr(allocs[0],'shuffled',m) for m in methods}
   j=D['llm']-D['frequency']; absolute={f'{a}|{t}|{m}':estimate(arr(a,t,m)) for a in allocs for t in ['true','shuffled'] for m in methods}
   bybranch={b:estimate(arr(allocs[1],'true','llm',b)-arr(allocs[1],'shuffled','llm',b)-arr(allocs[0],'true','llm',b)+arr(allocs[0],'shuffled','llm',b)-arr(allocs[1],'true','frequency',b)+arr(allocs[1],'shuffled','frequency',b)+arr(allocs[0],'true','frequency',b)-arr(allocs[0],'shuffled','frequency',b)) for b in branches}
   c=co[view];critical={p:w for p,w in c.items() if maps[p]['unresolved'] and abs(w)>1e-12};constant=sum(w*maps[p][scoring] for p,w in c.items() if p not in critical)
   lower=constant+sum(min(w,0) for w in critical.values());upper=constant+sum(max(w,0) for w in critical.values())
   rr_gain=arr(allocs[1],'true','rr')-arr(allocs[1],'true','llm');f_gain=arr(allocs[1],'true','frequency')-arr(allocs[1],'true','llm')
   results[scoring][view]={'J':estimate(j),'D':{m:estimate(v) for m,v in D.items()},'absolute':absolute,'J_by_branch':bybranch,'rr_minus_llm_mixed_true':estimate(rr_gain),'frequency_minus_llm_mixed_true':estimate(f_gain),'availability_M_minus_H':estimate(arr(allocs[1],'true','oracle')-arr(allocs[0],'true','oracle')),'final_M_minus_H_true':estimate(arr(allocs[1],'true','llm')-arr(allocs[0],'true','llm')),'shared_label_J_bounds':[lower,upper],'critical_uncertain_pairs':len(critical),'missing_choices':missing[view],'missing_J_envelope':[float(j.mean())-missing[view]/192,float(j.mean())+missing[view]/192]}
   kept=np.array([z for case,z in zip(cases,j) if case not in failed_cases]);rb=np.random.default_rng(202609071424).integers(0,len(kept),size=(50000,len(kept)));bv=kept[rb].mean(1)
   results[scoring][view]['generation_failure_sensitivity']={'affected_case_ids':sorted(failed_cases),'leave_affected_pairs_out':{'estimate':float(kept.mean()),'ci95':np.quantile(bv,[.025,.975]).tolist(),'n_pairs':len(kept)},'conservative_point_shift_envelope':[float(j.mean())-4*len(failed_branches)/192,float(j.mean())+4*len(failed_branches)/192],'scope':'one Qwen-only missing candidate call; all pairs retained in primary, pair deletion is a disclosed technical sensitivity'}
   assert abs(sum(c[p]*maps[p][scoring] for p in c)-j.mean())<1e-10
   vectors[scoring+'|'+view]=j.tolist()
 write(OUT/'RESULTS.json',results);write(OUT/'PAIR_VECTORS.json',{'case_ids':cases,'J':vectors});write(OUT/'DISPLACEMENT.json',displacements)
 cost={'GENERATION':json.loads((OUT/'GENERATION_FINAL_MANIFEST.json').read_text()),'SELECTION':json.loads((OUT/'SELECTION_RUN_MANIFEST.json').read_text())};write(OUT/'TOTAL_COST.json',{'phases':cost,'total_usd':sum(x['cost_usd'] for x in cost.values()),'billed_and_estimated_mixed':True})
 text=['# Fresh96 frozen confirmation','', '96 disjoint paired cases;192 branches. Intervals resample case pairs. Primary refinement endpoint, two frozen selectors;97.5% intervals control the two-primary family. Exact reference is a deliberately narrow sensitivity, not clinical truth.','', '|Endpoint|Selector|J|97.5% interval|RR minus LLM, mixed TRUE|Availability M−H|','|---|---|---:|---|---:|---:|']
 for s,vs in results.items():
  for v,r in vs.items():text.append(f"|{s}|{v}|{r['J']['estimate']:.4f}|{r['J']['ci97_5']}|{r['rr_minus_llm_mixed_true']['estimate']:.4f}|{r['availability_M_minus_H']['estimate']:.4f}|")
 text+=['','## Scoring and implementation limits',f"Unresolved mapping relations: {sum(m['unresolved'] for m in maps.values())}/{len(maps)}. Every corresponding occurrence shares the same label in the uncertainty envelope. These unrestricted bounds are not probability intervals or clinically plausible adjudications.",f"Valid choices: {len(good)}/{len(schedule)}. Invalid/missing choices score0;missing-outcome envelopes are retained. Costs: {sum(x['cost_usd'] for x in cost.values()):.6f} USD. Fixed-rule choices never use reference labels. All raw outputs remain saved."]
 (OUT/'RESULTS.md').write_text('\n'.join(text)+'\n')
 old=json.loads((ROOT/'data/joint_reference/RESULTS.json').read_text()); oldl=json.loads((ROOT/'data/selector_extension/RESULTS.json').read_text());fig,ax=plt.subplots(figsize=(6.8,2.6))
 for i,(name,v,dev) in enumerate([('Gemini','gemini_joint',old['refinement_temporal_etiologic_severity_or_site']['gemini_joint_reference']['J']),('Llama8B','llama8_joint',oldl['refinement_temporal_etiologic_severity_or_site']['llama8_joint']['J'])]):
  for j,(label,r,key) in enumerate([('Development48',dev,'ci95'),('Fresh96',results['refinement'][v]['J'],'ci97_5')]):
   e=r['estimate']*100;lo,hi=np.array(r[key])*100;ax.errorbar(e,i+(j-.5)*.2,xerr=[[e-lo],[hi-e]],fmt='o',capsize=3,color=['#7a7a7a','#145c9e'][j],label=label if i==0 else None)
 ax.axvline(0,color='gray',lw=.8);ax.set_yticks([0,1],['Gemini Flash-Lite','Llama3.1-8B']);ax.invert_yaxis();ax.set_xlabel('J, all-refinement scoring (percentage points)');ax.legend(fontsize=8);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(OUT/'FRESH_CONFIRMATION.png',dpi=150);fig.savefig(ROOT/'manuscript/figures/FRESH_CONFIRMATION.pdf',bbox_inches='tight');plt.close(fig)
 print('\n'.join(text),flush=True)
if __name__=='__main__':main()
