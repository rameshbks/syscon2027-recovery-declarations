> Historical analysis-package instructions. For the assembled release layout and verification entry point, start with the repository-root README.md.

# Stage 5 Statistical Analysis Package

The analysis is complete; no campaign rerun is needed. Start with `Stage5_Analysis_Report.md` and `outputs/VERIFIED_CAMPAIGN_AUDIT.md`.

## What is included

- `outputs/strategy_summary.csv`: all six strategies, explicit denominators, missing outcomes and timing summaries.
- `outputs/scenario_outcomes.csv`: per-scenario counts and assumption-dependent exact binomial intervals.
- `outputs/paired_gate_v2_gate_v3.csv`: matched scenario–seed outcomes and extra wait.
- `outputs/paired_intervals.csv`: conditional seed-block bootstrap intervals and degeneracy flags.
- `outputs/latency_by_scenario.csv`: paired timing medians, means and interquartile ranges.
- `outputs/worsened_followup_cases.csv`: the one worse follow-up result, intermittent seed 9.
- `outputs/scenario_weight_sensitivity.csv`: exclusion of the two explicit duplicate controls.
- `outputs/figure1_scenario_outcomes.pdf` and `.png`: scenario-level outcome counts.
- `outputs/figure2_paired_wait.pdf` and `.png`: additional declaration wait, with interquartile ranges.
- `outputs/ieee_results_table.tex`: editable full-width LaTeX table snippet. Check placement in the actual conference template.
- `outputs/analysis_manifest.json`: input hash, analysis source hash, parameters, outcomes and software versions.
- `reference_source/`: unchanged Stage 4 code used for outcome and HMAC audit.

Figures have been visually inspected. PDF figures are vector exports; PNGs are 300 dpi. Tables and figures do not imply journal or conference acceptance, and manuscript novelty checks remain outstanding.

## Reproduce in a separate environment

Keep the original results archive unchanged. Python 3.12 and the versions in `requirements-analysis.txt` reproduce the numerical environment used here. This analysis uses scientific packages not included in the earlier standard-library-only Docker image. Use a new environment rather than installing them into an existing research environment.

Example PowerShell commands from the extracted Stage 5 package directory:

```powershell
py -3.12 -m venv .venv-stage5
.\.venv-stage5\Scripts\python.exe -m pip install -r requirements-analysis.txt
.\.venv-stage5\Scripts\python.exe analyze_stage5.py --archive "C:\path\to\stage4_results_full_windows_v1.zip" --out analysis_reproduced_v1
```

Replace the placeholder archive path with the actual preserved ZIP location. The output directory must not exist. The script normalizes Windows archive path separators in its extracted copy, checks the recorded ZIP SHA-256, repeats the Stage 4 audit, then generates the CSV tables and figures. Its `input` subdirectory contains extracted trace data and disposable laboratory audit keys; preserve or manage that copy as research evidence. It does not alter the original ZIP.

The narrative report is reviewed prose accompanying the computed outputs, rather than an automatically regenerated template. PDF metadata timestamps and plot font rendering can vary by host even when numerical results agree. Compare numerical tables and source fingerprints rather than ZIP or PDF byte equality.

## Interpretation rules

The six methods share each trace. Bootstrap resampling keeps paired seed blocks and a fixed scenario mix. Primary binary intervals collapse because the engineered per-scenario outcome pattern is identical across seeds; do not interpret this as domain-wide certainty. There are 390 declarations with complete future follow-up and thirty missing declarations per method. All primary comparisons are exploratory and conditional on this simulation.

No additional full campaign was executed, and no Stage 4 result was overwritten. The uploaded source archive is already preserved separately; it is intentionally not repackaged here.
