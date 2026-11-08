import json,sys,csv,hashlib,collections
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'stage4'))
from evidence import sign,Verifier
from stage4_lab import decide
a={k:v for k,v in np.load(ROOT/'traces.npz').items()};meta=json.loads((ROOT/'metadata.json').read_text());digests=json.loads((ROOT/'packet_digests.json').read_text())
df=pd.read_csv(ROOT/'outcomes.csv')
manifest=json.loads((ROOT/'manifest.json').read_text())
assert len(meta)==5760 and len(df)==46080
for name,sha in manifest['source_sha256'].items():
 assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
T=a['time_s'];audit_assessments=0
for i,m in enumerate(meta):
 session=m['session'];key=hashlib.sha256(('laboratory-only:'+session).encode()).digest()
 verifier=Verifier(key,session);cached=None;digest=hashlib.sha256();authobs=[];obs=[]
 for j,t in enumerate(T):
  p=dict(service_ok=bool(a['service'][i,j]),monitor_present=True,probe_blocked=bool(a['policy'][i,j]),observed_level=float(a['noisy_level'][i,j]),age_s=float(a['age'][i,j]))
  packet=sign(key,session,j,float(t-a['age'][i,j]),p)
  manipulated=bool(a['manipulated'][i,j])
  if manipulated:
   fake=dict(service_ok=True,monitor_present=True,probe_blocked=True,observed_level=50.,age_s=0.)
   if m['scenario']=='modification':packet['body']['payload']=fake
   elif m['scenario']=='source_compromise':packet=sign(key,session,j,float(t-a['latency'][i,j]),fake)
   else:packet=cached
  if not a['post'][i,j]:cached=packet
  digest.update(json.dumps(packet,sort_keys=True,separators=(',',':')).encode())
  ok,reason,accepted=verifier.verify(packet,float(t))
  assert ok==a['auth_ok'][i,j]
  honest=dict(p,index=j,post_injection=bool(a['post'][i,j]))
  if manipulated:honest.update(fake)
  obs.append(honest)
  if accepted is None:accepted=dict(service_ok=False,monitor_present=False,probe_blocked=None,age_s=None,observed_level=None)
  authobs.append(dict(accepted,index=j,post_injection=bool(a['post'][i,j])))
 assert digest.hexdigest()==digests[i],('packet reconstruction',i)
 # Independent oracle decomposition.
 authority=a['active'][i]& (m['scenario'] in ['modification','replay','source_compromise'])
 truth=a['service'][i]&(a['level'][i]>=40)&(a['level'][i]<=60)&~authority
 assert np.array_equal(truth,a['truth'][i])
 rows=df[df.trace_id==i]
 for r in rows.itertuples():
  d=decide(authobs if r.auth else obs,'gate',window=r.window)
  assert (d if d is not None else -1)==r.declaration_step
  if d is not None:
   assert bool(r.unsafe)==bool(not all(truth[d-2:d+1]))
   assert bool(r.censored)==bool(d+5>=len(T))
   if not r.censored:assert bool(r.later)==bool(not all(truth[d+1:d+6]))
  audit_assessments+=1
 if (i+1)%720==0:print(f'audited {i+1}/5760 traces',flush=True)
print('FULL AUDIT PASS',flush=True)
md=pd.DataFrame(meta).drop(columns=['session'])
df=df.merge(md,on='trace_id',validate='many_to_one')
def summary(g):
 declared=g[~g.missing];future=declared[~declared.censored]
 return dict(n=len(g),declared=len(declared),unsafe=int(declared.unsafe.sum()),missing=int(g.missing.sum()),censored=int(declared.censored.sum()),later=int(future.later.sum()),future_eligible=len(future),median_wait_s=float(declared.wait_s.median()) if len(declared) else None)
out={'audit':dict(traces=len(meta),samples=a['level'].size,assessments=audit_assessments,status='PASS')}
out['methods']=[dict(auth=bool(auth),window=int(w),**summary(g)) for (auth,w),g in df.groupby(['auth','window'])]
out['scenarios']=[dict(scenario=s,auth=bool(au),window=int(w),**summary(g)) for (s,au,w),g in df[df.window.isin([3,8])].groupby(['scenario','auth','window'])]
out['factors']={}
for factor in ['duration','transport','buffer_s','sigma']:
 out['factors'][factor]=[dict(level=str(level),auth=bool(au),window=int(w),**summary(g)) for (level,au,w),g in df[df.window.isin([3,8])].groupby([factor,'auth','window'])]
# Correctly paired comparisons restricted to mutual declarations / complete follow-up.
left=df[(~df.auth)&(df.window==3)].set_index('trace_id')
right=df[df.auth&(df.window==8)].set_index('trace_id')
out['paired']={}
for metric in ['unsafe','later']:
 eligible=~left.missing & ~right.missing
 if metric=='later':eligible&=~left.censored&~right.censored
 l=left[eligible];r=right[eligible]
 lv=l[metric].astype(bool);rv=r[metric].astype(bool)
 improve=int((lv&~rv).sum());worse=int((~lv&rv).sum())
 blocks=np.array([[((lv.astype(int)-rv.astype(int))[l.seed==seed]).sum(),sum(l.seed==seed)] for seed in range(20000,20020)])
 generator=np.random.default_rng(20261107);ix=generator.integers(0,20,(10000,20));b=blocks[ix]
 samples=100*b[:,:,0].sum(axis=1)/b[:,:,1].sum(axis=1)
 out['paired'][metric]=dict(n=len(l),improve=improve,worsen=worse,difference_pp=100*(improve-worse)/len(l),conditional95=np.quantile(samples,[.025,.975]).tolist())
eligible=~left.missing & ~right.missing
out['paired_wait']=dict(n=int(sum(eligible)),median_s=float((right.loc[eligible,'wait_s']-left.loc[eligible,'wait_s']).median()),left_only=int((~left.missing&right.missing).sum()),right_only=int((left.missing&~right.missing).sum()),both_missing=int((left.missing&right.missing).sum()))
# Exploratory physical decomposition: no changes to frozen outcomes.
decomp=[]
for auth,w in [(False,3),(False,8),(True,3),(True,8)]:
 physical=authority_n=latency_n=only_physical=0
 for row in df[(df.auth==auth)&(df.window==w)&~df.missing].itertuples():
  i=row.trace_id;j=row.declaration_step;sl=slice(j-2,j+1)
  ph=bool(np.any((a['level'][i,sl]<40)|(a['level'][i,sl]>60)))
  au=bool(np.any(a['active'][i,sl])) and row.scenario in ['modification','replay','source_compromise']
  sv=bool(np.any(~a['service'][i,sl]))
  physical+=ph;authority_n+=au;latency_n+=sv;only_physical+=ph and not au and not sv
 decomp.append(dict(auth=auth,window=w,physical=physical,authority=authority_n,service=latency_n,physical_only=only_physical))
out['exploratory_decomposition']=decomp
(ROOT/'analysis.json').write_text(json.dumps(out,indent=2))
df.to_csv(ROOT/'analysis_records.csv.gz',index=False,compression='gzip')
print(json.dumps({k:v for k,v in out.items() if k not in ['scenarios','factors']},indent=2))
