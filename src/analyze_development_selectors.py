"""Independently reconstruct development selector interactions from scored choices."""
import json
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def main():
    count=0
    for folder in ['selector_extension','joint_reference']:
        p=ROOT/'data'/folder
        rows=[json.loads(x) for x in (p/'SCORED_ROWS.jsonl').read_text().splitlines()]
        expected=json.loads((p/'RESULTS.json').read_text())
        for scenario,views in expected.items():
            for view,r in views.items():
                chosen=[x for x in rows if x['scenario']==scenario and x['view']==view]
                cases=sorted({x['case_id'] for x in chosen});assert len(cases)==48
                cell={(x['case_id'],x['branch'],x['allocation'],x['condition']):x for x in chosen}
                values=[]
                for case in cases:
                    values.append(sum(sa*st*(cell[case,b,a,t]['LLM']-cell[case,b,a,t]['frequency']) for b in ['control','trap'] for a,sa in [('H',-1),('M',1)] for t,st in [('true',1),('shuffled',-1)])/2)
                assert abs(np.mean(values)-r['J']['estimate'])<1e-12,(scenario,view)
                count+=1
    print('PASS:',count,'development J estimates independently reconstructed from scored rows.')
if __name__=='__main__':main()
