import json,csv,sys,hashlib,collections,statistics,math
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(Path('stage4').resolve()))
from stage4_campaign import evaluate,STRATEGIES,fingerprint
from stage4_lab import outcome_ready
m=json.loads((ROOT/'manifest.json').read_text())
assert m['completed_trials']==240
assert m['source_hashes']==fingerprint()
keys=json.loads((ROOT/'audit_keys.json').read_text())
sched={(r['scenario'],r['seed']):r for r in json.loads((ROOT/'schedules.json').read_text())}
traces=collections.defaultdict(list)
for line in (ROOT/'traces.jsonl').open():
 r=json.loads(line);traces[(r['scenario'],r['seed'])].append(r)
expected={(s,n) for s in m['scenarios'] for n in m['seeds']}
assert set(traces)==expected
saved=list(csv.DictReader((ROOT/'runs.csv').open()))
bykey={(r['scenario'],int(r['seed']),r['strategy']):r for r in saved}
assert len(bykey)==1440==len(saved)
delay_count=0;overdeadline=0;num=0
for (s,n),trace in traces.items():
 assert [r['index'] for r in trace]==list(range(80))
 session=f'stage4:{s}:{n}'
 assert all(r['session']==session for r in trace)
 records,checks=evaluate(trace,bytes.fromhex(keys[session]),session,8)
 assert checks==[r['verification'] for r in trace]
 for rr in records:
  rr.update(scenario=s,seed=n)
  want={k:'' if v is None else str(v) for k,v in rr.items()}
  assert want==bykey[(s,n,rr['strategy'])]
  # Independently label the common trailing-3 and forward-5 outcome slices.
  i=rr['declaration_step']
  if i is not None:
   assert rr['unsafe_declaration']==any(not outcome_ready(t['ground_truth']) for t in trace[i-2:i+1])
   assert rr['followup_censored']==(i+5>=len(trace))
 for r,delay in zip(trace,sched[(s,n)]['response_delay_s']):
  assert r['observation']['post_injection']==(r['index']>=sched[(s,n)]['injection_step'])
  latency=r['ground_truth']['service_latency_s']
  assert latency>=delay-0.003,(s,n,r['index'],latency,delay)
  delay_count+=delay>.08;overdeadline+=latency>.1;num+=1
metrics=['unsafe_declaration','invalid_evidence_declaration','declaration_missing','post_declaration_failure','followup_censored']
summary=[]
for strategy in STRATEGIES:
 rows=[r for r in saved if r['strategy']==strategy]
 out={k:sum(r[k]=='True' for r in rows) for k in metrics}
 out.update(strategy=strategy,n=len(rows),declared=sum(r['declaration_missing']=='False' for r in rows),future_eligible=sum(r['followup_censored']=='False' for r in rows))
 summary.append(out)
scenario=[]
for s in m['scenarios']:
 out={'scenario':s}
 for method in ['gate_v2','gate_v3','auth_only','stability_only']:
  group=[r for r in saved if r['scenario']==s and r['strategy']==method]
  out[method]={k:sum(r[k]=='True' for r in group) for k in metrics}
 scenario.append(out)
pair={}
for field in ['unsafe_declaration','post_declaration_failure']:
 pairs=[(bykey[(s,n,'gate_v2')],bykey[(s,n,'gate_v3')]) for s,n in expected]
 eligible=[(a,b) for a,b in pairs if a[field]!='' and b[field]!='']
 improve=sum(a[field]=='True' and b[field]=='False' for a,b in eligible)
 worsen=sum(a[field]=='False' and b[field]=='True' for a,b in eligible)
 # Conditional seed-block bootstrap over fixed 12-condition mix; denominator varies with eligibility.
 blocks=[]
 for n in m['seeds']:
  ep=[(a,b) for a,b in eligible if int(a['seed'])==n]
  blocks.append((sum((a[field]=='True')-(b[field]=='True') for a,b in ep),len(ep)))
 rng=np.random.default_rng(20261106)
 ix=rng.integers(0,len(blocks),(10000,len(blocks)))
 arr=np.array(blocks);boot=100*np.sum(arr[ix,0],axis=1)/np.sum(arr[ix,1],axis=1)
 pair[field]=dict(eligible=len(eligible),improve=improve,worsen=worsen,difference_pp=100*(improve-worsen)/len(eligible),conditional95=list(np.quantile(boot,[.025,.975])))
wait=[1000*(float(b['declaration_s'])-float(a['declaration_s'])) for (s,n) in expected
 for a,b in [(bykey[(s,n,'gate_v2')],bykey[(s,n,'gate_v3')])] if a['declaration_s'] and b['declaration_s']]
out=dict(summary=summary,scenarios=scenario,paired=pair,paired_wait_n=len(wait),paired_wait_median_ms=statistics.median(wait),samples=num,high_delay_samples=delay_count,deadline_exceeded_samples=overdeadline,audit='PASS: all trace coverage, source hashes, signed verdicts, 1440 outcome records, schedules and real request-delay checks')
(ROOT/'analysis.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
