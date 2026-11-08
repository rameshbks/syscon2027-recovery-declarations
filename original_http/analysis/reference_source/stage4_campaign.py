"""Stage 4 HMAC evidence and retrospective stability assessment on HTTP traces."""
import argparse
import copy
import csv
import hashlib
import json
import math
import random
import secrets
import sys
from pathlib import Path
import stage4_lab as lab
from evidence import sign, Verifier

SCENARIOS = lab.SCENARIOS + ('replay_evidence', 'stale_signed', 'missing_signed', 'source_compromise')
PRIMARY = ('connectivity', 'policy', 'gate_v2', 'gate_v3')
STRATEGIES = PRIMARY + ('auth_only', 'stability_only')
FILES = ('stage4_campaign.py', 'stage4_lab.py', 'network_lab_stage3.py', 'evidence.py')


def score(trace, method, declaration):
    # Same trailing-three outcome window and forward-five check for every method.
    ref = lab.evaluate(trace, 'unused', 0)[0]
    record = {k:v for k,v in ref.items() if k not in ('scenario','seed','strategy')}
    record.update(declaration_step=declaration, declaration_missing=declaration is None,
                  declaration_s=None, unsafe_declaration=None, invalid_evidence_declaration=None,
                  post_declaration_failure=None, followup_censored=None,
                  declaration_minus_reference_s=None)
    if declaration is not None:
        record['declaration_s'] = trace[declaration]['since_injection_s']
        trailing = trace[declaration-2:declaration+1]
        record['unsafe_declaration'] = not all(lab.outcome_ready(r['ground_truth']) for r in trailing)
        record['invalid_evidence_declaration'] = any(not r['evidence_truth']['valid'] for r in trailing)
        record['followup_censored'] = declaration+5 >= len(trace)
        if not record['followup_censored']:
            record['post_declaration_failure'] = any(not lab.outcome_ready(r['ground_truth']) for r in trace[declaration+1:declaration+6])
        if ref['reference_recovery_s'] is not None:
            record['declaration_minus_reference_s'] = record['declaration_s']-ref['reference_recovery_s']
    record.update(strategy=method, primary_comparator=method in PRIMARY)
    return record


def evaluate(trace, key, session, stability_window=8):
    verifier = Verifier(key, session)
    auth_observations, checks = [], []
    for row in trace:
        valid, reason, p = verifier.verify(row['packet'], row['elapsed_s'])
        checks.append(dict(index=row['index'], valid=valid, reason=reason))
        if p is None:
            p=dict(service_ok=False, monitor_present=False, probe_blocked=None,
                   age_s=None, observed_level=None)
        auth_observations.append(dict(p, index=row['index'],
                                      post_injection=row['observation']['post_injection']))
    observations = [r['observation'] for r in trace]
    decisions = {}
    for method in STRATEGIES:
        if method in ('connectivity','policy'):
            decision=lab.decide(observations, method)
        elif method == 'gate_v2':
            decision=lab.decide(observations,'gate')
        elif method == 'stability_only':
            decision=lab.decide(observations,'gate',window=stability_window)
        else:
            decision=lab.decide(auth_observations,'gate',window=3 if method=='auth_only' else stability_window)
        decisions[method]=decision
    records=[score(trace, method, decision) for method,decision in decisions.items()]
    return records, checks


def run_trial(scenario, seed, steps=65, interval=0.02, stability_window=8, key=None):
    mapping=dict(replay_evidence='misleading_evidence', stale_signed='stale',
                 missing_signed='monitor_loss', source_compromise='misleading_evidence')
    base=mapping.get(scenario, scenario)
    if scenario not in SCENARIOS or stability_window < 3:
        raise ValueError('invalid scenario or stability window')
    trace, _, schedule=lab.run_trial(base, seed, steps, interval)
    key=secrets.token_bytes(32) if key is None else key
    session=f'stage4:{scenario}:{seed}'
    cached=None
    for row in trace:
        p=copy.deepcopy(row['honest_observation'])
        age=p['age_s']
        captured=row['elapsed_s']-age if age is not None else row['elapsed_s']
        packet=sign(key,session,row['index'],captured,p)
        active=schedule['injection_step'] <= row['index'] < schedule['restore_step']
        manipulated=False
        if scenario in ('misleading_evidence','source_compromise','replay_evidence') and active:
            fake=dict(service_ok=True,monitor_present=True,probe_blocked=True,
                      age_s=0.0,observed_level=50.0)
            row['observation'].update(fake)
            manipulated=True
            if scenario=='misleading_evidence':
                # On-path attacker can alter contents, but has no source key.
                packet['body']['payload']=fake
            elif scenario=='source_compromise':
                # Legitimate source/key holder signs false measurements.
                packet=sign(key,session,row['index'],row['elapsed_s'],fake)
            else:
                # Authentic old packet: preserve signed sequence and timestamp.
                packet=copy.deepcopy(cached)
        if scenario in ('monitor_loss','missing_signed') and active:
            packet=None
        row['evidence_truth']['manipulated']=manipulated
        row['evidence_truth']['valid']=(row['evidence_truth']['monitoring_present'] and
             not manipulated and row['evidence_truth']['real_age_s'] is not None and
             0 <= row['evidence_truth']['real_age_s'] <= lab.FRESHNESS)
        row['packet']=packet
        if row['index'] < schedule['injection_step']:
            cached=copy.deepcopy(packet)
    records, checks=evaluate(trace,key,session,stability_window)
    for record in records:
        record.update(scenario=scenario,seed=seed)
    return trace, records, schedule, checks, key.hex(), session


def fingerprint():
    root=Path(__file__).parent
    return {name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in FILES}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--seeds',type=int,default=2)
    p.add_argument('--steps',type=int,default=65)
    p.add_argument('--interval',type=float,default=0.02)
    p.add_argument('--stability-window',type=int,default=8)
    a=p.parse_args(argv)
    if a.seeds<1 or a.steps<50 or not math.isfinite(a.interval) or a.interval<0 or not 3<=a.stability_window<=a.steps-10:
        p.error('invalid seeds, steps, interval or stability window')
    try:
        a.out.mkdir(parents=True,exist_ok=False)
    except FileExistsError:
        p.error('output exists; choose a new directory')
    jobs=[(s,seed) for s in SCENARIOS for seed in range(a.seeds)]
    random.Random(20261105).shuffle(jobs)
    manifest=dict(stage='Stage 4 loopback HTTP trace-based HMAC experiment',status='running',
                  scenarios=list(SCENARIOS),strategies=list(STRATEGIES),primary_strategies=list(PRIMARY),
                  seeds=a.seeds,steps=a.steps,interval_target_s=a.interval,
                  stability_window=a.stability_window,hashes=fingerprint(),python=sys.version,
                  completed_trials=0,schedules=[],
                  limitations=['All roles share a host and process; no hardware trust boundary',
                               'Evidence signed and verified retrospectively on recorded HTTP traces',
                               'HMAC keys in audit_keys.json are disposable laboratory keys, not production credentials',
                               'Gate decisions do not control restoration',
                               'Authentication does not establish truthful measurement by a compromised signer',
                               'Sample windows cannot guarantee future availability'])
    mp=a.out/'manifest.json'
    mp.write_text(json.dumps(manifest,indent=2)+'\n')
    records, keys=[], {}
    with (a.out/'traces.jsonl').open('w') as f:
        for n,(scenario,seed) in enumerate(jobs,1):
            trace,result,schedule,checks,key,session=run_trial(scenario,seed,a.steps,a.interval,a.stability_window)
            keys[session]=key
            for row,check in zip(trace,checks):
                f.write(json.dumps(dict(row,scenario=scenario,seed=seed,session=session,verification=check))+'\n')
            f.flush()
            records.extend(result)
            manifest['completed_trials']=n
            manifest['schedules'].append(dict(scenario=scenario,seed=seed,**schedule))
            mp.write_text(json.dumps(manifest,indent=2)+'\n')
            (a.out/'audit_keys.json').write_text(json.dumps(keys,indent=2)+'\n')
            print(f'[{n}/{len(jobs)}] {scenario} seed {seed} complete',flush=True)
    with (a.out/'runs.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]))
        w.writeheader()
        w.writerows(records)
    manifest.update(status='completed',trials=len(jobs),primary_evaluations=len(jobs)*4,
                    ablation_evaluations=len(jobs)*2,total_strategy_evaluations=len(records))
    mp.write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'COMPLETED {len(jobs)} traces; {len(jobs)*4} primary and {len(jobs)*2} ablation evaluations')


if __name__=='__main__':
    main()
