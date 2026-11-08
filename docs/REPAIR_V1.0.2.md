# v1.0.2 distribution repair

The uploaded v1.0.1 source ZIP had four CSV byte mismatches and one missing checksum filename. All four CSVs were restored to their original manifest SHA-256 hashes and separately compared with the retained original research package. Cell values and experimental findings are unchanged.

| File | Recovery |
|---|---|
| validation/runs.csv | Exact original bytes restored |
| independent_v8/experiment/outcomes.csv | Exact original bytes restored |
| independent_v8/experiment/robustness_cells.csv | Exact original bytes restored |
| stage4/validation_pilot_linux_stage4/runs.csv | Exact original bytes restored |

LICENSE has the exact hash previously recorded for LICENSE.proposed; only its manifest name needed correction. README.md, CITATION.cff, docs/PUBLICATION.md and current provenance metadata now identify the public repository, MIT license, corrected version and the earlier archive separately. The new version DOI is pending and is not fabricated.

.gitattributes disables text conversion for all tracked files, protecting source fingerprints as well as CSV checksums. The final table-export comparison uses CSV records so regenerated output line endings can differ by operating system; delivered file integrity still uses exact SHA-256 checks.

The checksum manifest is regenerated for all intentionally edited documentation, new attributes and the verifier update. Frozen scientific sources, schedules and sample values remain unchanged.

A fresh Git clone with core.autocrlf=true and core.eol=crlf passes all distributed checksums. Full reproduction results are recorded in docs/v1.0.2_verification.log. The initial dependency runtime is reused; a new network dependency installation is not part of this repair.

Historical v1.0.0/v1.0.1 tags and Zenodo records must remain untouched. Publish the corrected commit as v1.0.2, verify its newly issued version DOI and cite that DOI in the manuscript.
