"""Exact recorded fresh-pool construction, separated from mapping and serving."""
import collections,hashlib,json,re,unicodedata
from pathlib import Path
def norm(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "").casefold().replace("&", " and ")
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value).split())

def pair_id(reference: str, candidate: str) -> str:
    return "P" + hashlib.sha256(f"{norm(reference)}\0{norm(candidate)}".encode()).hexdigest()[:16].upper()

def fresh_h(namespace: str, *values: object) -> str:
    return hashlib.sha256((namespace + "|" + "|".join(map(str, values))).encode()).hexdigest()

def fresh_pools(cfg,calls,lookup):
 good={r['identity']:r for r in calls if r.get('ok') or r.get('failed_call_empty')}
 pools=[];surfaces={}
 for case in cfg['cases']:
  for branch in cfg['branches']:
   for allocation,spec in cfg['allocations'].items():
    ids=[f"fresh96gen::{model}::{case['case_id']}::{branch}::{s}" for model,indices in spec.items() for s in indices]
    occurrences=collections.defaultdict(list)
    for identity in ids:
     row=good[identity]; item=row['item']
     for rank,c in enumerate(row['parsed']['candidates']):
      raw=' '.join(c['diagnosis'].split()); diagnosis=lookup.get(norm(raw),raw); key=norm(diagnosis)
      if key: occurrences[key].append(dict(source_identity=identity,source_model=item['model'],source_lineage=item['lineage'],sample_index=item['sample_index'],rank_in_call=rank,raw_diagnosis=raw,diagnosis=diagnosis,rationale=' '.join(c['rationale'].split()[:18])))
    candidates=[]
    for key,values in occurrences.items():
     r=min(values,key=lambda x:(x['rank_in_call'],fresh_h(cfg['seed_namespace'],'representative',x['source_identity'],key)))
     pid=pair_id(case[branch+'_label'],r['diagnosis']); surfaces[pid]=(case[branch+'_label'],r['diagnosis'])
     candidates.append(dict(pair_id=pid,diagnosis=r['diagnosis'],diagnosis_normalized=key,rationale=r['rationale'],frequency=len({x['source_identity'] for x in values}),source_models=sorted({x['source_model'] for x in values}),all_occurrences=values))
    candidates.sort(key=lambda x:fresh_h(cfg['seed_namespace'],'natural-order',case['case_id'],branch,allocation,x['diagnosis_normalized']))
    for i,c in enumerate(candidates,1): c['candidate_id']=f'C{i:03d}'
    pools.append(dict(pool_id=f"fresh96natural::{case['case_id']}::{branch}::{allocation}",case_id=case['case_id'],branch=branch,allocation=allocation,ground_truth=case[branch+'_label'],patient_record=case[branch+'_narrative_raw'],source_call_count=len(ids),source_calls=ids,candidate_count=len(candidates),candidates=candidates,orders={'order0':[c['candidate_id'] for c in candidates]}))
 return pools
