# AI Semantic Extension Implementation Plan

> **For agentic workers:** Execute inline using executing-plans; use requesting-code-review for an independent review before release. User approved repair then GitHub push on 2026-09-14.

**Goal:** Repair the supplied semantic review design as an optional post-cleaning extension without changing traditional cleaning rules.

**Architecture:** Read the final eleven-column XLSX as immutable input. Bind complete batches and structured AI evidence to its digest, validate all annotations and second-pass A reviews, then deterministically emit a review workbook and separate XLSX/CSV results. The host Agent performs semantic annotation; scripts do not pretend to contain an AI model.

**Tech Stack:** Python 3.10+, existing openpyxl, unittest, bundled output-path guards; no network/API dependencies or new credential handling.

## Files and boundaries

- `tools/semantic_review_io.py`: typed workbook snapshot, safe literal cells, verified staged artifact generation.
- `tools/semantic_review_contract.py`: policy, manifest, evidence and annotation validation.
- `tools/semantic_review.py`: explicit prepare/show-batch/validate/export/verify CLI.
- `config/semantic-review.json`: fixed semantic schema/families, no product-specific word lists.
- `skills/product-user-comment-data-merge-cleaning/references/ai-semantic-review.md`: workflow, rules, data/retention contract and commands.
- `skills/product-user-comment-data-merge-cleaning/assets/ai-semantic-review/`: reusable annotation prompt and confirmation template.
- `tools/sync_skill_bundle.py`: append new script/config names only.
- `tests/test_semantic_review.py`: synthetic contracts, corruptions, CLI and copied-package end-to-end tests.
- Skill entrypoint and extension policy: a scoped post-cleaning route; existing base paragraphs remain intact and explicitly apply to traditional mode.

## Task 1: Reproduce failures as executable acceptance tests

- [x] Build synthetic workbooks with exact 11 headers and typed cells; never use real user comments.
- [x] Assert absent `tools/semantic_review.py` makes the new CLI tests fail.
- [x] Cover 0/1/60/61/2000/2310/2400 rows, long comments, multi-sheet, blank/full hashes and literal `=` text.

```python
result = subprocess.run([sys.executable, str(cli), 'prepare', '--input', str(source),
    '--output', str(manifest), '--project', 'synthetic', '--platform', 'bilibili',
    '--confirm-traditional-output'], capture_output=True)
self.assertEqual(0, result.returncode, result.stderr)
```

## Task 2: Implement source-bound deterministic preparation

- [x] Snapshot source headers, sheet order, row keys, values, cell types and formats; reject invalid schemas and hashes while accepting empty hashes.
- [x] Include full source text, verified resource digests, runtime terms and batches of at most 60 in the manifest.
- [x] Use stable row keys based on sheet index and physical row, not historical standardized row numbers.
- [x] On every subsequent operation regenerate the expected manifest from source and parameters and compare it exactly.

## Task 3: Implement strict annotation and review validation

- [x] Accept only explicit annotation paths; require one exact result per declared batch, correct run ID, ordered row coverage, model/prompt provenance, typed fields, and quoted source evidence.
- [x] K1–K5 override A; R1 records consecutive function/effect evidence pairs (at least two to represent a chain), not a permanent zero column. This is a descriptive signal, not independent proof of fraud.
- [x] R2 is deterministic count of distinct confirmed runtime terms; R3 needs at least three different nonempty full keys, source-bound member evidence, and same-account pairs alone cannot authorize A.
- [x] Require independent full-text A review records bound to annotation digests before export; keep/uncertain review downgrades A to B, delete requires no K and supported family evidence.

## Task 4: Implement verified artifact output

- [x] Preserve all 11 original fields and types for retained rows; append AI类别/清洗处理/保留原因 only in AI output.
- [x] Emit review workbook with all rows, A candidates, computed groups and computed summary; do not copy any historical sample conclusions.
- [x] Preflight every explicit destination, preserve input/artifact paths, stage all artifacts and verify them before promoting any; retain each file's atomic replacement guarantee without claiming crash-atomic multi-file transactions.
- [x] Verify every output field against input and validated annotations, and every CSV field against the defined first-sheet serialization.

## Task 5: Package and release

- [x] Document optional explicit AI route, confirmations, full-text prompt, model limitations, source untrusted-data boundary and separate AI artifact retention. Do not recreate old traditional logs.
- [x] Synchronize additions; preserve all preexisting script/config bytes.
- [x] Run `python -m unittest discover -s tests`, `python tools/sync_skill_bundle.py --check` and Skill validator.
- [x] Copy the complete Skill into a temporary directory and run prepare/annotate synthetic fixture/export/verify from that copy.
- [x] Obtain independent code review, resolve important findings and rerun tests.
- [ ] Release step after this document is committed: push only exact task files on `codex/ai-semantic-cleaning-extension`, without force or unrelated dirty changes; verify the remote commit.

## Verification interpretation

Engineering tests prove schema, evidence plumbing and file integrity, not AI classification accuracy. No live comment data is sent to a model or GitHub during implementation. Classification performance remains unmeasured until a user-authorized, human-labeled evaluation is run.
