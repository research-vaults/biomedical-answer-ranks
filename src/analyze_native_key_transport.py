#!/usr/bin/env python3
"""Frozen case-level native-key contrasts; no clinical relabeling or outcome gates."""
import collections,json
import numpy as np
from transport_io import OUT,ROOT,readl,write,sha,parse

def main():
    cfg=json.loads((OUT/'CONFIG.json').read_text());pre=json.loads((OUT/'SELECTOR_MANIFEST.json').read_text())
    assert sha(OUT/'POOLS.json')==pre['pool_sha256'] and sha(OUT/'SELECTOR_SCHEDULE.jsonl')==pre['schedule_sha256']
    cases=cfg['cases'];ids=[c['id'] for c in cases];ps={p['pool_id']:p for p in json.loads((OUT/'POOLS.json').read_text())};schedule=readl(OUT/'SELECTOR_SCHEDULE.jsonl');rows=readl(OUT/'SELECTION_CALLS.jsonl');good={}
    for r in rows:
        if r.get('ok'):good.setdefault(r['identity'],r)
    assert {s['identity'] for s in schedule}<={r['identity'] for r in rows},'All frozen choices must be attempted before analysis'
    rng=np.random.default_rng(202609071700);groups=[np.array([i for i,c in enumerate(cases) if c['medical_task']==t]) for t in cfg['strata']]
    boot=np.concatenate([rng.choice(g,size=(50000,len(g)),replace=True) for g in groups],axis=1)
    def est(v,mask=None):
        v=np.array(v,dtype=float)
        if mask is None:vv=v;b=vv[boot].mean(1)
        else:
            vv=v[np.array(mask,dtype=bool)];ix=np.random.default_rng(202609071701).integers(0,len(vv),size=(50000,len(vv)));b=vv[ix].mean(1)
        return {'estimate':float(vv.mean()),'ci95':np.quantile(b,[.025,.975]).tolist(),'ci97_5':np.quantile(b,[.0125,.9875]).tolist(),'n':len(vv)}
    cells={};checks=[]
    for s in schedule:
        p=ps[s['pool_id']];cs=p['candidates'];byid={c['candidate_id']:c for c in cs};sup=p[s['condition']+'_support'];scores={c['candidate_id']:int(c['option_id']==p['ground_truth']) for c in cs}
        raw=good.get(s['identity']);chosen=None
        if raw:
            assert raw['payload']==s['payload'];parsed,state=parse(raw['text'],'selection',s['allowed_candidate_ids']);assert parsed==raw['parsed'];chosen=parsed['selected_candidate_id']
        f=[m['proposal_call_count'] for m in sup];rr=[sum(1/r for r in m['proposal_ranks_one_based']) for m in sup];ft=[i for i,v in enumerate(f) if v==max(f)];rt=[i for i,v in enumerate(rr) if abs(v-max(rr))<1e-12]
        score=lambda i:scores[cs[i]['candidate_id']]
        cell={'llm':scores.get(chosen,0),'frequency':sum(map(score,ft))/len(ft),'rr':sum(map(score,rt))/len(rt),'random':sum(scores.values())/len(cs),'oracle':max(scores.values()),'frequency_fixed':score(ft[0]),'rr_fixed':score(rt[0]),'valid':int(chosen is not None)}
        cells[s['case_id'],s['allocation'],s['condition'],s['view']]=cell
    methods=['llm','frequency','rr','random','oracle','frequency_fixed','rr_fixed'];results={};vectors={}
    for view in cfg['selectors']:
        def arr(a,c,m):return np.array([cells[i,a,c,view][m] for i in ids])
        D={m:arr('M','true',m)-arr('M','shuffled',m)-arr('H','true',m)+arr('H','shuffled',m) for m in methods};j=D['llm']-D['frequency']
        vectors[view]={'J':j.tolist(),'D':{m:v.tolist() for m,v in D.items()},'absolute':{f'{a}|{c}|{m}':arr(a,c,m).tolist() for a in ['H','M'] for c in ['true','shuffled'] for m in methods}}
        subgroups={f'{field}={val}':est(j,[c[field]==val for c in cases]) for field in ['medical_task','question_type'] for val in sorted({c[field] for c in cases})}
        # Direct independent-stratum differences, rather than comparing whether two CIs cross zero.
        contrasts={}
        for field in ['medical_task','question_type']:
            vals=sorted({c[field] for c in cases})
            for a in range(len(vals)):
                for b in range(a+1,len(vals)):
                    va=j[[c[field]==vals[a] for c in cases]];vb=j[[c[field]==vals[b] for c in cases]];r=np.random.default_rng(202609071703);ds=va[r.integers(0,len(va),(50000,len(va)))].mean(1)-vb[r.integers(0,len(vb),(50000,len(vb)))].mean(1)
                    contrasts[f'{field}:{vals[a]} minus {vals[b]}']={'estimate':float(va.mean()-vb.mean()),'ci95':np.quantile(ds,[.025,.975]).tolist(),'n':[len(va),len(vb)],'status':'EXPLORATORY_POINTWISE'}
        missing=sum(1-cells[i,a,c,view]['valid'] for i in ids for a in ['H','M'] for c in ['true','shuffled'])
        results[view]={'J':est(j),'D':{m:est(v) for m,v in D.items()},'absolute':{f'{a}|{c}|{m}':est(arr(a,c,m)) for a in ['H','M'] for c in ['true','shuffled'] for m in methods},'availability_M_minus_H':est(arr('M','true','oracle')-arr('H','true','oracle')),'final_M_minus_H_true':est(arr('M','true','llm')-arr('H','true','llm')),'rr_minus_llm_M_true':est(arr('M','true','rr')-arr('M','true','llm')),'subgroups':subgroups,'moderator_contrasts':contrasts,'missing_choices':missing,'missing_point_envelope':[float(j.mean())-missing/128,float(j.mean())+missing/128],'leave_one_case_out_mean_range':[float((j.sum()-j).min()/127),float((j.sum()-j).max()/127)]}
    canonical=readl(OUT/'GENERATOR_CANONICAL.jsonl');caseby={c['id']:c for c in cases};generator={}
    failed_cases={r['item']['case_id'] for r in canonical if not r.get('ok')}
    for view in results:
        j=np.array(vectors[view]['J']);kept=[i not in failed_cases for i in ids]
        results[view]['generation_failure_sensitivity']={'failed_case_ids':sorted(failed_cases),'leave_affected_cases_out':est(j,kept),'conservative_point_shift_envelope':[float(j.mean())-4*len(failed_cases)/128,float(j.mean())+4*len(failed_cases)/128],'interpretation':'Technical sensitivity; primary retains every frozen case and empty failed calls'}
    for model in cfg['models']:
        rs=[r for r in canonical if r['item']['model']==model];den=len(rs);valid=[r for r in rs if r.get('ok')]
        generator[model]={'expected_calls':den,'valid':len(valid),'top1_correct':sum(r['parsed']['candidates'][0]['option_id']==caseby[r['item']['case_id']]['label'] for r in valid),'top5_contains_key':sum(any(v['option_id']==caseby[r['item']['case_id']]['label'] for v in r['parsed']['candidates']) for r in valid),'finish_length':sum(r.get('finish_reason')=='length' for r in rs),'extracted_json':sum(r.get('parser_state')=='EXTRACTED_JSON' for r in rs),'valid_prompt_tokens':sum(r.get('usage',{}).get('prompt_tokens',0) for r in valid),'valid_completion_tokens':sum(r.get('usage',{}).get('completion_tokens',0) for r in valid)}
    # Infrastructure/account records are not needed for the scientific estimator.
    # Preserve their aggregate cost separately; reconstruct scientific diagnostics.
    diagnostic=json.loads((OUT/'DIAGNOSTICS_AND_COST.json').read_text())
    diagnostic.update(generation=generator,pool_sizes={a:float(np.mean([len(p['candidates']) for p in ps.values() if p['allocation']==a])) for a in ['H','M']},full_ten_option_pools={a:sum(len(p['candidates'])==10 for p in ps.values() if p['allocation']==a) for a in ['H','M']},valid_selectors=len(good),scheduled_selectors=1024,selector_attempts=len(rows))
    write(OUT/'RESULTS.json',results);write(OUT/'CASE_VECTORS.json',{'case_ids':ids,'by_selector':vectors});write(OUT/'DIAGNOSTICS_AND_COST.json',diagnostic)
    txt=['# MedXpertQA128 native-key transport','', 'Independent source; balanced43/43/42 medical-task strata. Primary case-stratified bootstrap97.5% intervals; two frozen selectors. This is finite-choice transport, not an exact free-form replication.','', '|Selector|J|97.5% interval|M−H availability|M−H final TRUE|','|---|---:|---|---:|---:|']
    for v,r in results.items():txt.append(f"|{v}|{r['J']['estimate']:.6f}|{r['J']['ci97_5']}|{r['availability_M_minus_H']['estimate']:.6f}|{r['final_M_minus_H_true']['estimate']:.6f}|")
    txt+=['','## Completeness and cost',json.dumps(diagnostic,indent=2),'','All fixed cases retained. No native key was shown to generators/selectors. Do not interpret official-key correctness as clinical efficacy or an evidence-stripped intrinsic lineage mechanism.']
    (OUT/'RESULTS.md').write_text('\n'.join(txt)+'\n');print('\n'.join(txt),flush=True)

if __name__=='__main__':main()
