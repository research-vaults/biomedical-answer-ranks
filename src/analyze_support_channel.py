#!/usr/bin/env python3
"""Direct channel contrasts and main-paper-oriented display of the executed panels."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];A=ROOT/'data/selector_extension';B=ROOT/'data/joint_reference'
def read(p):return [json.loads(l) for l in p.read_text().splitlines()]
count=read(A/'SCORED_ROWS.jsonl');joint=read(B/'SCORED_ROWS.jsonl')
keys=lambda r:(r['scenario'],r['case_id'],r['branch'],r['allocation'],r['condition'])
count={keys(r):r for r in count if r['view']=='gemini_counts'};joint={keys(r):r for r in joint}
assert count.keys()==joint.keys()
scenarios=sorted({k[0] for k in joint});cases=sorted({k[1] for k in joint});rng=np.random.default_rng(202609071300);draw=rng.integers(0,len(cases),(50000,len(cases)))
result={}
for sc in scenarios:
    arr=[]
    for case in cases:
        bs=[]
        for branch in ['control','trap']:
            delta={(a,c):joint[sc,case,branch,a,c]['LLM']-count[sc,case,branch,a,c]['LLM'] for a in ['H','M'] for c in ['true','shuffled']}
            bs.append([delta['H','true'],delta['M','true'],delta['M','true']-delta['H','true'],delta['M','true']-delta['M','shuffled']-delta['H','true']+delta['H','shuffled']])
        arr.append(np.mean(bs,axis=0))
    arr=np.array(arr);boot=arr[draw].mean(1)
    result[sc]={k:{'estimate':float(arr[:,i].mean()),'ci95':np.quantile(boot[:,i],[.025,.975]).tolist()} for i,k in enumerate(['H_true_joint_minus_counts','M_true_joint_minus_counts','R_true_allocation_channel_interaction','D_joint_minus_D_counts'])}
(B/'CHANNEL_CONTRASTS.json').write_text(json.dumps(result,indent=2)+'\n')
focal=['corrected_v4_strict','refinement_temporal_etiologic_severity_or_site'];summary=json.loads((A/'RESULTS.json').read_text());ref=json.loads((B/'RESULTS.json').read_text())
fig,axs=plt.subplots(1,2,figsize=(11,4.3),layout='constrained')
views=['gemma12_joint','llama8_joint','gemini_counts','gemini_derangement'];labels=['Gemma 12B · joint','Llama 8B · joint','Gemini · counts only','Gemini · alternative shuffle']
for j,(sc,color,label) in enumerate(zip(focal,['#285f9e','#c05722'],['Strict','With refinements'])):
    for i,v in enumerate(views):
        r=summary[sc][v]['J'];y=i+(j-.5)*.19;x=r['estimate']*100;lo,hi=np.array(r['ci95'])*100
        axs[0].errorbar(x,y,xerr=[[x-lo],[hi-x]],fmt='o',color=color,capsize=3,label=label if i==0 else None)
    r=result[sc]['R_true_allocation_channel_interaction'];x=r['estimate']*100;lo,hi=np.array(r['ci95'])*100
    axs[1].errorbar(x,j,xerr=[[x-lo],[hi-x]],fmt='o',color=color,capsize=4)
axs[0].set_yticks(range(4),labels);axs[0].invert_yaxis();axs[0].set_xlabel('J: LLM − frequency interaction (percentage points)');axs[0].set_title('Selector and interface boundary');fig.legend(*axs[0].get_legend_handles_labels(),frameon=False,loc='outside lower center',ncol=2,fontsize=9)
axs[1].set_yticks([0,1],['Strict','With refinements']);axs[1].set_xlabel('TRUE-choice allocation × channel interaction (pp)');axs[1].set_title('Direct rank-information contrast')
for ax in axs:ax.axvline(0,color='.5',ls='--',lw=.8);ax.grid(axis='x',alpha=.15);ax.spines[['top','right']].set_visible(False)
fig.suptitle('New selector outputs on 48 reused case pairs · paired 95% intervals',fontsize=11)
fig.savefig(B/'SUPPORT_CHANNEL_BOUNDARY.png',dpi=180)
print(json.dumps({k:result[k] for k in focal},indent=2))
