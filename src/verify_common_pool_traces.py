"""Independent text/payload replay; does not use the analysis program's cell builder."""
import collections,hashlib,json,math,re
from pathlib import Path
P=Path(__file__).resolve().parents[1];O=P/'data/common_pool'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 m=json.loads((O/'PREOUTPUT_MANIFEST.json').read_text());s=[json.loads(x) for x in (O/'SCHEDULE.jsonl').read_text().splitlines()];u={x['unit']:x for x in json.loads((O/'UNITS.json').read_text())};results=json.loads((O/'RESULTS.json').read_text())
 raw=[json.loads(x) for x in (O/'CALLS.jsonl').read_text().splitlines()];good={}
 for r in raw:
  if r['ok'] and r['identity'] not in good:good[r['identity']]=r
 assert len(good)==6400;observed={};promptgroups=collections.defaultdict(list);tokens=collections.defaultdict(list);finish=collections.Counter();cost=sum(x['charged_or_reserved_usd'] for x in raw)
 for item in s:
  r=good[item['identity']];assert item['payload']==r['payload'];t=r['text'];match=re.search(r'\{.*\}',t,re.S);choice=json.loads(match.group(0))['selected_candidate_id'];assert choice==r['parsed']['selected_candidate_id']
  unit=u[item['unit']];cs={c['candidate_id']:c for c in unit['candidates']};assert choice in cs
  text=item['payload']['messages'][1]['content'];vs=json.loads(text.split('CANDIDATES_JSON=')[1].split('\n\n')[0]);ids=[c['candidate_id'] for c in vs];assert len(set(ids))==len(cs)
  assert all(cs[c['candidate_id']]['text']==c['answer'] for c in vs)
  arm=item['arm'];rank={c['candidate_id']:int(c['support_rank']) for c in vs} if arm!='hidden' else {}
  if rank:
   assert sorted(rank.values())==list(range(1,len(cs)+1));assert rank=={cid:(len(cs)+1-z if arm.endswith('reverse') else z) for cid,z in unit['ordinal'][arm[0]].items()}
  else:assert all(c['support_rank']=='??' for c in vs)
  promptgroups[item['unit'],item['view'],item['order']].append((len(text.encode()),tuple((c['candidate_id'],c['answer']) for c in vs)))
  for metric,value in cs[choice]['scores'].items():
   best=min(rank,key=rank.get) if rank else None
   observed[item['unit'],item['view'],item['order'],arm,metric]=(value,cs[best]['scores'][metric] if best else 0)
  tokens[item['unit'],item['view'],item['order']].append((arm,r.get('usage',{}).get('prompt_tokens')))
  finish.update([r.get('finish_reason','UNKNOWN')])

 checks={}
 for key,res in results.items():
  ds,metric,view=key.split('|');us=[v for v in u.values() if v['dataset']==ds];v=[]
  for unit in us:
   for order in [0,1]:
    d=[0,0]
    for arm,sign in [('M_forward',1),('M_reverse',-1),('H_forward',-1),('H_reverse',1)]:
     a,b=observed[unit['unit'],view,order,arm,metric];d[0]+=sign*a;d[1]+=sign*b
    v.append(d[0]-d[1])
  point=sum(v)/len(v);assert math.isclose(point,res['J_norm']['estimate'],abs_tol=1e-12);checks[key]=point
 assert all(len(v)==5 and len(set(v))==1 for v in promptgroups.values())
 known=[[x for a,x in v] for v in tokens.values() if len(v)==5 and all(x is not None for a,x in v)];rankonly=[[x for a,x in v if a!='hidden'] for v in tokens.values() if len(v)==5 and all(x is not None for a,x in v)];out={'status':'PASS_RAW_TEXT_PAYLOAD_AND_POINT_REPLAY','valid':len(good),'attempts':len(raw),'cost_usd':cost,'cumulative_usd':m['prior_spend']+cost,'matched_prompt_groups':len(promptgroups),'provider_token_groups_available':len(known),'token_equal_groups':sum(len(set(v))==1 for v in known),'max_within_group_token_range':max((max(v)-min(v) for v in known),default=None),'rank_only_token_equal_groups':sum(len(set(v))==1 for v in rankonly),'rank_only_max_token_range':max((max(v)-min(v) for v in rankonly),default=None),'finish_reasons':dict(finish),'J_replayed':checks,'source_integrity_scope':'Release SHA256SUMS verifies sanitized inputs separately','clinical_authority_not_certified':True}
 print(json.dumps(out,indent=2))
if __name__=='__main__':main()
