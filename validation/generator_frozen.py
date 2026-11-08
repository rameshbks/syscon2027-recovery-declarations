def run_trial(scenario, seed, steps=55, interval=0.02):
    if scenario not in SCENARIOS or steps < 40 or not math.isfinite(interval) or interval < 0:
        raise ValueError('invalid scenario, steps or interval')
    mixed = int.from_bytes(hashlib.sha256(f'{scenario}:{seed}'.encode()).digest()[:8], 'big')
    rng = random.Random(mixed)
    start_step = rng.randint(6, 18)
    restore_step = start_step + rng.randint(4, 24)
    policy_restore = restore_step + rng.randint(3, 15)
    failure_probability = rng.uniform(0.2, 0.7)
    failures = {i for i in range(start_step, policy_restore) if rng.random() < failure_probability}
    delays = [rng.uniform(0.08,0.13) if rng.random() < 0.15 else rng.uniform(0,0.03) for _ in range(steps)]
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
            state.configure(outage=outage, permissive=permissive, stale=stale, response_delay_s=delays[index])
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
                    response_delay_s=delays, intermittent_probability=failure_probability, intermittent_failure_steps=sorted(failures) if scenario == 'intermittent' else [])
    return rows, evaluate(rows, scenario, seed), schedule
