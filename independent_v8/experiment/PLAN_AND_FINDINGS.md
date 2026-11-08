# Independent process validation and robustness study

## Frozen plan

The protocol and implementation hashes were saved before collecting campaign outcomes. The primary comparison is G3 versus G8+A. Windows 3, 5, 8 and 12, with and without authentication, were fixed in advance; no window was selected as an optimum after seeing results.

The standalone model has two gravity-drained tanks in cascade with nonlinear square-root outflows, PI pump control, saturation, and remote sensor noise. It does not import the original scalar plant or its generator. The existing HMAC verifier is intentionally reused as a fixed control. The new vectorized declaration engine is cross-checked against the unchanged original scalar predicate for every assessment.

The 5,760 observation traces arise from 320 process trajectories crossed with 18 transport/buffer/noise settings. They are not 5,760 independent physical runs. The entire fixed grid is carried together within each of 20 seed blocks.

## Completed campaign

- Full audit: 1,733,760 stored samples; 46,080 assessments; all packet digests, verification verdicts, declarations and outcomes matched.
- Physics checks: exact equilibrium, closed mass conservation, analytic tank-1 drainage, controller saturation / anti-windup, step refinement, and response to a pump disturbance. All six pass.
- Supplemental numerical audit: a separately coded 1 ms Euler solver checks all 320 trajectories without importing the RK4 plant; maximum level difference is 0.004514 units (fixed tolerance 0.1). All pass.
- Measurement-case audit: all 20 G3+A physical-only errors occur with noise sigma 2; the two G8+A physical-only errors occur at zero noise and arise from capture lag after manipulation ends.
- Telemetry interval: 200 ms; RK4 integration: 10 ms; PI update: 20 ms; horizon: 60 virtual seconds.
- Freshness remains 60 ms and service deadline 100 ms. The forward-five outcome now spans one virtual second, so elapsed times and failure rates must not be pooled with the original 20 ms HTTP campaigns.

## Method counts

| Method | Premature / declared | Missing / 5760 | Later / eligible | Median wait (s) |
|---|---:|---:|---:|---:|
| G3 | 2010/2976 | 2784 | 1896/2976 | 0.40 |
| G5 | 1602/2652 | 3108 | 1302/2652 | 0.80 |
| G8 | 1092/2400 | 3360 | 1092/2400 | 1.40 |
| G12 | 1080/2352 | 3408 | 1080/2352 | 2.20 |
| G3+A | 440/1872 | 3888 | 480/1872 | 1.20 |
| G5+A | 342/1826 | 3934 | 306/1826 | 1.80 |
| G8+A | 198/1768 | 3992 | 206/1768 | 3.40 |
| G12+A | 132/1656 | 4104 | 132/1656 | 6.50 |

## Paired primary comparison

Mutual declarations: 1768; G3-only declarations: 1208; G8+A-only: 0; both missing: 2784.
Premature outcomes: 604 improvements and 0 worsenings; difference 34.16 percentage points; conditional 95% seed-block interval [33.26, 35.08].
Later outcomes: 576 improvements and 4 worsenings; difference 32.35 percentage points; conditional interval [27.75, 36.88].
Median paired added wait: 1.50 virtual seconds. The intervals resample 20 seed blocks, 10,000 times, seed 20261107. They do not quantify industrial incidence, process-parameter uncertainty, or hardware uncertainty.

## Findings and limits

MAC rejection of modified and replayed packets transfers, but noise and lag in genuine measurements break the stronger statement that authentication removes every premature declaration within those scenario labels. At W=8, two such declarations remain (one modification, one replay), both at zero noise. Signed captured levels remain above 40 while actual levels cross 0.0079 units below 40. These small-margin, fresh-but-lagged boundary crossings occur after manipulation ends, not from accepting a tampered packet. At W=3, 20 physical-only failures occur at noise sigma 2; matched noise-free traces are not premature. This outcome decomposition is exploratory and does not change the frozen primary outcome.

Under source compromise G8+A is premature in 196/328 declarations; authentication does not establish measurement truth. Larger windows lower premature counts while increasing missing declarations from 3,888 to 4,104 for authenticated W=3 to W=12. The age and transport profiles include settings that cannot satisfy the fixed freshness limit. Their missing declarations are expected fail-closed behavior, not evidence of successful recovery.

The model is an author-implemented research simulation using illustrative SI parameters. It is not a Quanser/SWaT implementation, hardware experiment, independent instrumentation, or externally validated industrial safety model. The local PI loop uses ideal state feedback; Gaussian noise is applied only to remote telemetry. Latency and clocks are virtual. Shadow declarations do not prevent writes or restore control. No independent-evidence gate was added.

## Reproduce

From a fresh extracted package root, install the pinned experiment dependencies and run:

    python independent_v8/experiment/test_plant.py
    python independent_v8/experiment/campaign.py
    python independent_v8/experiment/audit_analyze.py
    python independent_v8/experiment/check_trajectories.py
    python independent_v8/experiment/check_measurement_cases.py
    python independent_v8/experiment/make_outputs.py

The runner overwrites outputs beside itself: use a fresh extraction and retain the delivered evidence. All lab keys are deterministic disposable test keys; packet digests and retained payload fields permit exact reconstruction. This provides computational reproducibility rather than cryptographic provenance. Protocol, source hashes, metadata, compressed raw arrays, outcomes, analysis records, uncertainty estimates, and plot/table regeneration code are included. The bundle is private until the authors choose to archive it publicly.
