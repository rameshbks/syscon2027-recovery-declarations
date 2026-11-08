# Publication handoff

Status: release candidate, unpublished. No repository or Zenodo DOI has been created.

1. Review the candidate files and proposed MIT license. Confirm all named contributors agree to public release and licensing. Rename LICENSE.proposed to LICENSE only after that decision. Add license: MIT to CITATION.cff at that point.
2. Create the public repository syscon2027-recovery-declarations under the chosen owner. Upload this tree, excluding local environments and verification scratch copies. Keep all frozen data/source bytes intact.
3. Connect that repository to Zenodo before creating its first GitHub release. Zenodo's GitHub integration requires a public repository.
4. Create the reviewed v1.0.0 release. Verify that Zenodo actually creates a public record and a version-specific DOI; a reserved draft DOI alone is not a public archive.
5. Add the real GitHub URL and version DOI to citation metadata and the manuscript. Cite the fixed version DOI for reproducibility. Do not invent identifiers.
6. Retain the checksums for the exact release. If files are changed after archiving, create a new version and cite that version's DOI.

The current official SysCon initial author page does not state a double-blind requirement. This is not proof that a special session has no additional rule; verify the EDAS track instructions before placing identifying repository links in a review manuscript. The same page lists conflicting general and academic deadline information, so use the specific EDAS track deadline rather than inferring an extension.

The manuscript itself is excluded from this code/data release. It still says the artifact has not been publicly archived, which remains accurate. Replace that statement only after the public archive and its contents are verified.

Suggested final wording after publication:
"The source code, recorded traces, outcome data, and reproduction and verification scripts are publicly archived in version 1.0.0 of the research artifact [17]."

Reference [17] must contain the actual authors, artifact title, Zenodo, publication year, version and verified DOI. No placeholder DOI is included in this preparation.

Authoritative workflow references:
- https://help.zenodo.org/docs/github/archive-software/github-upload/
- https://docs.github.com/en/repositories/archiving-a-github-repository/referencing-and-citing-content
- https://zenodo.org/help/versioning
- https://ieeesyscon.org/2027/authors/initial-author-instructions
