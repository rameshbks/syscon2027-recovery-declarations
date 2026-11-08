"""Stage 3 v2: process-outcome oracle and deceptive-evidence negative control.

Loopback HTTP only; shadow decisions; no distributed Docker fault injection.
The unchanged network_lab_stage3.py dependency supplies the laboratory.
"""
import argparse
import csv
import hashlib
import json
import math
import random
import sys
import time
from pathlib import Path
from network_lab_stage3 import laboratory, request

SCENARIOS = ('normal', 'permissive', 'outage', 'stale', 'partial_restore',
             'monitor_loss', 'combined', 'persistent_outage',
             'intermittent', 'misleading_evidence')
STRATEGIES = ('connectivity', 'policy', 'gate')
WINDOW = 3
FOLLOWUP = 5
FRESHNESS = 0.06
DEADLINE = 0.1


def decide(observations, method, window=WINDOW, fresh_limit=FRESHNESS):
    if method not in STRATEGIES or window < 1:
        raise ValueError('invalid strategy or window')
    count = 0
    for o in observations:
        if not o['post_injection']:
            continue
        ready = bool(o['service_ok'])
        if method in ('policy', 'gate'):
            ready = ready and o['monitor_present'] and o['probe_blocked'] is True
        if method == 'gate':
            age, level = o['age_s'], o['observed_level']
            ready = (ready and age is not None and math.isfinite(age) and
                     0 <= age <= fresh_limit and level is not None and
                     math.isfinite(level) and 40 <= level <= 60)
        count = count + 1 if ready else 0
        if count >= window:
            return o['index']
    return None


def outcome_ready(truth):
    """Primary oracle. Never reads coordinator evidence or configured fault flags.

    A valid target is required because a corrupted target can precede a physical
    excursion. Benchmark operational requirement, NOT industrial safety proof.
    """
    return (truth['service_completed'] and truth['service_latency_s'] <= DEADLINE and
            40 <= truth['physical_level'] <= 60 and
            abs(truth['controller_target'] - 50.0) <= 1e-9 and
            truth['accepted_unauthorized_writes'] == 0)


def evaluate(trace, scenario, seed, window=WINDOW, followup=FOLLOWUP):
    post = [r for r in trace if r['observation']['post_injection']]
    readiness = {r['index']: outcome_ready(r['ground_truth']) for r in trace}
    # Earliest retrospective reference with both a trailing window and follow-up.
    reference = next((r['index'] for r in post
                      if r['index'] >= post[0]['index'] + window - 1
                      and r['index'] + followup < len(trace)
                      and all(readiness[i] for i in
                              range(r['index']-window+1, r['index']+followup+1))), None)
    records = []
    for method in STRATEGIES:
        declaration = decide([r['observation'] for r in trace], method, window)
        elapsed = lambda i: None if i is None else trace[i]['since_injection_s']
        unsafe, evidence_bad, relapse, censored = None, None, None, None
        if declaration is not None:
            trailing = trace[declaration-window+1:declaration+1]
            unsafe = not all(outcome_ready(r['ground_truth']) for r in trailing)
            evidence_bad = any(not r['evidence_truth']['valid'] for r in trailing)
            censored = declaration + followup >= len(trace)
            if not censored:
                # Full future horizon only; never pad missing observations.
                relapse = any(not readiness[i] for i in
                              range(declaration+1, declaration+followup+1))
        records.append(dict(scenario=scenario, seed=seed, strategy=method,
                            declaration_step=declaration, declaration_s=elapsed(declaration),
                            declaration_missing=declaration is None,
                            unsafe_declaration=unsafe,
                            invalid_evidence_declaration=evidence_bad,
                            post_declaration_failure=relapse,
                            followup_censored=censored,
                            reference_recovery_step=reference,
                            reference_recovery_s=elapsed(reference),
                            reference_recovery_unobserved=reference is None,
                            declaration_minus_reference_s=None if reference is None or declaration is None
                            else elapsed(declaration)-elapsed(reference),
                            unauthorized_writes=sum(r['ground_truth']['accepted_unauthorized_writes'] for r in post),
                            out_of_band_samples=sum(not 40 <= r['ground_truth']['physical_level'] <= 60 for r in post),
                            invalid_target_samples=sum(abs(r['ground_truth']['controller_target']-50) > 1e-9 for r in post),
                            service_failure_samples=sum(not r['ground_truth']['service_completed'] or
                                                        r['ground_truth']['service_latency_s'] > DEADLINE for r in post)))
    return records


def run_trial(scenario, seed, steps=55, interval=0.02):
    if scenario not in SCENARIOS or steps < 40 or not math.isfinite(interval) or interval < 0:
        raise ValueError('invalid scenario, steps or interval')
    mixed = int.from_bytes(hashlib.sha256(f'{scenario}:{seed}'.encode()).digest()[:8], 'big')
    rng = random.Random(mixed)
    start_step = 10
    restore_step = start_step + rng.randint(10, 14)
    policy_restore = restore_step + rng.randint(6, 10)
    failures = {i for i in range(start_step, policy_restore) if rng.random() < 0.42}
    if scenario == 'intermittent':
        failures.add(start_step)
    rows = []
    with laboratory() as (process, state, plc, hmi, it):
        started, injected_at = time.monotonic(), None
        for index in range(steps):
            iteration = time.monotonic()
            if index == start_step:
                injected_at = time.monotonic()
            active = start_step <= index < restore_step
            late = start_step <= index < policy_restore
            outage = scenario in ('outage', 'partial_restore', 'combined') and active
            outage |= scenario == 'persistent_outage' and index >= start_step
            outage |= scenario == 'intermittent' and index in failures
            permissive = scenario in ('permissive', 'misleading_evidence') and active
            permissive |= scenario in ('partial_restore', 'combined') and late
            stale = (scenario == 'stale' and active) or (scenario == 'combined' and late)
            monitor = not (scenario == 'monitor_loss' and active)
            state.configure(outage=outage, permissive=permissive, stale=stale)
            if index in (restore_step, policy_restore):
                process.write(50.0)
            status, sample, latency = request(hmi)
            # Counter measured around the actual IT write, excluding harness resets.
            with process.lock:
                writes_before = process.writes
            probe_status, probe, _ = request(it, 'POST', '/setpoint', {'value': 80.0})
            physical = process.sample()
            with process.lock:
                target = process.setpoint
                write_delta = process.writes - writes_before
            observed_at = time.monotonic()
            age = None if status != 200 else observed_at - sample['measured_at']
            service_ok = status == 200 and latency <= DEADLINE
            observed_blocked = (probe_status == 403) if monitor else None
            observed_age = age if monitor else None
            observed_level = sample.get('level') if monitor else None
            honest_observation = dict(service_ok=service_ok, monitor_present=monitor,
                                      probe_blocked=observed_blocked, age_s=observed_age,
                                      observed_level=observed_level)
            manipulated = scenario == 'misleading_evidence' and active
            if manipulated:
                observed_blocked, observed_age, observed_level = True, 0.0, 50.0
            observation = dict(index=index, post_injection=index >= start_step,
                               service_ok=service_ok, monitor_present=monitor,
                               probe_blocked=observed_blocked, age_s=observed_age,
                               observed_level=observed_level)
            ground_truth = dict(service_completed=status == 200, service_latency_s=latency,
                                physical_level=physical['level'], controller_target=target,
                                accepted_unauthorized_writes=write_delta)
            # Secondary evidence metric distinct from the process outcome oracle.
            evidence_valid = (monitor and not manipulated and age is not None and
                              0 <= age <= FRESHNESS)
            rows.append(dict(index=index, elapsed_s=observed_at-started,
                             since_injection_s=None if injected_at is None else observed_at-injected_at,
                             observation=observation, honest_observation=honest_observation, ground_truth=ground_truth,
                             evidence_truth=dict(valid=evidence_valid, real_age_s=age,
                                                 monitoring_present=monitor, manipulated=manipulated),
                             raw_http=dict(service_status=status, probe_status=probe_status,
                                           probe_ack=probe.get('written')),
                             injection=dict(outage=outage, permissive=permissive, stale=stale)))
            remaining = interval - (time.monotonic()-iteration)
            if remaining > 0:
                time.sleep(remaining)
    schedule = dict(injection_step=start_step, restore_step=restore_step,
                    policy_restore_step=policy_restore,
                    intermittent_failure_steps=sorted(failures) if scenario == 'intermittent' else [])
    return rows, evaluate(rows, scenario, seed), schedule


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seeds', type=int, default=2)
    parser.add_argument('--steps', type=int, default=55)
    parser.add_argument('--interval', type=float, default=0.02)
    args = parser.parse_args(argv)
    if args.seeds < 1 or args.steps < 40 or not math.isfinite(args.interval) or args.interval < 0:
        parser.error('require seeds >=1, steps >=40 and finite interval >=0')
    try:
        args.out.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error('output directory exists; choose a new name to preserve evidence')
    jobs = [(scenario, seed) for scenario in SCENARIOS for seed in range(args.seeds)]
    random.Random(20261105).shuffle(jobs)
    source = Path(__file__)
    manifest = dict(stage='Stage 3 v2 loopback HTTP shadow decisions', status='running',
                    scenarios=list(SCENARIOS), strategies=list(STRATEGIES), seeds=args.seeds,
                    steps=args.steps, interval_target_s=args.interval,
                    window_samples=WINDOW, forward_followup_samples=FOLLOWUP,
                    freshness_limit_s=FRESHNESS, service_deadline_s=DEADLINE,
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    dependency_sha256=hashlib.sha256(source.with_name('network_lab_stage3.py').read_bytes()).hexdigest(),
                    python_version=sys.version, schedules=[], completed_trials=0,
                    limitations=['No packet-level or distributed Docker fault injection',
                                 'Shadow declarations do not control restoration or reduce exposure',
                                 'Primary oracle reads direct process state and write counter; service criterion remains shared',
                                 'Oracle is a synthetic operational requirement, not physical safety certification',
                                 'Unauthenticated observation forgery is a synthetic negative control',
                                 'Seeded schedules reproduce; wall-clock timings do not'])
    manifest_path = args.out/'manifest.json'
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    records = []
    with (args.out/'traces.jsonl').open('w', encoding='utf-8') as f:
        for n, (scenario, seed) in enumerate(jobs, 1):
            trace, result, schedule = run_trial(scenario, seed, args.steps, args.interval)
            for row in trace:
                f.write(json.dumps(dict(scenario=scenario, seed=seed, **row))+'\n')
            f.flush()
            records.extend(result)
            manifest['schedules'].append(dict(scenario=scenario, seed=seed, **schedule))
            manifest['completed_trials'] = n
            manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
            print(f'[{n}/{len(jobs)}] {scenario} seed {seed} complete', flush=True)
    with (args.out/'runs.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    manifest.update(status='completed', independent_scenario_seed_trials=len(jobs),
                    strategy_evaluations=len(records))
    manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'COMPLETED {len(jobs)} trials; {len(records)} strategy evaluations')


if __name__ == '__main__':
    main()
