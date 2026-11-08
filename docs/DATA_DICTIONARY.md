# Data dictionary

## HTTP campaigns

Each traces.jsonl record belongs to (scenario, seed, session, index). Observation fields are the evidence visible to declaration methods; ground_truth fields are direct evaluator state in the same synthetic harness. packet retains the signed envelope, and verification records the verdict. audit_keys.json maps synthetic session IDs to disposable laboratory keys. runs.csv has one row per method per trace; declaration_missing, unsafe_declaration, invalid_evidence_declaration, post_declaration_failure and followup_censored have distinct meanings. A missing outcome is not a successful recovery.

The original archive has 27,300 samples (420 × 65). Held-out validation has 19,200 samples (240 × 80). HTTP wall-clock timestamps and per-request latency were measured on the generating host. Seeds reproduce schedules, not operating-system timing.

## Nonlinear traces.npz

All arrays are numeric and can be read with numpy.load(..., allow_pickle=False). The main arrays have shape (5760, 301); time_s has 301 virtual timestamps. metadata.json aligns observation-trace IDs with scenario, seed, fault duration, transport, buffer and noise settings.

- level: actual tank-2 level, 100 times height in metres.
- capture_level: genuine level at capture time.
- noisy_level: remote captured level after observation noise.
- latency: simulated transport, seconds.
- age: capture age, seconds, including buffering and delayed-evidence faults.
- service, policy, post, active: service status, blocked policy probe, post-injection flag and active fault mask.
- truth: evaluator acceptability under the frozen outcome rules.
- manipulated: synthetic packet/payload manipulation flag.
- auth_ok: retained authentication verdict.
- packet_digests.json: per-trace digest of reconstructed ordered envelopes.
- outcomes.csv: 5,760 traces × eight gate configurations = 46,080 records.
- analysis_records.csv.gz: joined outcome and factor records.

The gate family uses W=3,5,8,12 with and without authentication. A declaration is premature if any of the trailing three actual samples is unacceptable; a later failure uses the next five. The latter spans one virtual second here, unlike the original HTTP timing. Missing declarations and censored follow-up are separate outcomes.
