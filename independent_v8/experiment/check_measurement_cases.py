"""Exploratory audit of physical-only declaration failures; no outcome changes."""
from pathlib import Path
import json,pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parent
d=pd.read_csv(ROOT/'analysis_records.csv.gz');a=dict(np.load(ROOT/'traces.npz'))
sel=d[d.auth & (d.unsafe==True) & d.scenario.isin(['modification','replay'])]
out=[]
for row in sel.itertuples():
 if row.window not in [3,8]:continue
 i,j,w=row.trace_id,row.declaration_step,row.window
 assert np.all(a['auth_ok'][i,j-w+1:j+1])
 assert not np.any(a['manipulated'][i,j-w+1:j+1])
 rec=dict(trace_id=i,scenario=row.scenario,window=w,sigma=row.sigma,declaration_step=j,
  actual_trailing_levels=a['level'][i,j-2:j+1].tolist(),
  captured_trailing_levels=a['capture_level'][i,j-2:j+1].tolist(),
  received_trailing_levels=a['noisy_level'][i,j-2:j+1].tolist())
 if w==8:
  assert row.sigma==0
  assert np.all(a['capture_level'][i,j-w+1:j+1]>=40)
  assert a['level'][i,j]<40
  rec['mechanism']='fresh-but-lagged genuine measurement near lower-bound crossing'
 else:
  assert row.sigma==2
  clean=d[d.auth&(d.window==3)&(d.path_id==row.path_id)&(d.transport==row.transport)&(d.buffer_s==row.buffer_s)&(d.sigma==0)].iloc[0]
  assert not clean['missing'] and not clean['unsafe']
  assert np.any((a['capture_level'][i,j-2:j+1]<40)|(a['capture_level'][i,j-2:j+1]>60))
  rec.update(mechanism='noise permits in-range readings while actual level violates bound',clean_trace_id=int(clean.trace_id),clean_premature=False)
 out.append(rec)
assert sum(r['window']==3 for r in out)==20
assert sum(r['window']==8 for r in out)==2
(ROOT/'measurement_case_audit.json').write_text(json.dumps(out,indent=2))
print('PASS: 20 noisy G3+A cases and 2 noise-free, fresh-but-lagged G8+A cases.')
