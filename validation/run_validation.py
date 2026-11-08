"""Frozen-predicate held-out schedule campaign; local loopback HTTP only."""
import sys,inspect,json,random,hashlib,time,csv,platform
from pathlib import Path
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(Path('stage4').resolve()))
import stage4_campaign as campaign
import stage4_lab as lab
import network_lab_stage3 as net
SCENARIOS=tuple(s for s in campaign.SCENARIOS if s not in ('stale_signed','missing_signed'))
SEEDS=list(range(10000,10020))
# Wrapping the HMI handler delays a real response path before backend sampling.
original_handler=net.gateway_handler
def delayed_handler(plc_port,state,ingress,plc_host='127.0.0.1'):
 cls=original_handler(plc_port,state,ingress,plc_host)
 if ingress=='hmi':
  route=cls.route
  def delayed(self):
   time.sleep(getattr(state,'response_delay_s',0.0))
   return route(self)
  cls.route=cls.do_GET=cls.do_POST=delayed
 return cls
net.gateway_handler=delayed_handler
# Change the generator only; declaration functions, verifier, score remain unchanged.
source=inspect.getsource(lab.run_trial)
source=source.replace('start_step = 10','start_step = rng.randint(6, 18)')
source=source.replace('rng.randint(10, 14)','rng.randint(4, 24)')
source=source.replace('rng.randint(6, 10)','rng.randint(3, 15)')
source=source.replace('failures = {i for i in range(start_step, policy_restore) if rng.random() < 0.42}',
 'failure_probability = rng.uniform(0.2, 0.7)\n    failures = {i for i in range(start_step, policy_restore) if rng.random() < failure_probability}\n    delays = [rng.uniform(0.08,0.13) if rng.random() < 0.15 else rng.uniform(0,0.03) for _ in range(steps)]')
source=source.replace('state.configure(outage=outage, permissive=permissive, stale=stale)',
 'state.configure(outage=outage, permissive=permissive, stale=stale, response_delay_s=delays[index])')
source=source.replace('intermittent_failure_steps=sorted(failures)', 'response_delay_s=delays, intermittent_probability=failure_probability, intermittent_failure_steps=sorted(failures)')
(ROOT/'generator_frozen.py').write_text(source)
namespace=dict(lab.__dict__)
exec(compile(source,str(ROOT/'generator_frozen.py'),'exec'),namespace)
lab.run_trial=namespace['run_trial']
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
manifest=dict(design_frozen_utc=datetime.now(timezone.utc).isoformat(),scenarios=SCENARIOS,seeds=SEEDS,steps=80,interval_s=.02,window_samples=[3,8],outcome_window_samples=3,followup_samples=5,deadline_s=.1,freshness_s=.06,
 injection_step='discrete uniform 6..18',duration_steps='discrete uniform 4..24',policy_delay_steps='discrete uniform 3..15',intermittent_probability='uniform 0.2..0.7',hmi_delay='per sample: 85% U(0,30 ms), 15% U(80,130 ms); sleep before HMI gateway routing',execution='sequential, local Linux runtime; real HTTP; same scalar process; no external physical validation',python=sys.version,platform=platform.platform(),source_hashes=campaign.fingerprint(),runner_sha256=digest(__file__),generator_sha256=digest(ROOT/'generator_frozen.py'),planned_trials=len(SCENARIOS)*len(SEEDS))
(ROOT/'design_frozen.json').write_text(json.dumps(manifest,indent=2))
jobs=[(s,n) for s in SCENARIOS for n in SEEDS]
random.Random(20261106).shuffle(jobs)
records=[];schedules=[];keys={}
with (ROOT/'traces.jsonl').open('w') as traceout:
 for count,(scenario,seed) in enumerate(jobs,1):
  trace,rr,schedule,checks,key,session=campaign.run_trial(scenario,seed,80,.02,8)
  keys[session]=key;records.extend(rr);schedules.append(dict(scenario=scenario,seed=seed,**schedule))
  for r,c in zip(trace,checks):
   traceout.write(json.dumps(dict(r,scenario=scenario,seed=seed,session=session,verification=c))+'\n')
  traceout.flush()
  if count%10==0:print(f'{count}/{len(jobs)} trials completed',flush=True)
with (ROOT/'runs.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
(ROOT/'schedules.json').write_text(json.dumps(schedules,indent=2))
(ROOT/'audit_keys.json').write_text(json.dumps(keys))
manifest['completed_trials']=len(jobs);manifest['completed_utc']=datetime.now(timezone.utc).isoformat()
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('COMPLETE',flush=True)
