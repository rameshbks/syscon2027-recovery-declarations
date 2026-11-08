# Held-out schedule validation

This is a new local loopback HTTP campaign in the same scalar process model as Stage 4. It is not an independent implementation, a physical testbed, production validation, or evidence of active recovery enforcement.

The runner writes design_frozen.json, generator_frozen.py, and the source hashes before starting the trial loop. Declaration predicates, HMAC verification, and score functions are imported unchanged from the frozen Stage 4 sources. New seeds are 10000 through 10019, distinct from the original 0 through 29.

## Fixed design

- 12 distinct scenario labels; duplicate stale_signed and missing_signed labels excluded.
- 20 new seeds per label: 240 new HTTP traces and 1,440 paired method assessments.
- 80 samples per trace; target interval 20 ms.
- Windows 3 and 8; freshness 60 ms; service deadline 100 ms.
- Primary outcome: common trailing-three samples; subsequent failure: next five samples.
- Fault onset uniformly selected from steps 6–18; duration 4–24 steps; policy delay 3–15 steps.
- Per-trial intermittent failure probability uniform over 0.2–0.7.
- HMI response-path delay before gateway routing: per sample 85% uniform 0–30 ms, 15% uniform 80–130 ms.
- Actual measured request latency determines deadline compliance.
- Fixed job shuffle; trials run sequentially in the Linux runtime. Wall-clock timings cannot be reproduced exactly.
- Source-compromise, message-modification and replay manipulations retain their original mechanics. A source that signs a false healthy payload remains able to lie.
- The delay changes request latency; it is not packet-level fault injection or a distributed clock model.

## Reproduce

From the package root, using Python 3 with NumPy available:

    python validation/run_validation.py
    python validation/analyze_validation.py

The runner expects the accompanying frozen Stage 4 modules in stage4/. Running again overwrites results, so preserve the original bundle first. The laboratory binds ephemeral loopback ports only. No network ACL, host firewall, container, or global Python changes are required.

## Files

- design_frozen.json: design and hash record saved before data collection
- run_validation.py / generator_frozen.py: generator changes and latency wrapper
- traces.jsonl: every observed sample, request outcome, evidence and verification verdict
- schedules.json: actual random schedules and configured per-sample delays
- audit_keys.json: disposable laboratory keys for replaying evidence verification
- runs.csv: six method records for each new trace
- manifest.json: completed campaign metadata
- analyze_validation.py / analysis.json: independent readback audit and summary
- progress.log: completion log
- CHECKSUMS.json: bundle checksums

Paired confidence intervals resample 20 seed identifiers in blocks, carrying the fixed 12-condition mix together. They quantify conditional schedule variation, not new fault families or physical-process uncertainty. The original Windows benchmark and this Linux campaign must remain separate because both the environment and schedule distributions differ.
