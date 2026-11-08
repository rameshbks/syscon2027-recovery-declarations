# Stage 5 Analysis of IT and OT Recovery Decisions

IEEE SysCon 2027 research evidence • 5 November 2026

The uploaded Windows campaign reproduces the reported aggregate results. In this controlled experiment, authentication accounts for the avoided unsafe declarations under message modification and replay, while the longer observation window accounts for fewer subsequent failures under intermittent service. The enhanced gate still accepts false measurements from a compromised authorized signer. Its median additional declaration wait is 101.17 ms. These findings support a bounded mechanism-validation study; they do not establish protection of operational industrial systems.

## Verified input and evidence

The archive `stage4_results_full_windows_v1.zip` is 3,725,240 bytes and has SHA-256 `68C5D1B880C5C1E78693262E6CEF03D8E2A7EF6D71D5D25CEC6F982621D31B41`, exactly matching the checksum supplied from Windows. ZIP integrity checks passed. Windows backslashes in archive member names were normalized only in the extracted analysis copy.

The original archive and prior stage source files were not modified. The matching Stage 4 code was used to verify the source fingerprints, all 420 scenario–seed traces, their 27,300 ordered samples, source/session bindings, HMAC and replay verdicts, and exact recomputation of all 2,520 CSV records. The audit heading has been changed to “Campaign Audit” in this derived report only; the frozen Stage 4 audit source remains unchanged.

The 2,520 rows are six paired method assessments of 420 traces: 1,680 primary assessments and 840 ablations. They are not 2,520 independent experiments. Each of fourteen selected labels has thirty seeds. Two labels explicitly repeat other fault mechanics; additional labels share parts of the same synthetic fault model.

## Outcome definitions and denominators

An unsafe declaration fails the direct process-outcome requirement over the trailing three samples: timely actual service, process level in the declared range, restored controller target, and no accepted unauthorized write. Invalid evidence is a separate endpoint. Subsequent failure means a process-outcome failure in the five samples after declaration. It does not necessarily mean a relapse from an initially healthy state.

Every method made 390 declarations and withheld declaration in thirty persistent-outage traces. All 390 declarations per method have complete five-sample follow-up; there are ZERO censored follow-up windows among these declarations. The thirty missing declarations have no safe/unsafe or future-failure label. Missing declaration is not a successful recovery.

| Method | Unsafe | Invalid evidence | No declaration | Subsequent failure | Median declaration time |
|---|---:|---:|---:|---:|---:|
| Connectivity | 180 | 238 | 30 | 205 | 45.04 ms |
| Policy | 90 | 148 | 30 | 115 | 174.16 ms |
| Gate v2 | 90 | 90 | 30 | 115 | 264.92 ms |
| Gate v3 | 30 | 30 | 30 | 31 | 387.50 ms |
| Authentication only | 30 | 30 | 30 | 55 | 285.35 ms |
| Stability only | 90 | 90 | 30 | 91 | 368.28 ms |

Counts are over 420 selected traces; declaration times use the 390 declaring traces. Unsafe declarations among declarations are 90/390 = 23.08% for Gate v2 and 30/390 = 7.69% for Gate v3. Counts divided by all traces are respectively 21.43% and 7.14%, with missing declarations explicitly reported alongside them. These two denominator conventions must not be mixed.

Subsequent-failure proportions among eligible declarations are 115/390 = 29.49% for Gate v2 and 31/390 = 7.95% for Gate v3. Earlier statements that some declared-record follow-up might be censored are not borne out by this uploaded dataset: none is censored here.

## Paired comparisons and uncertainty

Gate v3 avoids sixty unsafe declarations made by Gate v2 and introduces no newly unsafe declaration under the primary trailing-window endpoint. These sixty improvements are exactly the thirty message-modification and thirty replay cases. Both methods remain unsafe in all thirty compromised-source cases.

The observed unsafe-declaration reduction is 66.7% relative to Gate v2's ninety events. It is a reduction in declarations labeled unsafe on shared traces, not a reduction in physical incidents or unauthorized writes. The paired absolute difference among jointly declaring traces is 15.38 percentage points; the all-trace event-count difference is 14.29 percentage points.

For uncertainty calculations, the scenario mix is fixed. A paired seed-block percentile bootstrap resamples thirty seed identifiers with replacement, carrying every retained scenario and both methods together within each sampled block. This preserves method pairing and the dependence of repeated fault mechanics under the same seed identifier. Ten thousand bootstrap replicates use fixed analysis seed 20261105. These intervals describe variation under this selected scenario mixture and finite empirical seed distribution; they do not include uncertainty about which fault types occur in a real plant.

| Paired quantity | Eligible pairs | Estimate | Conditional 95% bootstrap interval |
|---|---:|---:|---:|
| Unsafe-declaration reduction | 390 | 15.38 percentage points | 15.38 to 15.38 |
| Invalid-evidence reduction | 390 | 15.38 percentage points | 15.38 to 15.38 |
| Subsequent-failure reduction | 390 | 21.54 percentage points | 20.26 to 22.56 |
| Mean additional declaration wait | 390 | 157.27 ms | 152.48 to 162.07 ms |
| Median additional declaration wait | 390 | 101.17 ms | 101.04 to 101.40 ms |

**The first two intervals are degenerate and must not be presented as evidence of perfect certainty.** Every seed block has exactly the same primary binary outcome pattern across the selected fault labels. Resampling seeds therefore produces no variation in those differences. More seeds of the same designed cases cannot measure uncertainty over new attack classes, sensor compromises, plants, topologies or model errors. Primary binary findings are better communicated as per-scenario counts, with this limitation explicit. No pooled independence-based significance test is claimed.

`scenario_outcomes.csv` also provides exact two-sided Clopper–Pearson intervals for individual scenario proportions, conditional on treating seeds within that scenario as Bernoulli replications. For reference, 0/30 has an upper 95% bound of about 11.57%, and 30/30 has a lower bound of about 88.43%. These assumption-dependent bounds are not guarantees about industrial deployments and do not correct model or scenario-selection bias.

This is retrospective exploratory analysis after pilot inspection, not a preregistered confirmatory inference. The bootstrap is one dependence-aware sensitivity analysis rather than a complete statistical model of the threat landscape.

## What the ablations establish

| Controlled comparison | Unsafe declarations | Subsequent failures | Interpretation within this model |
|---|---:|---:|---|
| Gate v2 to authentication only | 90 to 30 | 115 to 55 | Authentication avoids the modification and replay cases |
| Gate v2 to stability only | 90 to 90 | 115 to 91 | Waiting longer changes intermittent-fault follow-up, not evidence authenticity |
| Authentication only to Gate v3 | 30 to 30 | 55 to 31 | Longer observation reduces later failures in the intermittent scenario |
| Stability only to Gate v3 | 90 to 30 | 91 to 31 | Authentication supplies the missing protection against unauthenticated modification and replay |

All comparisons share traces. The authenticating verifier uses the laboratory key, session, source, increasing sequence and signed timestamp. Source-compromise trials retain valid authentication while measurements are false. Consequently Gate v3 fails in 30/30 such trials. This negative control must remain in the manuscript.

The intermittent comparison is **25/30 subsequent failures for the short-window methods and 1/30 for the long-window methods**. Every intermittent declaration is initially acceptable under the trailing outcome window. Thus these are genuine later failures under the stated operational predicate, whereas the thirty compromised-source subsequent failures follow already-unsafe declarations. Gate v2 has 25 initially acceptable declarations followed by failure overall; Gate v3 has one.

Pairwise detail matters: Gate v3 improves subsequent-failure status in 85 traces and worsens it in one, giving a net reduction of 84. The worse case is `intermittent`, seed 9. Gate v2's early five-sample follow-up contains no failure; Gate v3 declares later and its next five samples include a failure. The later window changes which future interval is evaluated. The result is not monotonic protection and must not be described as forecasting or guaranteeing recovery stability.

## Declaration timing and operational interpretation

The median of matched Gate v3 minus Gate v2 declaration times is 101.17 ms, with an interquartile range of approximately 100.52 to 103.90 ms. The mean paired increase is 157.27 ms because adversarial and intermittent cases require substantially longer waits. The difference of the two aggregate medians is not the median paired difference; use the paired statistic.

| Scenario | Median extra wait for Gate v3 |
|---|---:|
| Normal operation | 100.76 ms |
| Intermittent service | 366.38 ms |
| Modified evidence | 343.25 ms |
| Replayed evidence | 343.14 ms |
| Compromised source | 101.05 ms |

Five additional past samples explain much of the approximately 100 ms baseline difference at the 20 ms target interval. All times are trace-relative waiting times. Cryptographic processing was retrospective; these values are not HMAC CPU cost, end-to-end authenticated telemetry latency, or measured controller downtime. Persistent-outage cases are excluded from timing comparisons because neither method declares recovery; they are not assigned an artificial finite recovery time.

## Scenario weighting sensitivity

Removing the two explicit duplicate controls, `stale_signed` and `missing_signed`, leaves 360 traces. Unsafe counts remain ninety for Gate v2 and thirty for Gate v3, but the all-trace proportions change from 21.43% to 25.00% and from 7.14% to 8.33%, respectively. The relative event reduction remains 66.7%. This shows why the aggregate percentage depends on the benchmark's weighting, even when the mechanism-level comparison is unchanged. It does not make the remaining labels independent threat families.

## Suggested manuscript wording

“We evaluated four recovery-declaration methods and two ablations on 420 local HTTP traces spanning fourteen selected scenario labels and thirty seeds per label. The authenticated, longer-window gate recorded thirty unsafe declarations, compared with ninety for the existing gate. The sixty avoided declarations occurred in message-modification and replay scenarios. Both methods remained unsafe in all thirty compromised-source trials. The longer observation window reduced subsequent failures in the intermittent scenario from twenty-five to one of thirty trials, while increasing median paired declaration wait by 101.17 ms. These results characterize the mechanisms within the defined simulation and do not demonstrate active protection of an industrial process.”

For methods: “Outcome comparisons were paired by scenario and seed. We reported missing declarations separately and calculated subsequent-failure outcomes only for complete follow-up windows. Conditional uncertainty was assessed using 10,000 paired seed-block bootstrap replicates while holding the scenario set fixed. Degenerate primary binary intervals reflected invariant outcome patterns across seed blocks and were not interpreted as absence of model uncertainty.”

## Limits and submission implications

The primary contribution remains a candidate controlled assessment of evidence-based recovery decisions. Novelty against published secure-recovery and runtime-assurance work is not established by this analysis. The completed figures and table are evidence assets, not a final submission-ready paper.

The experiment uses a scalar simulated process and actual loopback HTTP requests inside a Docker-hosted laboratory. It does not use industrial protocols, hardware PLCs, separate-service authenticated traffic, packet-level failures or validated physical safety models. Signing and verification run retrospectively. Strategies do not control restoration and cannot alter accepted-write counts or process trajectories. Probe writes actively perturb the process. Honest-source observations are trusted by construction; a legitimate signer can lie. The evaluator is separate from coordinator observations but remains part of the same synthetic system and shares service requirements with the gate. Session restart persistence, distributed clocks, key provisioning and rotation, and runtime cryptographic overhead were not evaluated.

The next manuscript work should complete the closest-work and existing-manuscript overlap checks, select claims proportional to this evidence, and determine whether additional implementation realism is needed. More repeated seeds alone will not resolve these limitations.

## Included evidence assets

The package includes audited tables and paired records in CSV, two inspected figures in vector PDF and 300 dpi PNG, a LaTeX table snippet, the derived campaign audit, software/version metadata, and the exact analysis script with unchanged reference sources. The original archive, raw trace copies and disposable audit keys are not duplicated in the deliverable. Reproduction reads the original results ZIP and re-audits it before analysis.
