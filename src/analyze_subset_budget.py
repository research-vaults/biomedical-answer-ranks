#!/usr/bin/env python3
"""Post-hoc all-subset, matched-call-budget replay; no inference or relabeling."""
import collections,hashlib,itertools,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];F=R/'data/fresh_confirmation';O=R/'data/subset_budget'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 O.mkdir(exist_ok=True)
 pools=json.loads((F/'NATURAL_POOL_MANIFEST.json').read_text())['pools'];maps={r['pair_id']:r for r in map(json.loads,(F/'FROZEN_MAP.jsonl').read_text().splitlines())};cfg=json.loads((F/'CONFIG.json').read_text());models=sorted(m['key'] for m in cfg['models']);cases=sorted(c['case_id'] for c in cfg['cases']);by={(p['case_id'],p['branch'],p['allocation']):p for p in pools}
 subsets=[s for k in range(1,5) for s in itertools.combinations(models,k)];policies={'+'.join(s):{m:set(range(2)) for m in s} for s in subsets};policies.update({f'H{b}':{'gemma4_26b':set(range(b))} for b in [2,4,6,8]})
 cells={};metrics=['oracle','frequency','rr','random','pool_size'];criteria=['strict','refinement','exact_reference']
 for case in cases:
  for branch in ['control','trap']:
   universe={}
   for allocation in ['homogeneous_gemma','uniform_mixed']:
    for c in by[case,branch,allocation]['candidates']:
     x=universe.setdefault(c['diagnosis_normalized'],{'pair_id':c['pair_id'],'occ':{}});assert x['pair_id']==c['pair_id']
     for occ in c['all_occurrences']:
      identity=(occ['source_identity'],occ['rank_in_call']);x['occ'][identity]=occ
   for policy,spec in policies.items():
    cand={}
    for key,x in universe.items():
     best={}
     for occ in x['occ'].values():
      if occ['source_model'] in spec and occ['sample_index'] in spec[occ['source_model']]:best[occ['source_identity']]=min(best.get(occ['source_identity'],999),occ['rank_in_call']+1)
     if best:cand[key]={'pair_id':x['pair_id'],'frequency':len(best),'rr':sum(1/r for r in best.values())}
    assert cand
    for criterion in criteria:
     score={k:maps[c['pair_id']][criterion] for k,c in cand.items()};v={'pool_size':len(cand),'oracle':max(score.values()),'random':float(np.mean(list(score.values())))}
     for method in ['frequency','rr']:
      maximum=max(c[method] for c in cand.values());ties=[k for k,c in cand.items() if abs(c[method]-maximum)<1e-12];v[method]=float(np.mean([score[k] for k in ties]))
     cells[case,branch,policy,criterion]=v
 rng=np.random.default_rng(202609071620);boot=rng.integers(0,96,size=(50000,96))
 def est(a):
  a=np.array(a);z=a[boot].mean(1);return {'estimate':float(a.mean()),'ci95':np.quantile(z,[.025,.975]).tolist(),'n_case_pairs':96}
 def arr(policy,criterion,metric):return np.array([np.mean([cells[c,b,policy,criterion][metric] for b in ['control','trap']]) for c in cases])
 full='+'.join(models);summary={};vectors={};primary=json.loads((F/'RESULTS.json').read_text());checks=0
 for criterion in criteria:
  summary[criterion]={'policies':{},'equal_subset_mean':{},'leave_one_out':{}}
  for policy,spec in policies.items():
   budget=sum(map(len,spec.values()));summary[criterion]['policies'][policy]={'models':list(spec),'calls':budget,'absolute':{m:est(arr(policy,criterion,m)) for m in metrics},'minus_matched_H':{m:est(arr(policy,criterion,m)-arr(f'H{budget}',criterion,m)) for m in metrics}}
   vectors[criterion+'|'+policy]={m:arr(policy,criterion,m).tolist() for m in metrics}
  for k in range(1,5):
   selected=['+'.join(s) for s in subsets if len(s)==k];summary[criterion]['equal_subset_mean'][str(k)]={m:est(np.mean([arr(p,criterion,m) for p in selected],axis=0)-arr(f'H{k*2}',criterion,m)) for m in metrics}
  for removed in models:
   policy='+'.join(m for m in models if m!=removed);summary[criterion]['leave_one_out'][removed]={m:est(arr(policy,criterion,m)-arr(full,criterion,m)) for m in metrics}
  for policy,allocation in [('H8','homogeneous_gemma'),(full,'uniform_mixed')]:
   for method in ['oracle','frequency','rr','random']:
    expected=primary[criterion]['gemini_joint']['absolute'][allocation+'|true|'+method]['estimate'];assert abs(arr(policy,criterion,method).mean()-expected)<1e-12;(checks:=checks+1)
 assert np.array_equal(arr('H2','strict','frequency'),arr('gemma4_26b','strict','frequency'))
 report={'status':'POST_HOC_SAVED_OUTPUT_REPLAY','case_pairs':96,'branches':192,'model_subsets':15,'distinct_policy_count':18,'primary_cells_reconstructed':checks,'new_calls':0,'cost_usd':0,'summary':summary,'input_hashes':{p.name:sha(p) for p in [F/'NATURAL_POOL_MANIFEST.json',F/'FROZEN_MAP.jsonl',F/'RESULTS.json']},'code_sha256':sha(Path(__file__))}
 (O/'SUBSET_BUDGET_RESULTS.json').write_text(json.dumps(report,indent=2)+'\n');(O/'SUBSET_PAIR_VECTORS.json').write_text(json.dumps({'case_ids':cases,'vectors':vectors})+'\n')
 lines=['# All15 subset / matched-call replay','', 'Exploratory analysis on saved96pairs; no new LLM choices or criterion authority. Intervals are pointwise95%; equal subset means are descriptive, not best-subset selection.','', '|Criterion|Models k|Access difference|Frequency difference|RR difference|','|---|---:|---|---|---|']
 for criterion in criteria:
  for k,row in summary[criterion]['equal_subset_mean'].items():lines.append('|'+criterion+'|'+k+'|'+'|'.join(f"{row[m]['estimate']:.4f} {row[m]['ci95']}" for m in ['oracle','frequency','rr'])+'|')
 (O/'SUBSET_BUDGET_RESULTS.md').write_text('\n'.join(lines)+'\n')
 fig,axes=plt.subplots(1,2,figsize=(7,2.1));colors={'oracle':'#007c83','frequency':'#386cb0','rr':'#ba4a22'}
 for ax,criterion in zip(axes,['strict','refinement']):
  for j,method in enumerate(['oracle','frequency','rr']):
   rows=[summary[criterion]['equal_subset_mean'][str(k)][method] for k in range(1,5)];y=np.array([r['estimate'] for r in rows])*100;ci=np.array([r['ci95'] for r in rows])*100;x=np.array([2,4,6,8])+(j-1)*.15;ax.errorbar(x,y,yerr=[y-ci[:,0],ci[:,1]-y],marker='o',capsize=2,color=colors[method],label=method)
  ax.axhline(0,color='.65',lw=.7);ax.set_xticks([2,4,6,8]);ax.set_xlabel('Proposal calls (2 per included model)');ax.set_title(criterion.capitalize());ax.spines[['top','right']].set_visible(False)
 axes[0].set_ylabel('Difference from Gemma (pp)');handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,['Credited availability','Frequency','Reciprocal rank'],loc='upper center',ncol=3,frameon=False);fig.tight_layout(rect=(0,0,1,.88));fig.savefig(O/'SUBSET_BUDGET.pdf',bbox_inches='tight');fig.savefig(O/'SUBSET_BUDGET.png',dpi=180,bbox_inches='tight')
 print(json.dumps({k:report[k] for k in report if k!='summary'},indent=2));print('\n'.join(lines),flush=True)
if __name__=='__main__':main()
