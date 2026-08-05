# Safe Extension Policy

## Contents

- [Locked Base Rules](#locked-base-rules)
- [Adding A Header Alias](#adding-a-header-alias)
- [Adding A Platform Preprocessing Profile](#adding-a-platform-preprocessing-profile)
- [Changing The Standardized Output Audit](#changing-the-standardized-output-audit)
- [Adding A Fixed Delete Word](#adding-a-fixed-delete-word)
- [Changing Cleaner Configuration](#changing-cleaner-configuration)
- [Adding Automation](#adding-automation)
- [Required Change Record](#required-change-record)
- [Validation For Every Extension](#validation-for-every-extension)
- [Adding An Identity Header](#adding-an-identity-header)
- [Adding A Platform-Specific Post-Standardization Filter](#adding-a-platform-specific-post-standardization-filter)

## Locked Base Rules

All confirmed merge, standardization, cleaning, naming, confirmation, output, and retention rules are locked. Do not change a base rule while adding another feature. A base rule may change only when the user explicitly identifies the exact rule to modify.

Examples of locked behavior include:

- deterministic processing without AI data judgment;
- the eleven-column standard output order: `评论日期`, `评论内容`, `产品名`, `电商平台评分`, `用户属性`, `哈希ID`, `点赞数`, `子评论数/追评数`, `一级评论`, `二级评论`, and `三级评论`;
- Chinese main-comment threshold of 7 or fewer characters;
- non-Chinese threshold of 2 or fewer words and unspaced fallback of 4 or fewer characters;
- pure numeric legacy threshold;
- fixed-word append-only behavior preserving `链接`;
- same-worksheet main-comment duplicate policy that keeps the highest `点赞数`, with the last occurrence as the deterministic tie, blank, non-numeric, or missing-column fallback;
- subcomment duplicate/short rules that clear cells instead of deleting rows;
- confirmation gates between merge, standardization, and cleaning;
- default retention of only cleaned `.xlsx` and `.csv`.
- rejection of duplicate input paths and unconfirmed output replacement;
- canonical bundled cleaner configuration only; no external or per-run cleaner JSON;
- platform-specific cleaner exceptions are prohibited; every platform uses the same reviewed canonical fixed-word configuration;
- exact `--confirm-overwrite` confirmation for every existing output replacement;
- mandatory explicit standardized `评论内容` header and confirmed platform for public cleaner CLI calls;
- mandatory explicit final `.xlsx` and `.csv` verification before intermediate cleanup;
- no recreation of default-retention-deleted cleaner `.deletions.csv` or `.summary.json` artifacts at a finalized output path;
- mandatory protected paths for intermediate cleanup;
- formula-aware, duplicate-multiplicity-aware audit comparison.

## Adding A Header Alias

1. Obtain an explicit mapping from the user.
2. Update only the relevant `aliases` list in `config/header-standardizer.json`.
3. Do not change output order, required status, or another alias list unless explicitly requested.
4. Add a representative test proving the new alias maps to the intended standard column with its data intact.
5. Update `references/header-standardization.md`.
6. Synchronize the bundled configuration.

## Adding A Platform Preprocessing Profile

1. Require explicit user confirmation and a representative platform schema; record exact headers only, never raw identity values or comment values.
2. Add one independent profile to `config/platform-preprocessing.json` with a unique namespace, fixed aliases, and either one complete ordered `header_signature` or explicitly named complete ordered variants. Each variant may use only supported deterministic operations. If variants need to participate in `--merge-registered-variants`, their configured temporary output headers must be identical and in the same order.
3. Do not move platform-specific raw transformations into `config/header-standardizer.json`; the common standardizer keeps the locked final schema and hash-output boundary.
4. Specify every source field's fixed order, parser, separator, unmatched-value behavior, and whether it exists only temporarily for hash derivation.
5. Add tests for positive signature detection, unmatched-signature rejection, expected column values, sensitive-field omission, and successful common standardization/hash derivation.
6. Add a deterministic naming and identity configuration only when the user confirms it; do not infer a platform or identity field from values.
7. Treat X 推文 and X 评论 as separate profiles. A shared exporter signature is allowed only when the user first confirms the data-type gate and the configuration forces explicit profile selection. The registered `twitter-comments` profile may reuse `Twitter用户ID`/`Twitter昵称` and the `twitter` hash namespace only because the user explicitly confirmed that identity contract; it must never reuse the X 推文 keep-keyword filter.
8. Update `header-standardization.md`, `workflow.md`, `data-contract.md`, `tool-reference.md`, `naming-and-retention.md`, and the change record.
9. Synchronize the bundled scripts/config and run an isolated Skill copy test.

## Changing The Standardized Output Audit

1. Add a failing test for each new structural check before changing the audit tool.
2. Audit only deterministic structure, configuration, counts, header names, hash format, and fixed source-to-output mapping equality. Never inspect comment semantics or raw identity values.
3. Make failures block standardization approval, KOL collection, and cleaning until the underlying deterministic defect or configuration is corrected.
4. Ensure the audit JSON contains no raw comment content, raw identity values, or project secret material.
5. Record the audit artifact as an explicit cleanup intermediate unless the user requests retention before cleaning.

## Adding A Fixed Delete Word

1. Append the confirmed term; never replace or remove existing terms.
2. Add confirmed equivalents for Chinese, English, Japanese, Korean, Spanish, Thai, and Hindi where applicable.
3. Use the case-insensitive list when case variants must match.
4. For a Han-only fixed term that must be treated as Japanese, add its exact literal mapping to `fixed_term_script_group_overrides`; do not add a Python-only exception list.
5. Do not use AI-generated translations as live cleaning decisions.
6. Add tests for matching and a nearby negative case.
7. Update `references/cleaning-rules.md` and synchronize the bundled configuration.

## Changing Cleaner Configuration

1. Require the user to identify the exact rule change; never create an external or temporary cleaner JSON for one run.
2. Update the canonical root `config/comment-cleaner.json` and its bundled Skill copy together.
3. Platform-specific cleaner exceptions and `platform_profiles` are prohibited. A user-confirmed cleaner rule change applies through the canonical configuration to every platform or must be implemented as a separately confirmed deterministic workflow stage, never by removing base cleaner terms.
4. Update deterministic positive and negative tests, including adjacent values that must not be deleted and a cross-platform assertion proving every platform retains the same fixed terms.
5. Update `references/cleaning-rules.md`, `references/data-contract.md`, and this policy when the execution contract changes.
6. Verify all public preprocessing, standardization, hash-ID, audit, and cleaner CLIs reject every non-canonical `--config` path; verify the cleaner still requires its standardized header/platform arguments.

## Adding Automation

- Put deterministic executable behavior in `scripts/`.
- Put executable configuration in `config/`.
- Put detailed requirements and content standards in `references/`.
- Put reusable templates, forms, and output scaffolds in `assets/`.
- Keep `SKILL.md` concise and link to the relevant reference instead of duplicating long rule lists.
- Preserve standalone operation: bundled scripts must resolve companion modules and configuration relative to the Skill folder.

## Required Change Record

Use `assets/rule-extension-template.md` to record:

- the exact user-confirmed change;
- the rules explicitly kept unchanged;
- affected config, script, reference, and tests;
- isolated Skill verification.

## Validation For Every Extension

- Update or add a test before changing behavior.
- Confirm the test fails for the missing behavior.
- Make the minimal deterministic implementation.
- Run the entire suite, not only the new test.
- Run the Skill bundle consistency check.
- Run the isolated-copy smoke test.
- Do not claim completion while any validation fails.

## Adding An Identity Header

1. Require explicit user confirmation and platform-specific evidence from the exporter schema or a representative platform export.
2. Classify the new field explicitly as a stable account ID or a display-name fallback; never infer identity type from values.
3. Add it only to the matching platform and ordered list in `config/hash-id.json`.
4. Preserve worksheet-wide priority: registered `user_id_headers` containing at least one nonblank value outrank every `display_name_headers` entry; only when all registered account-ID columns are entirely blank may display-name entries follow their configured order.
5. Never register comment IDs, parent IDs, URLs, profile links, IP fields, `用户身份`, source-provided `哈希ID`, or other ambiguous identity fields.
6. A username or nickname may be added only as a platform-confirmed display-name fallback, never as a stable account ID.
7. Add positive, priority, blank, same-name, cross-project, cross-platform, account-ID/display-name separation, and raw-value non-disclosure tests.
8. Update `references/data-contract.md`, `references/header-standardization.md`, `references/tool-reference.md`, and the rule-extension record.
9. Keep every existing merge, cleaning, naming, confirmation, and retention rule unchanged.
10. Synchronize the bundled scripts/config and verify the isolated Skill package.

## Adding A Platform-Specific Post-Standardization Filter

1. Obtain the exact user-confirmed platform scope, stage order, matching predicate, and confirmation prompts.
2. Implement the predicate as a standalone deterministic script in `scripts/`; do not add a natural-language decision path to the common cleaner.
3. Specify whether matching is literal, case-sensitive, case-insensitive, token-boundary-based, or regular-expression-based. Do not leave matching behavior implicit.
4. Place the filter after standardization audit and user approval, and before the common KOL and cleaner stages, unless the user explicitly changes that order.
5. Require an explicit completion confirmation for any user-provided dynamic rule list before execution.
6. Add tests for positive retention, negative deletion, blank/invalid inputs, missing target headers, summary privacy, and output-path safety.
7. Document input/output/cleanup behavior in `workflow.md`, `data-contract.md` or a dedicated reference, `tool-reference.md`, `naming-and-retention.md`, and reusable confirmation assets.
8. Preserve the final naming, KOL, common-cleaner, original-file, and intermediate-cleanup rules unless the user explicitly changes them.
