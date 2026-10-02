#!/usr/bin/env python3
"""Post-result descriptive transition accounting and honest source comparison."""
import json,collections
import numpy as np
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams.update({'pdf.fonttype':42,'ps.fonttype':42,'font.size':9})
import matplotlib.pyplot as plt
from transport_io import OUT,ROOT,write

def main():
    med=json.loads((OUT/'RESULTS.json').read_text());vec=json.loads((OUT/'CASE_VECTORS.json').read_text());old=json.loads((ROOT/'data/fresh_confirmation/RESULTS.json').read_text());ov=json.loads((ROOT/'data/fresh_confirmation/PAIR_VECTORS.json').read_text());cfg=json.loads((OUT/'CONFIG.json').read_text());post={}
    rng=np.random.default_rng(202609071720);tasks=[c['medical_task'] for c in cfg['cases']];groups=[np.where(np.array(tasks)==task)[0] for task in cfg['strata']];bnew=np.concatenate([rng.choice(g,(50000,len(g)),replace=True) for g in groups],axis=1);bold=rng.integers(0,96,(50000,96))
    for view,oldview in [('gemini','gemini_joint'),('llama','llama8_joint')]:
        a=vec['by_selector'][view]['absolute'];trans=[]
        for H,M in [(0,0),(0,1),(1,0),(1,1)]:
            indices=[i for i in range(128) if a['H|true|oracle'][i]==H and a['M|true|oracle'][i]==M]
            trans.append({'H_available':H,'M_available':M,'cases':len(indices),'H_correct':sum(a['H|true|llm'][i] for i in indices),'M_correct':sum(a['M|true|llm'][i] for i in indices)})
        newj=np.array(vec['by_selector'][view]['J']);oldj=np.array(ov['J']['refinement|'+oldview]);d=newj[bnew].mean(1)-oldj[bold].mean(1)
        post[view]={'transitions':trans,'transport_minus_fresh_J':{'estimate':float(newj.mean()-oldj.mean()),'ci95':np.quantile(d,[.025,.975]).tolist(),'status':'POSTHOC_INDEPENDENT_SOURCE_COMPARISON_NOT_MECHANISM','scope':'Different source, answer regime and estimand composition; new128 tasks-balanced items minus old96 paired-case means'}}
    write(OUT/'POSTHOC_BOUNDARY.json',post)
    fig,axs=plt.subplots(1,2,figsize=(6.8,2.4),gridspec_kw={'width_ratios':[1.1,1]})
    for i,(view,oldview,name) in enumerate([('gemini','gemini_joint','Gemini'),('llama','llama8_joint','Llama8B')]):
        for offset,(label,r,color) in enumerate([('MedEinst96',old['refinement'][oldview]['J'],'#145c9e'),('MedXpertQA128',med[view]['J'],'#bd6235')]):
            e=r['estimate']*100;lo,hi=np.array(r['ci97_5'])*100;axs[0].errorbar(e,i+(offset-.5)*.23,xerr=[[e-lo],[hi-e]],fmt='o',capsize=3,color=color,label=label if i==0 else None)
    axs[0].set_yticks([0,1],['Gemini','Llama8B']);axs[0].invert_yaxis();axs[0].set_xlabel('J (percentage points)');axs[0].set_title('Support-rule contrast');axs[0].legend(fontsize=7,loc='center left')
    for i,(label,r) in enumerate([('Key available',med['gemini']['availability_M_minus_H']),('Gemini final',med['gemini']['final_M_minus_H_true']),('Llama final',med['llama']['final_M_minus_H_true'])]):
        e=r['estimate']*100;lo,hi=np.array(r['ci95'])*100;axs[1].errorbar(e,i,xerr=[[e-lo],[hi-e]],fmt='o',capsize=3,color='#bd6235')
    axs[1].set_yticks([0,1,2],['Key available','Gemini final','Llama final']);axs[1].invert_yaxis();axs[1].set_xlabel('Mixed minus H (pp)');axs[1].set_title('Native-key consequences')
    for ax in axs:ax.axvline(0,color='gray',lw=.7);ax.spines[['top','right']].set_visible(False)
    fig.tight_layout(w_pad=1.2);fig.savefig(OUT/'TRANSPORT_BOUNDARY.png',dpi=160);fig.savefig(ROOT/'manuscript/figures/FRESH_CONFIRMATION.pdf',bbox_inches='tight');plt.close(fig)
    print(json.dumps(post,indent=2))

if __name__=='__main__':main()
