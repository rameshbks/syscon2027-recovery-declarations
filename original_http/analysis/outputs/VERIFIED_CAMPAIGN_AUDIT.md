# Stage 4 Campaign Audit

Passed: 420 HTTP traces and 2520 strategy records.
Source fingerprints, coverage, ordered samples, session binding, HMAC/replay decisions and CSV recomputation matched.

| Strategy | Role | Evaluations | Unsafe | Invalid evidence | No declaration | Future failure |
|---|---|---:|---:|---:|---:|---:|
| connectivity | primary | 420 | 180 | 238 | 30 | 205 |
| policy | primary | 420 | 90 | 148 | 30 | 115 |
| gate_v2 | primary | 420 | 90 | 90 | 30 | 115 |
| gate_v3 | primary | 420 | 30 | 30 | 30 | 31 |
| auth_only | ablation | 420 | 30 | 30 | 30 | 55 |
| stability_only | ablation | 420 | 90 | 90 | 30 | 91 |

Counts use all scenario–seed trials as denominator. Missing declarations have no unsafe/safe outcome label; censored follow-up is not counted as success.

| Scenario | Gate v2 unsafe | Gate v3 unsafe | Gate v3 missing |
|---|---:|---:|---:|
| normal | 0/30 | 0/30 | 0/30 |
| permissive | 0/30 | 0/30 | 0/30 |
| outage | 0/30 | 0/30 | 0/30 |
| stale | 0/30 | 0/30 | 0/30 |
| partial_restore | 0/30 | 0/30 | 0/30 |
| monitor_loss | 0/30 | 0/30 | 0/30 |
| combined | 0/30 | 0/30 | 0/30 |
| persistent_outage | 0/30 | 0/30 | 30/30 |
| intermittent | 0/30 | 0/30 | 0/30 |
| misleading_evidence | 30/30 | 0/30 | 0/30 |
| replay_evidence | 30/30 | 0/30 | 0/30 |
| stale_signed | 0/30 | 0/30 | 0/30 |
| missing_signed | 0/30 | 0/30 | 0/30 |
| source_compromise | 30/30 | 30/30 | 0/30 |

Post-injection authentication verdict counts: `{"accepted": 20831, "age": 841, "mac": 365, "missing": 698, "replay": 365}`.

This is a controlled mechanism-validation pilot, not evidence of industrial protection. HMAC checks run retrospectively on recorded local HTTP evidence, using laboratory-only keys. Source-compromise scenarios deliberately permit a legitimate signer to lie. The sustained observation window uses past samples and cannot guarantee future availability.

The stale_signed and missing_signed scenarios duplicate the respective stale and monitor_loss fault mechanics to make authentication controls explicit; they are not additional independent fault classes. Primary and ablation results share traces and must be analyzed as paired observations.
