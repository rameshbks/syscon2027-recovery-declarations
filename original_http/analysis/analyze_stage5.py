"""Reproduce Stage 5 tables, fixed-scenario paired bootstrap and figures.

Run: python analyze_stage5.py --archive PATH --out NEW_DIRECTORY
"""
import argparse
import hashlib
import json
import platform
import sys
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from scipy.stats import beta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ORDER=['connectivity','policy','gate_v2','gate_v3','auth_only','stability_only']
B=10000
BOOT_SEED=20261105


def cp(k,n):
    return (0.0 if k==0 else float(beta.ppf(.025,k,n-k+1)),
            1.0 if k==n else float(beta.ppf(.975,k+1,n-k)))


def block_bootstrap(pair, field, estimator='mean'):
    # Each row is a seed block, each column a fixed scenario. Preserve all pairs
    # and repeated-mechanic correlations within the same seed identifier.
    matrix=pair[field].unstack('scenario').sort_index().to_numpy(dtype=float)
    assert np.isfinite(matrix).all()
    rng=np.random.default_rng(BOOT_SEED)
    indices=rng.integers(0,len(matrix),size=(B,len(matrix)))
    samples=matrix[indices].reshape(B,-1)
    stat=np.mean(samples,axis=1) if estimator=='mean' else np.median(samples,axis=1)
    estimate=float(np.mean(matrix) if estimator=='mean' else np.median(matrix))
    lo,hi=np.quantile(stat,[.025,.975])
    return estimate,float(lo),float(hi)


def analyze(archive,out):
    out.mkdir(parents=True,exist_ok=False)
    source_hash=hashlib.sha256(archive.read_bytes()).hexdigest()
    expected='68c5d1b880c5c1e78693262e6cef03d8e2a7ef6d71d5d25cec6f982621d31b41'
    if source_hash!=expected:
        raise ValueError('Archive does not match the recorded Windows full campaign')
    data_dir=out/'input'
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError('ZIP CRC failed')
        for member in z.infolist():
            name=Path(member.filename.replace('\\','/'))
            if name.is_absolute() or '..' in name.parts:
                raise ValueError('unsafe archive path')
            path=data_dir/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(z.read(member))
    root=data_dir/'stage4_results_full_windows_v1'
    sys.path.insert(0,str(Path(__file__).parent/'reference_source'))
    import audit_stage4
    rows,verdicts,trials=audit_stage4.audit(root)
    # Keep raw evidence and disposable audit keys only in this local input tree.
    # Deliverable ZIP is built separately and excludes it.
    audit_text=audit_stage4.report(root).replace('Stage 4 Pilot Audit','Stage 4 Campaign Audit')
    (out/'VERIFIED_CAMPAIGN_AUDIT.md').write_text(audit_text)
    d=pd.DataFrame(rows)
    bools=['declaration_missing','unsafe_declaration','invalid_evidence_declaration',
           'post_declaration_failure','followup_censored','primary_comparator']
    for name in bools:
        d[name]=d[name].map({'True':True,'False':False,'':pd.NA}).astype('boolean')
    for name in ['seed','declaration_s','reference_recovery_s','declaration_step']:
        d[name]=pd.to_numeric(d[name],errors='coerce')
    m=json.loads((root/'manifest.json').read_text())
    scenarios=m['scenarios']
    assert len(d)==2520 and not d.duplicated(['scenario','seed','strategy']).any()
    assert set(d.seed)==set(range(30))
    summary=[]
    for method in ORDER:
        r=d[d.strategy==method]
        declared=r[~r.declaration_missing]
        eligible=r[r.post_declaration_failure.notna()]
        summary.append(dict(strategy=method,evaluations=len(r),declared=len(declared),
            unsafe=int(r.unsafe_declaration.sum()),invalid_evidence=int(r.invalid_evidence_declaration.sum()),
            no_declaration=int(r.declaration_missing.sum()),followup_eligible=len(eligible),
            followup_censored=int(r.followup_censored.sum()),future_failure=int(r.post_declaration_failure.sum()),
            unsafe_percent_all_traces=100*float(r.unsafe_declaration.sum())/len(r),
            unsafe_percent_declared=100*float(r.unsafe_declaration.sum())/len(declared),
            future_failure_percent_eligible=100*float(r.post_declaration_failure.sum())/len(eligible),
            median_declaration_ms=1000*declared.declaration_s.median(),
            mean_declaration_ms=1000*declared.declaration_s.mean(),
            safe_now_then_future_failure=int(((r.unsafe_declaration==False)&(r.post_declaration_failure==True)).sum())))
    summary=pd.DataFrame(summary)
    summary.to_csv(out/'strategy_summary.csv',index=False)
    scenario_rows=[]
    for (s,method),r in d.groupby(['scenario','strategy'],sort=False):
        n=int(r.unsafe_declaration.notna().sum())
        k=int(r.unsafe_declaration.sum())
        lo,hi=cp(k,n) if n else (np.nan,np.nan)
        scenario_rows.append(dict(scenario=s,strategy=method,n_traces=len(r),declared=n,unsafe=k,
            no_declaration=int(r.declaration_missing.sum()),invalid_evidence=int(r.invalid_evidence_declaration.sum()),
            future_failure=int(r.post_declaration_failure.sum()),followup_eligible=int(r.post_declaration_failure.notna().sum()),
            unsafe_cp95_lower=lo,unsafe_cp95_upper=hi))
    per=pd.DataFrame(scenario_rows)
    per.to_csv(out/'scenario_outcomes.csv',index=False)
    a=d[d.strategy=='gate_v2'].set_index(['scenario','seed']).sort_index()
    b=d[d.strategy=='gate_v3'].set_index(['scenario','seed']).sort_index()
    pair=pd.DataFrame(index=a.index)
    for field in ['unsafe_declaration','invalid_evidence_declaration','post_declaration_failure']:
        pair[field+'_a']=a[field];pair[field+'_b']=b[field]
        pair[field+'_reduction']=a[field].astype('Float64')-b[field].astype('Float64')
    pair['extra_wait_ms']=(b.declaration_s-a.declaration_s)*1000
    pair.to_csv(out/'paired_gate_v2_gate_v3.csv')
    pair[(pair.post_declaration_failure_a==False)&
         (pair.post_declaration_failure_b==True)].to_csv(out/'worsened_followup_cases.csv')
    intervals=[]
    for field in ['unsafe_declaration','invalid_evidence_declaration','post_declaration_failure']:
        complete=pair.dropna(subset=[field+'_reduction'])
        est,lo,hi=block_bootstrap(complete,field+'_reduction')
        aa,bb=complete[field+'_a'],complete[field+'_b']
        intervals.append(dict(metric=field,pairs=len(complete),estimate=100*est,lower95=100*lo,upper95=100*hi,
                              unit='percentage points reduction among jointly observed outcomes',
                              improved=int(((aa==True)&(bb==False)).sum()),
                              worsened=int(((aa==False)&(bb==True)).sum()),
                              degenerate_interval=bool(np.isclose(lo,hi))))
    for estimator in ['mean','median']:
        est,lo,hi=block_bootstrap(pair.dropna(subset=['extra_wait_ms']),'extra_wait_ms',estimator)
        intervals.append(dict(metric='extra_wait_'+estimator,pairs=390,estimate=est,lower95=lo,upper95=hi,unit='ms',
                              improved=np.nan,worsened=np.nan,degenerate_interval=bool(np.isclose(lo,hi))))
    ci=pd.DataFrame(intervals)
    ci.to_csv(out/'paired_intervals.csv',index=False)
    sensitivity=[]
    for label,excluded in [('all_labels',[]),('remove_explicit_duplicates',['stale_signed','missing_signed'])]:
        for method in ['gate_v2','gate_v3']:
            r=d[(d.strategy==method)&(~d.scenario.isin(excluded))]
            sensitivity.append(dict(mix=label,strategy=method,n=len(r),unsafe=int(r.unsafe_declaration.sum()),
                                    missing=int(r.declaration_missing.sum()),unsafe_fraction_all=float(r.unsafe_declaration.sum())/len(r)))
    pd.DataFrame(sensitivity).to_csv(out/'scenario_weight_sensitivity.csv',index=False)
    latency=[]
    for s in scenarios:
        r=pair.xs(s,level='scenario').extra_wait_ms.dropna()
        if len(r):
            latency.append(dict(scenario=s,n_pairs=len(r),median_ms=r.median(),q25_ms=r.quantile(.25),
                                q75_ms=r.quantile(.75),mean_ms=r.mean(),min_ms=r.min(),max_ms=r.max()))
    latency=pd.DataFrame(latency)
    latency.to_csv(out/'latency_by_scenario.csv',index=False)
    # IEEE-compatible vector outputs and 300 dpi PNG previews.
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'pdf.fonttype':42})
    fig,axes=plt.subplots(1,2,figsize=(7.3,6.4),sharey=True,layout='constrained')
    methods=['gate_v2','gate_v3','auth_only','stability_only']
    labels=['Gate v2','Gate v3','Auth only','Stability only']
    for ax,field,title in zip(axes,['unsafe','future_failure'],['Unsafe declaration','Failure after declaration']):
        mat=per.pivot(index='scenario',columns='strategy',values=field).reindex(scenarios)[methods].to_numpy(float)
        for i,s in enumerate(scenarios):
            if s=='persistent_outage':mat[i,:]=np.nan
        cmap=plt.get_cmap('YlOrRd').copy();cmap.set_bad('#dddddd')
        ax.imshow(np.ma.masked_invalid(mat),vmin=0,vmax=30,cmap=cmap,aspect='auto')
        for i in range(len(scenarios)):
            for j in range(4):
                value=mat[i,j]
                ax.text(j,i,'—' if np.isnan(value) else str(int(value)),ha='center',va='center',
                        color='white' if value>22 else 'black',fontsize=8)
        ax.set_xticks(range(4),labels,rotation=35,ha='right')
        ax.set_title(title)
    axes[0].set_yticks(range(len(scenarios)),[s.replace('_',' ') for s in scenarios])
    fig.supxlabel('Counts out of 30 trials per scenario; gray = no declaration',fontsize=9)
    fig.savefig(out/'figure1_scenario_outcomes.pdf');fig.savefig(out/'figure1_scenario_outcomes.png',dpi=300)
    plt.close(fig)
    fig,ax=plt.subplots(figsize=(7.3,4.8),layout='constrained')
    y=np.arange(len(latency))
    ax.errorbar(latency.median_ms,y,xerr=[latency.median_ms-latency.q25_ms,latency.q75_ms-latency.median_ms],
                fmt='o',color='#24557a',capsize=3)
    ax.set_yticks(y,latency.scenario.str.replace('_',' '));ax.invert_yaxis()
    ax.set_xlabel('Additional declaration wait for Gate v3 versus Gate v2 (ms)')
    ax.set_title('Matched trace medians and interquartile ranges')
    ax.grid(axis='x',alpha=.25)
    fig.savefig(out/'figure2_paired_wait.pdf');fig.savefig(out/'figure2_paired_wait.png',dpi=300);plt.close(fig)
    tex=['% Counts over 420 traces; 390 declarations and complete follow-up per method.',
         r'\begin{table*}[t]',r'\centering',r'\caption{Observed outcomes in the fixed scenario mix.}',
         r'\label{tab:stage4}',r'\begin{tabular}{lrrrr}',r'\hline',
         r'Method & Unsafe & Invalid & Missing & Later failure \\',r'\hline']
    for row in summary.itertuples():
        tex.append(row.strategy.replace('_',r'\_')+f' & {row.unsafe} & {row.invalid_evidence} & {row.no_declaration} & {row.future_failure} '+r'\\')
    tex += [r'\hline',r'\end{tabular}',r'\end{table*}']
    (out/'ieee_results_table.tex').write_text('\n'.join(tex)+'\n')
    results=dict(archive_sha256=source_hash,trials=trials,rows=len(d),bootstrap_replicates=B,bootstrap_seed=BOOT_SEED,
                 conditional_mix=scenarios,summary=summary.to_dict('records'),
                 intervals=ci.astype(object).where(pd.notna(ci),None).to_dict('records'),
                 analysis_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                 versions=dict(python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,
                               scipy=scipy.__version__,matplotlib=matplotlib.__version__))
    (out/'analysis_manifest.json').write_text(json.dumps(results,indent=2,allow_nan=False)+'\n')
    print(summary.to_string(index=False));print(ci.to_string(index=False))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();analyze(a.archive,a.out)
