"""Loopback HTTP laboratory with a simulated process and enforced gateway ACL.

No external destinations, host firewall changes, dependencies or privileged calls.
"""
import argparse
import csv
import hashlib
import http.client
import json
import random
import threading
import time
from contextlib import ExitStack, contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SCENARIOS = ('normal', 'permissive', 'outage', 'stale', 'partial_restore',
             'monitor_loss', 'combined', 'persistent_outage')


def request(port, method='GET', path='/sample', payload=None, timeout=0.2, host='127.0.0.1'):
    start = time.monotonic()
    conn = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        body = None if payload is None else json.dumps(payload)
        conn.request(method, path, body, {'Content-Type': 'application/json'})
        response = conn.getresponse()
        return response.status, json.loads(response.read()), time.monotonic() - start
    except (OSError, TimeoutError, http.client.HTTPException, ValueError):
        return 0, {}, time.monotonic() - start
    finally:
        conn.close()


class Process:
    def __init__(self):
        self.lock = threading.Lock()
        self.level = 50.0
        self.setpoint = 50.0
        self.writes = 0
        self.last = time.monotonic()

    def sample(self):
        with self.lock:
            now = time.monotonic()
            # Explicitly simulated plant: local controller independent of HMI.
            dt = now - self.last
            self.level += max(-20.0, min(20.0, 2.0 * (self.setpoint - self.level))) * dt
            self.last = now
            return dict(level=self.level, measured_at=now, writes=self.writes)

    def write(self, value):
        self.sample()
        with self.lock:
            self.setpoint = float(value)
            self.writes += 1


class QuietHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, status, value):
        body = json.dumps(value).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def plc_handler(process):
    class PLC(QuietHandler):
        def do_GET(self):
            if self.path != '/sample':
                return self.reply(404, {})
            self.reply(200, process.sample())

        def do_POST(self):
            if self.path != '/setpoint':
                return self.reply(404, {})
            try:
                data = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                value = float(data['value'])
                if not 0 <= value <= 100:
                    raise ValueError()
                process.write(value)
                self.reply(200, {'written': True})
            except (KeyError, ValueError, TypeError):
                self.reply(400, {'written': False})
    return PLC


class GatewayState:
    def __init__(self):
        self.lock = threading.Lock()
        self.outage = False
        self.permissive = False
        self.stale = False
        self.cached = None

    def configure(self, **values):
        with self.lock:
            for key, value in values.items():
                setattr(self, key, value)


def gateway_handler(plc_port, state, ingress, plc_host='127.0.0.1'):
    class Gateway(QuietHandler):
        def route(self):
            with state.lock:
                outage, permissive, stale, cached = (
                    state.outage, state.permissive, state.stale, state.cached)
            if outage:
                return self.reply(503, {'error': 'link unavailable'})
            # Identity comes from a separate server listener, never a client header.
            allowed = (ingress == 'hmi' and self.command == 'GET' and self.path == '/sample')
            allowed = allowed or (ingress == 'it' and permissive and
                                  self.command == 'POST' and self.path == '/setpoint')
            if not allowed:
                return self.reply(403, {'error': 'denied'})
            if ingress == 'hmi' and stale and cached is not None:
                return self.reply(200, cached)
            payload = None
            if self.command == 'POST':
                try:
                    payload = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                except (KeyError, ValueError):
                    return self.reply(400, {})
            status, data, _ = request(plc_port, self.command, self.path, payload, host=plc_host)
            if ingress == 'hmi' and status == 200:
                state.configure(cached=data)
            self.reply(status or 502, data)

        do_GET = route
        do_POST = route
    return Gateway


@contextmanager
def server(handler):
    httpd = ThreadingHTTPServer(('127.0.0.1', 0), handler)
    httpd.daemon_threads = True
    worker = threading.Thread(target=lambda: httpd.serve_forever(poll_interval=0.01), daemon=True)
    worker.start()
    try:
        yield httpd.server_port
    finally:
        httpd.shutdown()
        httpd.server_close()
        worker.join(timeout=1)


@contextmanager
def laboratory():
    process, state = Process(), GatewayState()
    with ExitStack() as stack:
        plc = stack.enter_context(server(plc_handler(process)))
        hmi = stack.enter_context(server(gateway_handler(plc, state, 'hmi')))
        it = stack.enter_context(server(gateway_handler(plc, state, 'it')))
        yield process, state, plc, hmi, it


def decide(observations, method, window=3, fresh_limit=0.06):
    count = 0
    for o in observations:
        if not o['post_injection']:
            continue
        ready = o['service_ok']
        if method == 'gate':
            ready = (ready and o['monitor_present'] and o['probe_blocked'] and
                     o['age_s'] is not None and o['age_s'] <= fresh_limit and
                     o['observed_level'] is not None and 40 <= o['observed_level'] <= 60)
        elif method != 'connectivity':
            raise ValueError('unknown method')
        count = count + 1 if ready else 0
        if count >= window:
            return o['index']
    return None


def run_trial(scenario, seed, steps=55, interval=0.02):
    if scenario not in SCENARIOS:
        raise ValueError('unknown scenario')
    rng = random.Random(seed)
    start_step = 10
    restore_step = start_step + rng.randint(10, 14)
    policy_restore = restore_step + 8
    rows = []
    with laboratory() as (process, state, plc, hmi, it):
        started = time.monotonic()
        injection_at = None
        for index in range(steps):
            iteration = time.monotonic()
            active = start_step <= index < restore_step
            if index == start_step:
                injection_at = time.monotonic()
            late = start_step <= index < policy_restore
            outage = scenario in ('outage', 'partial_restore', 'combined') and active
            outage = outage or (scenario == 'persistent_outage' and index >= start_step)
            permissive = scenario == 'permissive' and active
            permissive = permissive or (scenario in ('partial_restore', 'combined') and late)
            stale = (scenario == 'stale' and active) or (scenario == 'combined' and late)
            monitor = not (scenario == 'monitor_loss' and active)
            state.configure(outage=outage, permissive=permissive, stale=stale)
            # Setpoint reset is a scheduled harness action shared by comparators.
            if index in (restore_step, policy_restore):
                process.write(50.0)
            status, sample, latency = request(hmi)
            # Real application write used as a containment probe, inside this lab.
            probe_status, probe, _ = request(it, 'POST', '/setpoint', {'value': 80.0})
            truth = process.sample()
            observed_at = time.monotonic()
            age = None if status != 200 else observed_at - sample['measured_at']
            service_ok = status == 200 and latency <= 0.1
            # An unavailable gateway is not evidence that its policy was restored.
            blocked = probe_status == 403
            truth_ok = (service_ok and blocked and age is not None and age <= 0.06
                        and 40 <= truth['level'] <= 60)
            observation = dict(index=index, post_injection=index >= start_step,
                               service_ok=service_ok, monitor_present=monitor,
                               probe_blocked=blocked if monitor else None,
                               age_s=age if monitor else None,
                               observed_level=sample.get('level') if monitor else None)
            rows.append(dict(index=index, elapsed_s=observed_at-started,
                             since_injection_s=None if injection_at is None else observed_at-injection_at,
                             observation=observation, true_level=truth['level'],
                             true_writes=truth['writes'], truth_ok=truth_ok,
                             service_http=status, probe_http=probe_status,
                             write_success=probe_status == 200 and probe.get('written') is True,
                             latency_s=latency, actual_age_s=age,
                             configured_outage=outage, configured_permissive=permissive,
                             configured_stale=stale))
            # Wall-clock execution, never interpreted as a real industrial cycle.
            remaining = interval - (time.monotonic() - iteration)
            if remaining > 0:
                time.sleep(remaining)
    results = []
    for method in ('connectivity', 'gate'):
        declaration = decide([r['observation'] for r in rows], method)
        premature = None if declaration is None else not all(
            r['truth_ok'] for r in rows[declaration-2:declaration+1])
        results.append(dict(scenario=scenario, seed=seed, strategy=method,
                            declaration_s=None if declaration is None else rows[declaration]['since_injection_s'],
                            premature_declaration=premature,
                            unauthorized_writes=sum(r['write_success'] for r in rows),
                            declaration_missing=declaration is None))
    return rows, results, dict(injection_step=start_step, restore_step=restore_step,
                               policy_restore_step=policy_restore)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, default=Path('network_results'))
    parser.add_argument('--seeds', type=int, default=3)
    args = parser.parse_args()
    if args.seeds < 1:
        parser.error('seeds must be positive')
    args.out.mkdir(parents=True, exist_ok=True)
    jobs = [(s, seed) for s in SCENARIOS for seed in range(args.seeds)]
    random.Random(20261105).shuffle(jobs)
    results, schedules = [], []
    with (args.out/'traces.jsonl').open('w') as f:
        for scenario, seed in jobs:
            trace, records, schedule = run_trial(scenario, seed)
            for row in trace:
                f.write(json.dumps(dict(scenario=scenario, seed=seed, **row))+'\n')
            results.extend(records)
            schedules.append(dict(scenario=scenario, seed=seed, **schedule))
            print(f'{scenario} seed {seed} complete', flush=True)
    with (args.out/'runs.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    manifest = dict(stage='loopback HTTP application gateway', seeds=args.seeds,
                    traces=len(jobs), strategy_evaluations=len(results), schedules=schedules,
                    source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    interval_target_s=0.02, service_deadline_s=0.1,
                    fresh_limit_s=0.06, window_samples=3,
                    note='Wall-clock timings vary; seeded fault schedules reproduce.')
    (args.out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')


if __name__ == '__main__':
    main()
