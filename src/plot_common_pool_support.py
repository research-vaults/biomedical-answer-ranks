import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
P=Path(__file__).resolve().parents[1];O=P/'data/common_pool';r=json.loads((O/'RESULTS.json').read_text())
fig,ax=plt.subplots(1,2,figsize=(6.8,2.3));labels=[]
for i,(ds,metric,view,name) in enumerate([('medeinst','refinement','gemini','MedEinst / Gemini'),('medeinst','refinement','llama','MedEinst / Llama'),('medx','native_key','gemini','MedXpertQA / Gemini'),('medx','native_key','llama','MedXpertQA / Llama')]):
 v=r[f'{ds}|{metric}|{view}'];labels.append(name)
 for a,shift,color in [('H',-.12,'#145c9e'),('M',.12,'#b55522')]:
  e=v['source_comparisons'][a]['forward_minus_hidden'];x=e['estimate']*100;lo,hi=[t*100 for t in e['ci95']];ax[0].errorbar(x,i+shift,xerr=[[x-lo],[hi-x]],fmt='o',markersize=3,capsize=2,color=color,label=a+' support' if i==0 else None)
 e=v['J_norm'];x=e['estimate']*100;lo,hi=[t*100 for t in e['ci98_75']];ax[1].errorbar(x,i,xerr=[[x-lo],[hi-x]],fmt='o',color='#553c78',capsize=3,markersize=4)
for a in ax:a.axvline(0,color='gray',lw=.7);a.spines[['top','right']].set_visible(False);a.set_ylim(3.5,-.5);a.tick_params(labelsize=7)
ax[0].set_yticks(range(4),labels);ax[1].set_yticks(range(4),[]);ax[0].legend(fontsize=7,loc='upper center',bbox_to_anchor=(.5,1.20),ncol=2,frameon=False);ax[0].set_xlabel('Forward minus hidden (pp); 95% CI',fontsize=8);ax[1].set_xlabel('$J_{norm}$ (pp); 98.75% CI',fontsize=8);fig.tight_layout(w_pad=1.2)
fig.savefig(O/'COMMON_POOL_SUPPORT.png',dpi=180);fig.savefig(P/'manuscript/figures/COMMON_POOL_SUPPORT.pdf');plt.close(fig)
