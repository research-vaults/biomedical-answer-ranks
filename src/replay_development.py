#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parents[1]/'data/development_replay'
def load(name):return json.loads((HERE/name).read_text())
def main():
    for line in (HERE/'SHA256SUMS').read_text().splitlines():
        expected,name=line.split('  ',1)
        assert hashlib.sha256((HERE/name).read_bytes()).hexdigest()==expected,name
    data=load('inputs.json');scenarios=load('scenarios.json');expected=load('expected_c2.json');exp3=load('expected_c3b.json')
    cases=sorted({p['case_id'] for p in data['pools']})
    assert len(cases)==48 and len(data['pools'])==192
    output={}
    for name,sc in scenarios.items():
        branch={}
        for p in data['pools']:
            prefix='homogeneous' if p['allocation']=='homogeneous_gemma' else 'mixed'
            r=branch.setdefault((p['case_id'],p['branch']),{})
            labels={}
            for c in p['candidates']:
                rel=data['relations'][c['pair_id']]['original_relation' if sc['version']=='original_frozen' else 'relation']
                if c['pair_id'] in sc['promoted_pairs']:rel='EXACT_OR_SYNONYM'
                labels[c['candidate_id']]=int(rel=='EXACT_OR_SYNONYM' or sc['endpoint']=='inclusive' and rel=='ACCEPTABLE_PARENT_OR_SUBTYPE')
            r[prefix+'_available']=int(any(labels.values()))
            r[prefix+'_final']=labels[p['c2_ranking'][0]]
            assert set(p['c2_ranking'])==set(labels)
            for arm,completion in p['c3b_completions'].items():
                obj=json.loads(completion)
                assert set(obj)=={'selected_candidate_id'}
                r[prefix+'_'+arm]=labels[obj['selected_candidate_id']]
        for r in branch.values():
            r['access_effect']=r['mixed_available']-r['homogeneous_available']
            r['final_effect']=r['mixed_final']-r['homogeneous_final']
            r['allocation_interface_interaction']=r['mixed_true']-r['mixed_hidden']-r['homogeneous_true']+r['homogeneous_hidden']
            r['mixed_true_minus_shuffled']=r['mixed_true']-r['mixed_shuffled']
        summary={}
        for k in next(iter(branch.values())):
            observed=sum(r[k] for r in branch.values())/96
            ref=expected[name] if k in expected[name] else exp3[name]
            assert abs(observed-ref[k]['estimate'])<1e-12,(name,k)
            summary[k]=observed
        # Exact case-resampling reconstruction for the two C3B screening contrasts.
        fields=['allocation_interface_interaction','mixed_true_minus_shuffled']
        vals=np.array([[sum(r[k] for (cid,b),r in branch.items() if cid==case)/2 for k in fields] for case in cases])
        ix=np.random.default_rng(data['c3b_bootstrap_seed']).integers(0,48,size=(50000,48))
        boot=vals[ix].mean(axis=1)
        for i,k in enumerate(fields):
            for label,quantiles in [('ci95',[.025,.975]),('ci97_5',[.0125,.9875])]:
                assert np.allclose(np.quantile(boot[:,i],quantiles),exp3[name][k][label])
        output[name]=summary
    result={'status':'PASS','cases':48,'branches':96,'pools':192,'scenarios':13,'c3b_choices':576,
            'c2_and_c3b_point_estimates_match':True,'c3b_focal_confidence_intervals_match':True,
            'criterion_validity_or_fresh_generation_certified':False,'effects':output}
    (HERE/'REPLAY_RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print('PASS: 13 scenarios, C2/C3B point estimates, and both C3B focal confidence intervals. Criterion validity is not certified.')
if __name__=='__main__':main()
