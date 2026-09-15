# AI Semantic Extension Release Verification

Verified on 2026-09-15 (Asia/Shanghai). User authorized repair then GitHub push, with traditional cleaning unchanged and AI review as an optional subsequent stage.

## Delivered

- Portable post-cleaning prepare/show-batch/validate/export/verify commands.
- Full-text, source/policy/prompt-bound batches, complete typed annotation/evidence validation and A-candidate second-pass review binding.
- Real R1 evidence, deterministic R2 counts and source-bound R3 groups using at least three different nonempty full pseudonymous keys.
- Independent review XLSX and AI result XLSX/CSV with all-field checks, typed cell/formula preservation, protected original/final paths and confirmed atomic per-file replacement.
- Scoped Skill routing, fixed semantic configuration, full prompt/confirmation assets, workflow/data/retention contracts and synthetic tests.
- No changes to existing traditional executable scripts/configuration, no historical comment data or credentials in the release.

## Evidence

- Before implementation, all 10 initial extension tests failed because the CLI was absent.
- An independent code review reproduced the generated-empty-string XLSX round-trip mismatch. It was fixed by writing generated blanks as actual blank cells, and export/corruption tests passed afterward.
- Additional tests exposed absent smaller-batch support and finalized-traditional-log output protection; both were implemented and passed.
- Fresh complete suite: **286 tests, OK**, including 14 extension tests and the existing 272 tests. Expected argparse errors printed by negative tests do not represent suite failures.
- `tools/sync_skill_bundle.py --check`: synchronized.
- Official `skill-creator/scripts/quick_validate.py`: Skill is valid. PyYAML was installed only in an ignored local validation-dependency directory; it is not a new runtime dependency of this extension.
- Full-Skill isolated-copy test executed prepare, validation rejection, export and verify outside the repository source path.
- Synthetic boundary coverage includes 0/1/60/61/2000/2310/2400 rows, multiple sheets, blank hashes, long comments, typed dates/formulas/literal equals text, missing/duplicate/corrupted annotations, stale reviews, K protection, R1/R3 evidence, all 14 final fields and protected output paths.

## Limitations and non-claims

Engineering verification does not establish AI classification accuracy. No real user comments were cleaned or sent to a model for this implementation, and no precision/recall or three-platform validation claim is made. The host Agent supplies semantic annotations; these scripts do not include an AI model/API client. Reviewer identity/full-text flags are explicit attestations, not cryptographic proof a human reviewed the data.

An additional fresh-agent workflow exercise could not run because that agent hit its usage limit. It is not counted as passed. Independent code review and deterministic copied-package execution did complete.

CSV represents the first worksheet only. XLSX retains all sheets. Multi-file promotion is verified before replacement but is not crash-atomic across three files; incomplete publication must never be reported as successful.

## Git publication boundary

Publish only this extension's explicit file set, based on the existing remote technical-rule revision `bd75102eab89660653b026d212f3d74ab291c5cf`. Exclude three unrelated local documentation commits and all unrelated dirty/untracked files. A release branch push is not a merge into main. Source datasets, runtime manifests, annotations, review records, local dependencies and the original supplied data-bearing Markdown are not committed.
