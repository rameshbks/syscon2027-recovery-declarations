# Release-candidate verification

Executed in an isolated temporary copy of the assembled artifact with Python 3.12 and the versions recorded in verification_environment.json. This is extraction/readback validation in the supplied analysis runtime; downloading/installing the dependencies into a network-clean environment was not tested.

Results:
- 34 retained implementation tests PASS, including changed-packet and missing-strategy corruption checks.
- 6 separate plant tests PASS.
- Original campaign: 27,300 samples and 2,520 assessments audited; regenerated CSV results match all six retained numerical tables exactly.
- Original authenticated window sweep matches the retained W=3/5/8/12 values.
- Held-out campaign: 19,200 samples and 1,440 assessments audited; regenerated analysis.json matches exactly.
- Nonlinear campaign: 1,733,760 samples and 46,080 assessments audited; packet digests, verifier verdicts, original scalar predicates and primary outcomes match. Recomputed analysis.json matches exactly.
- Separately coded 1 ms Euler check passes for all 320 trajectories. Maximum level difference is 0.004514 units, under fixed tolerance 0.1.
- Measurement-case audit confirms 20 noisy G3+A physical-only errors and two zero-noise G8+A lag errors.
- Total retained main-campaign assessments checked: 50,040.
- Full retained-trace reproduction completed in approximately 56 seconds in this runtime; runtime varies by host.
- Numerical Tables IV–VIII and all three selected analytical figure exports were generated separately. The three exported plots were visually inspected.
- Pattern scan of text files and original archive contents found no matching credential tokens, personal email addresses, user-specific paths, or listed corporate identifiers. This is a targeted scan, not a guarantee against every possible disclosure. Disposable lab HMAC keys remain intentionally included.

The first assembly omitted the pilot fixture required by two corruption tests. It was added without changing the test code or frozen scientific sources; the final complete test run passes. The pilot is a fixture, not a new main experiment.

No full HTTP campaign was recollected and no historical result was overwritten. The nonlinear generator was not rerun during packaging; its retained outputs were fully reconstructed and numerically checked. Source hashes for all frozen campaign dependencies and the original ZIP match the retained manifests. No public repository, release, or DOI was created.
