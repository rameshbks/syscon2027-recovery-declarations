"""Supplemental numerical audit: independent Euler implementation, no plant imports."""
from pathlib import Path
import json,numpy as np
ROOT=Path(__file__).resolve().parent
m=json.loads((ROOT/'metadata.json').read_text());a=dict(np.load(ROOT/'traces.npz'))
unique={}
for r in m:unique.setdefault(r['path_id'],r)
spec=[unique[i] for i in range(320)]
A1,A2=.12,.1;k1,k2=.035,.025;kp,ki=.025,.006;dt=.001
h1=np.full(320,(k2/k1)**2*.5);h2=np.full(320,.5);integ=np.zeros(320);q=np.full(320,k2*np.sqrt(.5))
starts=np.array([r['onset_s'] for r in spec]);ends=np.array([r['end_s'] for r in spec])
attack=np.array([r['scenario'] in ['modification','replay','source_compromise'] for r in spec])
expected=np.array([a['level'][r['trace_id']] for r in spec]);maxerr=0.
for j in range(60000):
 t=j*dt
 if j%20==0:
  target=np.where((t>=starts-1e-8)&(t<ends-1e-8)&attack,.8,.5)
  err=target-h2
  raw=k2*np.sqrt(.5)+kp*err+ki*integ
  q=np.maximum(0,np.minimum(.04,raw))
  allow=((raw>=0)&(raw<=.04))|((raw>.04)&(err<0))|((raw<0)&(err>0))
  integ+=np.where(allow,.02*err,0.)
 flow12=k1*np.sqrt(np.maximum(h1,0));flowout=k2*np.sqrt(np.maximum(h2,0))
 next_h1=h1+dt*(q-flow12)/A1;next_h2=h2+dt*(flow12-flowout)/A2
 h1=np.maximum(0,next_h1);h2=np.maximum(0,next_h2)
 if (j+1)%200==0:
  col=(j+1)//200
  maxerr=max(maxerr,float(np.max(abs(100*h2-expected[:,col]))))
assert maxerr < .1,maxerr
out=dict(method='independently coded forward Euler at 1 ms versus campaign RK4 at 10 ms',trajectories=320,max_level_error=maxerr,tolerance_level_units=.1,status='PASS',scope='supplemental numerical audit, not physical calibration')
(ROOT/'trajectory_audit.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
