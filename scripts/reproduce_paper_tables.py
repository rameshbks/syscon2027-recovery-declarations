"""Export experiment-derived manuscript tables and analytical figure values."""
from pathlib import Path
import argparse,json,shutil
import pandas as pd,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
NAMES={'connectivity':'C','policy':'P','gate_v2':'G3','auth_only':'G3+A','stability_only':'G8','gate_v3':'G8+A'}
ORDER=list(NAMES)
def export(out):
 out.mkdir(parents=True,exist_ok=False)
 df=pd.read_csv(ROOT/'original_http/analysis/outputs/strategy_summary.csv').set_index('strategy').loc[ORDER]
 pd.DataFrame([{'Method':NAMES[k],'Premature / declared':f'{int(r.unsafe)}/{int(r.declared)}','Invalid / declared':f'{int(r.invalid_evidence)}/{int(r.declared)}','Missing / 420':int(r.no_declaration),'Later / eligible':f'{int(r.future_failure)}/{int(r.followup_eligible)}'} for k,r in df.iterrows()]).to_csv(out/'table_IV.csv',index=False)
 pd.DataFrame([{'Window':w,'Unauthenticated premature / later':f"{df.loc[u,'unsafe']} / {df.loc[u,'future_failure']}",'Authenticated premature / later':f"{df.loc[a,'unsafe']} / {df.loc[a,'future_failure']}"} for w,u,a in [(3,'gate_v2','auth_only'),(8,'stability_only','gate_v3')]]).to_csv(out/'table_V.csv',index=False)
 sweep=json.loads((ROOT/'original_http/window_sensitivity.json').read_text())
 pd.DataFrame([{'W':r['window'],'Premature / declared':f"{r['unsafe_declaration']}/{r['declared']}",'Later / eligible':f"{r['post_declaration_failure']}/{r['declared']}",'Intermittent later / 30':r['intermittent_future']} for r in sweep]).to_csv(out/'table_VI.csv',index=False)
 h={r['strategy']:r for r in json.loads((ROOT/'validation/analysis.json').read_text())['summary']}
 pd.DataFrame([{'Method':NAMES[k],'Premature / declared':f"{h[k]['unsafe_declaration']}/{h[k]['declared']}",'Later / eligible':f"{h[k]['post_declaration_failure']}/{h[k]['future_eligible']}",'Missing / 240':h[k]['declaration_missing'],'Censored':h[k]['followup_censored']} for k in ORDER]).to_csv(out/'table_VII.csv',index=False)
 nl=json.loads((ROOT/'independent_v8/experiment/analysis.json').read_text())
 methods={(r['window'],r['auth']):r for r in nl['methods']}
 pd.DataFrame([{'Gate':f'G{w}'+('+A' if au else ''),'Premature / declared':f"{methods[w,au]['unsafe']}/{methods[w,au]['declared']}",'Missing / 5760':methods[w,au]['missing'],'Later / eligible':f"{methods[w,au]['later']}/{methods[w,au]['future_eligible']}",'Median wait (s)':methods[w,au]['median_wait_s']} for w in [3,5,8,12] for au in [False,True]]).to_csv(out/'table_VIII.csv',index=False)
 # Small figures reproduce manuscript data, not exact document typography.
 plt.rcParams.update({'font.family':'DejaVu Serif','font.size':8})
 s=pd.read_csv(ROOT/'original_http/analysis/outputs/scenario_outcomes.csv').set_index(['scenario','strategy'])
 scenarios=['intermittent','misleading_evidence','replay_evidence','source_compromise']
 gates=['gate_v2','auth_only','stability_only','gate_v3']
 fig,axs=plt.subplots(1,2,figsize=(4.2,2.2),layout='constrained')
 values={}
 for ax,key,title in zip(axs,['unsafe','future_failure'],['Premature','Later failure']):
  z=np.array([[s.loc[(sc,g),key] for g in gates]for sc in scenarios])
  values[key]=z.tolist();ax.imshow(z,cmap='Blues',vmin=0,vmax=30,aspect='auto')
  ax.set_title(title);ax.set_xticks(range(4),[NAMES[g]for g in gates],fontsize=7)
  for i in range(4):
   for j in range(4):ax.text(j,i,str(z[i,j]),ha='center',va='center',color='white'if z[i,j]>16 else 'black')
 axs[0].set_yticks(range(4),['Intermittent','Modification','Replay','Source compromise']);axs[1].set_yticks([])
 fig.savefig(out/'figure_1.pdf');fig.savefig(out/'figure_1.png',dpi=300);plt.close(fig)
 (out/'figure_1_values.json').write_text(json.dumps(values,indent=2)+'\n')
 l=pd.read_csv(ROOT/'original_http/analysis/outputs/latency_by_scenario.csv').set_index('scenario').loc[['normal',*scenarios[0:3],'source_compromise']]
 fig,ax=plt.subplots(figsize=(4.2,2),layout='constrained')
 for i,r in enumerate(l.itertuples()):
  ax.plot([r.q25_ms,r.q75_ms],[i,i],lw=3,color='#82a6cf');ax.scatter(r.median_ms,i,color='#205c9a',s=20,zorder=3)
  ax.annotate(str(round(r.median_ms)),(r.median_ms,i),xytext=(6,0),textcoords='offset points',va='center',fontsize=7)
 ax.set_yticks(range(5),['Normal','Intermittent','Modification','Replay','Source compromise']);ax.invert_yaxis();ax.set_xlim(70,450);ax.set_xlabel('Additional declaration wait (ms)');ax.grid(axis='x',alpha=.2)
 fig.savefig(out/'figure_2.pdf');fig.savefig(out/'figure_2.png',dpi=300);plt.close(fig)
 l.to_csv(out/'figure_2_values.csv')
 c=pd.read_csv(ROOT/'independent_v8/experiment/robustness_cells.csv')
 fig,axs=plt.subplots(1,2,figsize=(4.2,2.1),layout='constrained')
 for ax,col,title in zip(axs,['unsafe','missing'],['Premature (%)','Missing (%)']):
  z=100*c[col].to_numpy().reshape(3,3)/640
  ax.imshow(z,cmap='Blues',vmin=0,vmax=100);ax.set_title(title)
  ax.set_xticks(range(3),['0','40','100']);ax.set_xlabel('Buffer age (ms)')
  for i in range(3):
   for j in range(3):ax.text(j,i,f'{z[i,j]:.1f}',ha='center',va='center',color='white'if z[i,j]>55 else'black')
 axs[0].set_yticks(range(3),['5–15','45–65','85–115']);axs[0].set_ylabel('Transport (ms)');axs[1].set_yticks([])
 fig.savefig(out/'figure_3.pdf');fig.savefig(out/'figure_3.png',dpi=300);plt.close(fig)
 c.to_csv(out/'figure_3_values.csv',index=False)
 print('Exported numerical Tables IV–VIII and all three analytical figures.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);export(p.parse_args().out)
