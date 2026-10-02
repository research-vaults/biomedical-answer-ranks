"""Regenerate the two development displays from the recorded effect matrices."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
R=Path(__file__).resolve().parents[1];D=R/'manuscript/figures'
results={}
for f in ['selector_extension','joint_reference']:
    results.update({(s,v):r for s,vs in json.loads((R/'data'/f/'RESULTS.json').read_text()).items() for v,r in vs.items()})
fig,ax=plt.subplots(figsize=(6.8,2.25))
for i,(s,color,label) in enumerate([('corrected_v4_strict','#145c9e','Strict'),('refinement_temporal_etiologic_severity_or_site','#d17b20','All refinements')]):
    views=['gemini_joint_reference','gemma12_joint','llama8_joint'];y=np.arange(3)+(i-.5)*.18
    vals=np.array([results[s,v]['J']['estimate']*100 for v in views]);ci=np.array([results[s,v]['J']['ci95'] for v in views])*100
    ax.errorbar(vals,y,xerr=[vals-ci[:,0],ci[:,1]-vals],fmt='o',capsize=3,label=label,color=color)
ax.set_yticks(range(3),['Gemini Flash-Lite','Gemma3-12B','Llama3.1-8B']);ax.axvline(0,color='gray',lw=.8);ax.invert_yaxis();ax.set_xlabel('LLM-minus-frequency allocation interaction J (percentage points)');ax.legend(loc='center left',bbox_to_anchor=(0,.30),fontsize=8);ax.spines[['top','right']].set_visible(False);fig.tight_layout();fig.savefig(D/'THREE_SELECTOR_J.pdf',bbox_inches='tight');plt.close(fig)
E=json.loads((R/'data/scoring_sensitivity/C2_EFFECT_MATRIX.json').read_text())
names=['original_frozen_strict','corrected_v4_strict','refinement_temporal','refinement_temporal_etiologic_severity_or_site','corrected_v4_inclusive']
fig,ax=plt.subplots(figsize=(7.2,3.2),layout='constrained')
for field,offset,color,label in [('access_effect',-.13,'#187b80','Availability'),('final_effect',.13,'#ac4d28','Final choice')]:
    vals=np.array([E[n][field]['estimate'] for n in names]);bounds=np.array([E[n][field]['ci95'] for n in names]);ax.errorbar(vals,np.arange(len(names))+offset,xerr=[vals-bounds[:,0],bounds[:,1]-vals],fmt='o',capsize=3,color=color,label=label)
ax.axvline(0,color='#777777',lw=.8);ax.set_yticks(np.arange(5),['Original strict','Corrected strict','Temporal refinements','All refinements','Corrected inclusive']);ax.invert_yaxis();ax.set_xlabel('Mixed minus homogeneous (proportion of branches)');ax.legend(loc='lower left',bbox_to_anchor=(0,1.01),ncol=2,fontsize=9,frameon=False);ax.spines[['top','right']].set_visible(False);fig.savefig(D/'SCORING_SENSITIVITY.pdf');plt.close(fig)
