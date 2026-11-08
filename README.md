# SysCon 2027 recovery declaration research artifact

Source code and recorded evidence supporting **Evaluating Recovery Declarations in Interconnected IT/OT Systems Under Evidence Manipulation and Communication Failures**, by Ramesh Subramani, Abdul Khadir Mahamed, and Sai Pavan Kumar Mandapaka (New York University).

Version 1.0.2 corrects distribution integrity and publication metadata; experimental results are unchanged.

- Public repository: https://github.com/rameshbks/syscon2027-recovery-declarations
- Earlier archived release v1.0.1: https://doi.org/10.5281/zenodo.24061066
- This corrected v1.0.2: its version-specific Zenodo DOI is pending archival. The earlier DOI does not identify these corrected files.
- License: MIT License, in LICENSE.

See docs/PUBLICATION.md for release history and the final archive check. The manuscript is intentionally excluded.

## What is measured

| Campaign | Recorded traces | Method assessments | Clock and process |
|---|---:|---:|---|
| Original HTTP | 420 | 2,520 | Windows loopback HTTP; scalar process |
| Held-out HTTP | 240 | 1,440 | Linux loopback HTTP; same scalar model, new seeds/schedules |
| Nonlinear robustness | 5,760 observation traces | 46,080 | Virtual time; 320 two-tank trajectories crossed with 18 observation settings |

The combined assessment count is 50,040. Do not pool campaign rates or elapsed times. The 5,760 observation traces are paired crossed observations, not independent physical runs. All declarations are retrospective shadow assessments. Neither the artifact nor a DOI validates physical safety.

## Quick reproduction

Use Python 3.12 in a separate environment. From this repository root:

    python -m venv .venv
    # Linux/macOS:
    . .venv/bin/activate
    # Windows PowerShell instead:
    # .venv/Scripts/Activate.ps1
    python -m pip install -r requirements.txt
    python scripts/verify_release.py

The verifier copies the artifact to a temporary directory, runs 34 retained implementation tests and six physics tests, replays all three campaigns, compares retained numerical results, re-evaluates windows, and runs numerical and measurement-case audits. It removes its temporary copy afterward and prints a PASS summary. Redirect stdout/stderr if a retained execution log is needed. The unit tests bind ephemeral loopback ports. The readback audits contact no external systems. They do not recollect either full HTTP campaign.

Dependencies are pinned to the analysis environment. See docs/VERIFICATION.md for the actual validation performed and limits of installation testing.

## Data and source map

- original_http/stage4_results_full_windows_v1.zip: unchanged, hash-identified 420-trace archive, including raw JSONL, CSV outcomes, schedules and disposable HMAC keys. ZIP paths use Windows backslashes; the analysis safely normalizes extracted paths.
- original_http/analysis/analyze_stage5.py: original readback, statistics and analytical plots. reference_source/ preserves the exact audit implementation. outputs/ contains delivered numerical results.
- original_http/window_sensitivity.json: retained authenticated W=3/5/8/12 sweep on the same original traces. scripts/window_sensitivity.py reproduces it.
- stage4/: frozen laboratory, verifier, predicates and tests. validation_pilot_linux_stage4/ is a test fixture, not an additional main campaign.
- validation/: all 240 held-out traces, outcomes, schedules, design freeze, generator and readback auditor.
- independent_v8/experiment/: separate two-tank plant, frozen grid, 5,760 raw traces in traces.npz, metadata, packet digests, 46,080 outcomes, analysis and figure scripts.
- scripts/reproduce_paper_tables.py: exports numerical Tables IV–VIII and analytical versions of Figures 1–3 from retained computed results.
- docs/: data dictionary, limitations, publication instructions and verification.

The frozen numerical sources remain byte-identical to their hash records. Packaging and export scripts are separate additions. Exact re-running of HTTP latency is impossible; retained trace readback is the reproducibility target for historical numbers. New HTTP campaigns are separate experiments.

## Regenerate analyses separately

Original analysis (output directory must not exist):

    python original_http/analysis/analyze_stage5.py --archive original_http/stage4_results_full_windows_v1.zip --out reproduced_original
    python scripts/window_sensitivity.py --input reproduced_original/input/stage4_results_full_windows_v1 --out reproduced_windows.json

Held-out readback, from repository root (writes validation/analysis.json):

    python validation/analyze_validation.py

Nonlinear readback (writes its analysis outputs):

    python independent_v8/experiment/audit_analyze.py
    python independent_v8/experiment/check_trajectories.py
    python independent_v8/experiment/check_measurement_cases.py
    python independent_v8/experiment/make_outputs.py

Preserve a fresh extraction before running scripts that overwrite outputs. To collect new nonlinear trajectories, run independent_v8/experiment/campaign.py only in a fresh copy, then audit again. To collect new HTTP schedules use validation/run_validation.py in a fresh copy; it overwrites the retained held-out outputs and measured timings will differ.

Regenerate paper tables and selected-scenario figures (new output directory):

    python scripts/reproduce_paper_tables.py --out reproduced_paper_outputs

## Manuscript result map

| Manuscript element | Reproduction input/source |
|---|---|
| Tables I–II | Qualitative scope and literature comparisons; not experiment-generated |
| Table III | Scenario taxonomy; 14 labels × 30 seeds in original archive manifest |
| Tables IV–V | original_http/analysis/outputs/strategy_summary.csv |
| Table VI | original_http/window_sensitivity.json |
| Table VII | validation/analysis.json |
| Table VIII | independent_v8/experiment/analysis.json |
| Figures 1–2 | Original analysis script, scenario counts and paired waiting CSVs |
| Figure 3 | independent_v8/experiment/make_outputs.py, robustness_cells.csv |
| Algorithm 1 | stage4/evidence.py, stage4/stage4_lab.py and stage4/stage4_campaign.py |
| Equations (1)–(2) | independent_v8/experiment/plant.py |

Later manuscript figure typography may differ from the retained analytical plots; the underlying values are reproduced, not a pixel-identical page. The manuscript equations and algorithm are editable document objects and are not experiment outputs.

## Citation and licensing

CITATION.cff identifies version 1.0.2, all three authors, the public repository and the MIT License. Cite the version-specific Zenodo DOI for the exact release used. The earlier v1.0.1 DOI is https://doi.org/10.5281/zenodo.24061066; do not use it to identify v1.0.2. The new version DOI will be assigned when Zenodo archives this corrected release. Dependencies retain their own licenses and are not redistributed here.

Git preserves every tracked file byte-for-byte via .gitattributes, including the original CRLF CSV fixtures. Do not use a spreadsheet or text editor to resave raw evidence files. Check CHECKSUMS.json before verification. Historical campaign reports retain their preparation-era wording; this README and docs/PUBLICATION.md describe current availability.

## Keys and provenance

Audit keys are synthetic disposable experiment fixtures, deliberately retained to verify historical packets. They are not production credentials. Do not deploy them. They make computation replayable; they do not provide independent cryptographic provenance of the experiment. Signed values from a compromised source can still be false.
