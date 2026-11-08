"""Verify HMAC decisions and recompute outcomes from saved Stage 4 traces."""
import argparse
import csv
import json
from collections import defaultdict, Counter
from pathlib import Path
from stage4_campaign import SCENARIOS, STRATEGIES, PRIMARY, evaluate, fingerprint


def audit(directory):
    m=json.loads((directory/'manifest.json').read_text())
    if m['status']!='completed' or m['hashes']!=fingerprint():
        raise ValueError('incomplete campaign or changed source hashes')
    keys=json.loads((directory/'audit_keys.json').read_text())
    traces=defaultdict(list)
    for line in (directory/'traces.jsonl').read_text().splitlines():
        r=json.loads(line)
        traces[(r['scenario'],r['seed'])].append(r)
    expected={(s,seed) for s in SCENARIOS for seed in range(m['seeds'])}
    if set(traces)!=expected:
        raise ValueError('scenario/seed coverage mismatch')
    target={}
    counts=Counter()
    for (s,seed),trace in traces.items():
        if [r['index'] for r in trace]!=list(range(m['steps'])):
            raise ValueError('trace steps missing, duplicated or out of order')
        session=f'stage4:{s}:{seed}'
        if any(r['session']!=session for r in trace):
            raise ValueError('session metadata mismatch')
        records,checks=evaluate(trace,bytes.fromhex(keys[session]),session,m['stability_window'])
        if checks!=[r['verification'] for r in trace]:
            raise ValueError('saved authentication decisions disagree with HMAC replay')
        for row,check in zip(trace,checks):
            if row['observation']['post_injection']:
                counts[check['reason']]+=1
        for r in records:
            r.update(scenario=s,seed=seed)
            target[(s,seed,r['strategy'])]={k:'' if v is None else str(v) for k,v in r.items()}
    with (directory/'runs.csv').open(newline='') as f:
        rows=list(csv.DictReader(f))
    if len(rows)!=len(expected)*len(STRATEGIES):
        raise ValueError('evaluation count mismatch')
    seen=set()
    for r in rows:
        key=(r['scenario'],int(r['seed']),r['strategy'])
        if key in seen or key not in target or r!=target[key]:
            raise ValueError('duplicate or inconsistent CSV outcome')
        seen.add(key)
    if m['trials']!=len(expected) or m['total_strategy_evaluations']!=len(rows) or m['completed_trials']!=len(expected):
        raise ValueError('manifest count mismatch')
    return rows,counts,len(expected)


def report(directory):
    rows,counts,n=audit(directory)
    lines=['# Stage 4 Pilot Audit','',f'Passed: {n} HTTP traces and {len(rows)} strategy records.',
           'Source fingerprints, coverage, ordered samples, session binding, HMAC/replay decisions and CSV recomputation matched.','',
           '| Strategy | Role | Evaluations | Unsafe | Invalid evidence | No declaration | Future failure |',
           '|---|---|---:|---:|---:|---:|---:|']
    count=lambda group,f:sum(r[f]=='True' for r in group)
    for strategy in STRATEGIES:
        group=[r for r in rows if r['strategy']==strategy]
        values=[str(count(group,f)) for f in ('unsafe_declaration','invalid_evidence_declaration','declaration_missing','post_declaration_failure')]
        lines.append('| '+strategy+' | '+('primary' if strategy in PRIMARY else 'ablation')+' | '+str(len(group))+' | '+' | '.join(values)+' |')
    lines+=['','Counts use all scenario–seed trials as denominator. Missing declarations have no unsafe/safe outcome label; censored follow-up is not counted as success.','',
            '| Scenario | Gate v2 unsafe | Gate v3 unsafe | Gate v3 missing |',
            '|---|---:|---:|---:|']
    for s in SCENARIOS:
        a=[r for r in rows if r['scenario']==s and r['strategy']=='gate_v2']
        b=[r for r in rows if r['scenario']==s and r['strategy']=='gate_v3']
        lines.append(f"| {s} | {count(a,'unsafe_declaration')}/{len(a)} | {count(b,'unsafe_declaration')}/{len(b)} | {count(b,'declaration_missing')}/{len(b)} |")
    lines+=['','Post-injection authentication verdict counts: `'+json.dumps(dict(counts),sort_keys=True)+'`.','',
            'This is a controlled mechanism-validation pilot, not evidence of industrial protection. HMAC checks run retrospectively on recorded local HTTP evidence, using laboratory-only keys. Source-compromise scenarios deliberately permit a legitimate signer to lie. The sustained observation window uses past samples and cannot guarantee future availability.','',
            'The stale_signed and missing_signed scenarios duplicate the respective stale and monitor_loss fault mechanics to make authentication controls explicit; they are not additional independent fault classes. Primary and ablation results share traces and must be analyzed as paired observations.']
    return '\n'.join(lines)+'\n'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--results',type=Path,required=True)
    p.add_argument('--report',type=Path)
    a=p.parse_args()
    text=report(a.results)
    if a.report:
        with a.report.open('x',encoding='utf-8') as f:
            f.write(text)
    print(text)


if __name__=='__main__':
    main()
