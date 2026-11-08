"""Frozen standalone process campaign and declaration engine."""
import json,hashlib,hmac,sys,time,itertools,gzip,platform
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from plant import PARAMS,equilibrium,step,control
# Only the fixed cryptographic control is shared with earlier experiments.
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'stage4'))
from evidence import sign,Verifier,canonical
ROOT=Path(__file__).resolve().parent
SCENARIOS=['normal','outage','persistent_outage','intermittent','delayed_evidence','modification','replay','source_compromise']
SEEDS=range(20000,20020);WINDOWS=[3,5,8,12]
def rng(seed):return np.random.default_rng(seed)
def first_run(mask,w):
 # Separate vectorized implementation, checked against the frozen scalar engine.
 cs=np.cumsum(mask.astype(np.int16));roll=cs.copy()
 roll[w:]-=cs[:-w];roll[:w-1]=0
 ix=np.flatnonzero(roll>=w)
 return int(ix[0]) if len(ix) else -1
def make_paths(dt=.01):
 specs=[(s,d,seed) for s in SCENARIOS for d in ['short','long'] for seed in SEEDS]
 n=len(specs);times=np.arange(round(60/dt)+1)*dt
 starts=[];ends=[]
 for s,d,seed in specs:
  r=rng(seed);start=round(r.uniform(5,10)/.2)*.2
  duration=round(r.uniform(.4,1.2) if d=='short' else r.uniform(4,10),10)
  duration=round(duration/.2)*.2
  starts.append(start);ends.append(start+duration)
 starts=np.array(starts);ends=np.array(ends)
 attacks=np.array([s in ['modification','replay','source_compromise'] for s,d,z in specs])
 h1,h2,q=equilibrium();h1=np.full(n,h1);h2=np.full(n,h2);q=np.full(n,q);integral=np.zeros(n)
 history=np.empty((n,len(times)));history[:,0]=h2
 for j,t in enumerate(times[:-1]):
  active=(t>=starts-1e-8)&(t<ends-1e-8)&attacks
  target=np.where(active,.8,.5)
  if j%round(.02/dt)==0:q,integral=control(h2,target,integral,.02)
  h1,h2=step(h1,h2,q,dt)
  history[:,j+1]=h2
 return specs,starts,ends,history
def run():
 protocol=json.loads((ROOT/'protocol.json').read_text())
 hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('*.py')}
 frozen=dict(protocol=protocol,frozen_utc=datetime.now(timezone.utc).isoformat(),source_sha256=hashes,
  fixed_evidence_sha256=hashlib.sha256((Path(__file__).resolve().parents[2]/'stage4/evidence.py').read_bytes()).hexdigest(),
  python=sys.version,numpy=np.__version__,platform=platform.platform())
 (ROOT/'design_frozen.json').write_text(json.dumps(frozen,indent=2))
 specs,starts,ends,history=make_paths()
 t=np.arange(301)*.2
 shape=(len(specs)*18,len(t));N=shape[0]
 arrays={k:np.empty(shape,dtype=np.float64) for k in ['level','capture_level','latency','age','noisy_level']}
 for k in ['active','service','policy','post','truth','manipulated','auth_ok']:arrays[k]=np.empty(shape,dtype=np.bool_)
 # raw capture times + honest payloads, plus deterministic packet recipe, reproduce all MACs.
 records=[];metadata=[];packet_digests=[]
 for pid,(scenario,duration,seed) in enumerate(specs):
  for transport,buffer,sigma in itertools.product(range(3),[0.,.04,.10],[0.,2.]):
   idx=len(metadata);r=rng(seed+170000)
   u=r.random(len(t));lat=np.array([.005,.045,.085])[transport]+u*np.array([.01,.02,.03])[transport]
   active=(t>=starts[pid]-1e-8)&(t<ends[pid]-1e-8)
   post=t>=starts[pid]-1e-8
   extra=.12*active if scenario=='delayed_evidence' else 0.
   age=lat+buffer+extra
   captured=np.maximum(0,t-age)
   age=t-captured
   xp=captured/.01;lo=np.floor(xp).astype(int);hi=np.minimum(lo+1,6000);frac=xp-lo
   captured_level=100*(history[pid,lo]*(1-frac)+history[pid,hi]*frac)
   level=100*history[pid,::20]
   noisy=captured_level+sigma*rng(seed+180000).standard_normal(len(t))
   outage=np.zeros(len(t),bool)
   if scenario=='outage':outage=active.copy()
   elif scenario=='persistent_outage':outage=post.copy()
   elif scenario=='intermittent':outage=active&(rng(seed+190000).random(len(t))<.4)
   service=(~outage)&(lat<=.1)
   writes=active&np.isin(scenario,['modification','replay','source_compromise'])
   policy=(~outage)&(~writes)
   truth=service&(level>=40)&(level<=60)&(~writes)
   manipulated=active&np.isin(scenario,['modification','replay','source_compromise'])
   session=f'tanks:{scenario}:{duration}:{transport}:{buffer}:{sigma}:{seed}'
   key=hashlib.sha256(('laboratory-only:'+session).encode()).digest()
   verifier=Verifier(key,session)
   auth_payload=[];auth_ok=[];packets=hashlib.sha256();cached=None
   # Unauthenticated payload is honest unless evidence is manipulated.
   obslevel=noisy.copy();obsage=age.copy();obsservice=service.copy();obspolicy=policy.copy()
   obslevel[manipulated]=50.;obsage[manipulated]=0.;obsservice[manipulated]=True;obspolicy[manipulated]=True
   for j,now in enumerate(t):
    payload=dict(service_ok=bool(service[j]),monitor_present=True,probe_blocked=bool(policy[j]),observed_level=float(noisy[j]),age_s=float(age[j]))
    packet=sign(key,session,j,float(captured[j]),payload)
    if manipulated[j]:
     fake=dict(service_ok=True,monitor_present=True,probe_blocked=True,observed_level=50.,age_s=0.)
     if scenario=='modification':packet['body']['payload']=fake
     elif scenario=='source_compromise':packet=sign(key,session,j,float(now-lat[j]),fake)
     else:packet=cached
    if not post[j]:cached=packet
    packets.update(json.dumps(packet,sort_keys=True,separators=(',',':')).encode())
    ok,reason,p=verifier.verify(packet,float(now));auth_ok.append(ok)
    auth_payload.append(p)
   auth=np.array(auth_ok)
   base=obsservice&obspolicy&np.isfinite(obslevel)&(obslevel>=40)&(obslevel<=60)&(obsage>=0)&(obsage<=.06)&post
   abase=np.array([p is not None and p['service_ok'] and p['monitor_present'] and p['probe_blocked'] is True and p['observed_level'] is not None and 40<=p['observed_level']<=60 for p in auth_payload])&auth&post
   meta=dict(trace_id=idx,path_id=pid,scenario=scenario,duration=duration,transport=['low','age_boundary','deadline_boundary'][transport],buffer_s=buffer,sigma=sigma,seed=seed,onset_s=float(starts[pid]),end_s=float(ends[pid]),session=session)
   metadata.append(meta);packet_digests.append(packets.hexdigest())
   for k,v in dict(level=level,capture_level=captured_level,latency=lat,age=age,noisy_level=noisy,active=active,service=service,policy=policy,post=post,truth=truth,manipulated=manipulated,auth_ok=auth).items():arrays[k][idx]=v
   for useauth,mask in [(False,base),(True,abase)]:
    for w in WINDOWS:
     dec=first_run(mask,w)
     missing=dec<0;censored=(not missing and dec+5>=len(t))
     unsafe=None if missing else not bool(np.all(truth[dec-2:dec+1]))
     later=None if missing or censored else not bool(np.all(truth[dec+1:dec+6]))
     invalid=None if missing else bool(np.any(manipulated[dec-2:dec+1]|(age[dec-2:dec+1]>.06)))
     records.append(dict(trace_id=idx,auth=useauth,window=w,declaration_step=dec,missing=missing,censored=censored,unsafe=unsafe,later=later,invalid=invalid,wait_s=None if missing else float(t[dec]-starts[pid])))
   if (idx+1)%360==0:print(f'{idx+1}/{N} traces',flush=True)
 arrays['time_s']=t
 np.savez_compressed(ROOT/'traces.npz',**arrays)
 (ROOT/'metadata.json').write_text(json.dumps(metadata))
 (ROOT/'packet_digests.json').write_text(json.dumps(packet_digests))
 import csv
 with (ROOT/'outcomes.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=records[0]);w.writeheader();w.writerows(records)
 frozen.update(completed_utc=datetime.now(timezone.utc).isoformat(),traces=N,assessments=len(records),samples=N*len(t))
 (ROOT/'manifest.json').write_text(json.dumps(frozen,indent=2))
 print('COMPLETE',flush=True)
if __name__=='__main__':run()
