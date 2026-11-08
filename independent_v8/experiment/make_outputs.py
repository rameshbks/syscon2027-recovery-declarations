from pathlib import Path
import json,csv
import pandas as pd,numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parent
a=json.loads((ROOT/'analysis.json').read_text())
df=pd.read_csv(ROOT/'analysis_records.csv.gz')
g=df[df.auth & (df.window==8)]
trans=['low','age_boundary','deadline_boundary'];buffers=[0.,.04,.1]
miss=np.zeros((3,3));unsafe=np.zeros((3,3));counts=[]
for i,t in enumerate(trans):
 for j,b in enumerate(buffers):
  rows=g[(g.transport==t)&(g.buffer_s==b)]
  assert len(rows)==640
  miss[i,j]=100*rows.missing.mean();unsafe[i,j]=100*rows.unsafe.sum()/len(rows)
  counts.append(dict(transport=t,buffer_s=b,n=len(rows),unsafe=int(rows.unsafe.sum()),missing=int(rows.missing.sum()),declared=int((~rows.missing).sum())))
with (ROOT/'robustness_cells.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=counts[0]);w.writeheader();w.writerows(counts)
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':7.5})
fig,axes=plt.subplots(1,2,figsize=(3.5,1.85),constrained_layout=True)
for ax,z,title in zip(axes,[unsafe,miss],['Premature (%)','Missing (%)']):
 ax.imshow(z,cmap='Blues',vmin=0,vmax=100)
 for i in range(3):
  for j in range(3):ax.text(j,i,f'{z[i,j]:.1f}',ha='center',va='center',color='white' if z[i,j]>55 else 'black',fontsize=8.5)
 ax.set_xticks(range(3),['0','40','100']);ax.set_xlabel('Buffer age (ms)')
 ax.set_yticks(range(3),['5–15','45–65','85–115']);ax.set_title(title,fontsize=8)
axes[0].set_ylabel('Transport (ms)')
axes[1].set_yticklabels([])
fig.savefig(ROOT/'figure3_robustness.png',dpi=300);fig.savefig(ROOT/'figure3_robustness.pdf');plt.close(fig)
p=a['paired'];w=a['paired_wait']
lines=['# Independent process validation and robustness study','',
'## Frozen plan','',
'The protocol and implementation hashes were saved before collecting campaign outcomes. The primary comparison is G3 versus G8+A. Windows 3, 5, 8 and 12, with and without authentication, were fixed in advance; no window was selected as an optimum after seeing results.','',
'The standalone model has two gravity-drained tanks in cascade with nonlinear square-root outflows, PI pump control, saturation, and remote sensor noise. It does not import the original scalar plant or its generator. The existing HMAC verifier is intentionally reused as a fixed control. The new vectorized declaration engine is cross-checked against the unchanged original scalar predicate for every assessment.','',
'The 5,760 observation traces arise from 320 process trajectories crossed with 18 transport/buffer/noise settings. They are not 5,760 independent physical runs. The entire fixed grid is carried together within each of 20 seed blocks.','',
'## Completed campaign','',
f"- Full audit: {a['audit']['samples']:,} stored samples; {a['audit']['assessments']:,} assessments; all packet digests, verification verdicts, declarations and outcomes matched.",
'- Physics checks: exact equilibrium, closed mass conservation, analytic tank-1 drainage, controller saturation / anti-windup, step refinement, and response to a pump disturbance. All six pass.',
'- Supplemental numerical audit: a separately coded 1 ms Euler solver checks all 320 trajectories without importing the RK4 plant; maximum level difference is 0.004514 units (fixed tolerance 0.1). All pass.',
'- Measurement-case audit: all 20 G3+A physical-only errors occur with noise sigma 2; the two G8+A physical-only errors occur at zero noise and arise from capture lag after manipulation ends.',
'- Telemetry interval: 200 ms; RK4 integration: 10 ms; PI update: 20 ms; horizon: 60 virtual seconds.',
'- Freshness remains 60 ms and service deadline 100 ms. The forward-five outcome now spans one virtual second, so elapsed times and failure rates must not be pooled with the original 20 ms HTTP campaigns.','',
'## Method counts','',
'| Method | Premature / declared | Missing / 5760 | Later / eligible | Median wait (s) |','|---|---:|---:|---:|---:|']
for r in a['methods']:
 name=f"G{r['window']}"+('+A' if r['auth'] else '')
 lines.append(f"| {name} | {r['unsafe']}/{r['declared']} | {r['missing']} | {r['later']}/{r['future_eligible']} | {r['median_wait_s']:.2f} |")
lines+=['','## Paired primary comparison','',
f"Mutual declarations: {p['unsafe']['n']}; G3-only declarations: {w['left_only']}; G8+A-only: {w['right_only']}; both missing: {w['both_missing']}.",
f"Premature outcomes: {p['unsafe']['improve']} improvements and {p['unsafe']['worsen']} worsenings; difference {p['unsafe']['difference_pp']:.2f} percentage points; conditional 95% seed-block interval [{p['unsafe']['conditional95'][0]:.2f}, {p['unsafe']['conditional95'][1]:.2f}].",
f"Later outcomes: {p['later']['improve']} improvements and {p['later']['worsen']} worsenings; difference {p['later']['difference_pp']:.2f} percentage points; conditional interval [{p['later']['conditional95'][0]:.2f}, {p['later']['conditional95'][1]:.2f}].",
f"Median paired added wait: {w['median_s']:.2f} virtual seconds. The intervals resample 20 seed blocks, 10,000 times, seed 20261107. They do not quantify industrial incidence, process-parameter uncertainty, or hardware uncertainty.",'',
'## Findings and limits','',
'MAC rejection of modified and replayed packets transfers, but noise and lag in genuine measurements break the stronger statement that authentication removes every premature declaration within those scenario labels. At W=8, two such declarations remain (one modification, one replay), both at zero noise. Signed captured levels remain above 40 while actual levels cross 0.0079 units below 40. These small-margin, fresh-but-lagged boundary crossings occur after manipulation ends, not from accepting a tampered packet. At W=3, 20 physical-only failures occur at noise sigma 2; matched noise-free traces are not premature. This outcome decomposition is exploratory and does not change the frozen primary outcome.',
'',
'Under source compromise G8+A is premature in 196/328 declarations; authentication does not establish measurement truth. Larger windows lower premature counts while increasing missing declarations from 3,888 to 4,104 for authenticated W=3 to W=12. The age and transport profiles include settings that cannot satisfy the fixed freshness limit. Their missing declarations are expected fail-closed behavior, not evidence of successful recovery.',
'',
'The model is an author-implemented research simulation using illustrative SI parameters. It is not a Quanser/SWaT implementation, hardware experiment, independent instrumentation, or externally validated industrial safety model. The local PI loop uses ideal state feedback; Gaussian noise is applied only to remote telemetry. Latency and clocks are virtual. Shadow declarations do not prevent writes or restore control. No independent-evidence gate was added.','',
'## Reproduce','',
'From a fresh extracted package root, install the pinned experiment dependencies and run:',
'',
'    python independent_v8/experiment/test_plant.py',
'    python independent_v8/experiment/campaign.py',
'    python independent_v8/experiment/audit_analyze.py',
'    python independent_v8/experiment/check_trajectories.py',
'    python independent_v8/experiment/check_measurement_cases.py',
'    python independent_v8/experiment/make_outputs.py',
'',
'The runner overwrites outputs beside itself: use a fresh extraction and retain the delivered evidence. All lab keys are deterministic disposable test keys; packet digests and retained payload fields permit exact reconstruction. This provides computational reproducibility rather than cryptographic provenance. Protocol, source hashes, metadata, compressed raw arrays, outcomes, analysis records, uncertainty estimates, and plot/table regeneration code are included. The bundle is private until the authors choose to archive it publicly.']
(ROOT/'PLAN_AND_FINDINGS.md').write_text('\n'.join(lines)+'\n')
(ROOT/'requirements.txt').write_text('\n'.join([f'numpy=={np.__version__}',f'pandas=={pd.__version__}',f'matplotlib=={matplotlib.__version__}'])+'\n')
print('Outputs generated')
