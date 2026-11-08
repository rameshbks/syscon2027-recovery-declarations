# Publication and version history

Public repository: https://github.com/rameshbks/syscon2027-recovery-declarations

The contributors approved public release under the MIT License. LICENSE contains the approved license text. The review manuscript includes author names and the user confirmed that double-blind review does not apply.

## v1.0.0 and v1.0.1

The earlier releases were published on GitHub. The user supplied the published v1.0.1 source archive for this repair. The earlier Zenodo archive is:
https://doi.org/10.5281/zenodo.24061066

Do not replace that archival record or retarget the historical tags.

Fresh-download inspection confirmed that four CSV files had LF line endings instead of the retained CRLF bytes. Their cell values were unchanged, but byte-level checks failed. LICENSE.proposed had also been renamed to LICENSE without updating the checksum manifest. Citation metadata still identified 1.0.0 and preparation-era README text had not been updated.

## Corrected v1.0.2

This version restores all four CSV files to their original recorded SHA-256 hashes. It preserves the license bytes, updates the checksum filename and publication metadata, and adds .gitattributes so Git does not change tracked bytes. All checksums are regenerated for the corrected release, including intentionally edited documentation. Scientific sources, raw sample values, schedules, predicates and outcome rules are unchanged.

The final table-export verifier compares parsed CSV records rather than platform-specific output line endings. It does not relax byte-level integrity checks on delivered data.

The v1.0.2 version DOI has not yet been issued. CITATION.cff therefore does not attach the older version DOI to the corrected release.

## Publish this fix

1. Copy the corrected tree into the existing local clone; preserve its .git directory. Include .gitattributes, README.md, CITATION.cff, LICENSE and CHECKSUMS.json.
2. In GitHub Desktop, review and commit the corrected files, then Push origin.
3. Verify a fresh clone or GitHub source archive. Run python scripts/check_integrity.py and python scripts/verify_release.py.
4. Only after those checks pass, publish tag v1.0.2 from the corrected commit. Zenodo integration is already enabled.
5. Open the resulting Zenodo record and verify version, authors, MIT license, linked tag, archive files and new version DOI.
6. Use that new version DOI in the manuscript. Keep the older DOI identified as v1.0.1.

To keep citation metadata synchronized without making another code release, Zenodo record metadata can be edited after the version DOI exists. A DOI added to the GitHub default branch afterward does not change the archived tag. Do not claim the old DOI is the new version DOI.
