# Script And Configuration Reference

## Contents

- [Script Inventory](#script-inventory)
- [Configuration Inventory](#configuration-inventory)
- [Hash Identity Tool Contract](#hash-identity-tool-contract)
- [Command Reference](#command-reference)
- [Runtime Requirements](#runtime-requirements)
- [Validation](#validation)

Run commands from the Skill root directory. The Agent runs these tools for the user; do not ask the user to open a terminal or type commands.

## Script Inventory

- `scripts/output_file_naming.py`: deterministically discover product/source candidates, require the confirmed X data type when the source is Twitter/X, identify any planned registered preprocessing profile, state its required full ordered-header-signature validation, and plan the four output filenames.
- `scripts/inventory_comment_inputs.py`: count logical data rows for only the explicit supplied Excel/CSV files. CSV records containing quoted newlines count as one row; it never scans a folder.
- `scripts/merge_excel_workbooks.py`: merge explicit `.xlsx`, `.xlsm`, and `.csv` inputs into a new raw merged `.xlsx`.
- `scripts/strip_bilibili_reply_prefixes.py`: remove only fixed B站 `回复@xxx：`/`回复 @xxx:` prefixes in a separate workbook.
- `scripts/preprocess_platform_comments.py`: route an exact registered platform header signature through its deterministic preprocessing profile before common standardization; with `--merge-registered-variants`, transform a validated mixed-variant batch into one platform-preprocessed merged workbook.
- `scripts/filter_comments_by_keywords.py`: retain only standardized rows whose `评论内容` contains at least one confirmed literal keyword; used only at the X 推文 post-standardization gate after the user selected `推文`.
- `scripts/hash_id_pseudonymizer.py`: select a worksheet-wide registered account ID or display-name fallback, normalize the value, and compute project/platform/identity-type-isolated HMAC-SHA256 values.
- `scripts/hash_id_project_store.py`: create/load protected project keys; Windows uses current-user DPAPI.
- `scripts/standardize_excel_headers.py`: map fixed aliases, use a confirmed literal `--product-name` fallback only when a source product value is absent or blank, derive `哈希ID`, reorder complete columns, convert configured dates, apply fixed cross-platform rating/likes numeric normalization, and omit non-standard columns.
- `scripts/audit_standardized_comments.py`: verify the fixed standardized schema, source/output row and fixed-mapping consistency, hash-ID format, and nonblank standardized `点赞数` values before cleaning; it never rewrites the workbook.
- `scripts/clean_excel_comments.py`: apply deterministic main-comment, confirmed technical-term, KOL, fixed-word, random-heap, duplicate, and subcomment rules using only the bundled canonical cleaner configuration.
- `scripts/cleanup_intermediate_outputs.py`: delete only explicitly supplied current-run intermediates while protecting inputs and final outputs.
- `scripts/compare_cleaned_workbooks.py`: optional audit-only workbook comparison; it is not part of the default workflow.
- `scripts/csv_excel_compat.py`: text-preserving CSV compatibility shared by the other scripts.
- `scripts/output_path_safety.py`: reject input/output collisions and unconfirmed overwrites, then stage output files for atomic replacement.

## Configuration Inventory

- `config/comment-cleaner.json`: active cleaning thresholds, exact text, fixed contains terms, random-heap thresholds, duplicate policy, subcomment rules, and CSV encoding. Platform profiles are prohibited.
- `config/header-standardizer.json`: exact standard output order, fixed aliases, required/optional columns, and known dropped headers.
- `config/hash-id.json`: platform aliases plus ordered `user_id_headers` and `display_name_headers`; do not add ambiguous identity fields.
- `config/platform-preprocessing.json`: exact platform header signatures and deterministic pre-standardization field operations. Current registered profiles: `amazon-japan`, `amazon-us`, `rakuten`, `twitter`, `twitter-comments`, and `reddit`; `rakuten` has five named exact header variants. `twitter` and `twitter-comments` intentionally share one signature and must be selected explicitly through the user-confirmed X data type.
- In `config/hash-id.json`, `schema_version` must be `2`; schema version `1` is rejected. `config/platform-preprocessing.json` independently requires `schema_version: 1`.
- `algorithm_version` remains `bazhuayu-hash-id-v1`, and this schema migration does not change hash outputs.


## Hash Identity Tool Contract

- Stable account ID is selected first for the whole worksheet when a registered account-ID column contains at least one nonblank value.
- Display-name fallback is allowed only when no registered account-ID column contains any nonblank value.
- The observed literal exporter null marker `None` is treated as blank only while evaluating a stable account-ID column. It does not erase a display name literally equal to `None`.
- The selected header applies to all rows in that worksheet; blank account-ID cells do not fall back row-by-row.
- Display-name hashes include a separate identity domain, so they cannot equal account-ID hashes for the same normalized text.
- The exact registered mappings and priority order are defined in `config/hash-id.json` and documented in `header-standardization.md`.
- Raw account IDs, usernames, and nicknames are read only in memory and remain omitted from outputs, logs, and summaries.
- Comment IDs, parent IDs, URLs, IP fields, `用户身份`, and ambiguous fields are never identity sources.
- Identity selection, normalization, and hashing are deterministic tooling only; do not use AI.
## Command Reference

Every transformation command below requires `--output`. Pass the exact path already shown and confirmed by the naming plan; `--output-dir` alone is not a workflow output contract.

Plan output names:

```powershell
python scripts\output_file_naming.py "<file1.xlsx-or-csv>" "<file2.xlsx-or-csv>"

# For Twitter/X after the user has selected the type:
python scripts\output_file_naming.py "<file1.xlsx-or-csv>" --x-data-type "推文-or-评论"
```

Count explicit input records before reporting a total:

```powershell
python scripts\inventory_comment_inputs.py "<file1.xlsx-or-csv>" "<file2.xlsx-or-csv>"
```

Use the returned `data_rows` value, not a physical text-line count, a folder scan, or a remembered number from an earlier batch.

Merge explicit inputs:

```powershell
python scripts\merge_excel_workbooks.py "<file1.xlsx-or-csv>" "<file2.xlsx-or-csv>" --output "<raw-merged.xlsx>"
```

Strip B站 reply prefixes only when applicable:

```powershell
python scripts\strip_bilibili_reply_prefixes.py "<raw-merged.xlsx>" --output "<reply-prefix-stripped-merged.xlsx>"
```

Preprocess a registered platform only when its exact configured signature applies:

```powershell
python scripts\preprocess_platform_comments.py "<raw-or-prefix-stripped.xlsx>" --platform "amazon-japan-or-amazon-us-or-rakuten-or-twitter-or-twitter-comments-or-reddit" --output "<platform-preprocessed.xlsx>"
```

The command stops rather than guessing when the headers do not match the selected profile. It does not replace the common standardizer or apply a profile to unregistered platforms.

Merge a validated batch of multiple exact variants only after ordinary raw merge stopped with `HeaderMismatchError`:

```powershell
python scripts\preprocess_platform_comments.py "<input-1.xlsx>" "<input-2.xlsx>" --platform "rakuten" --merge-registered-variants --output "<platform-preprocessed-merged.xlsx>"
```

Every input sheet must match one complete variant of the selected profile, and all of those variants must expose the same ordered temporary output columns. The command stops without an output when any signature fails. The platform-preprocessed merged workbook proceeds directly to common standardization; do not run this splitter again on it.

Standardize:

```powershell
python scripts\standardize_excel_headers.py "<input.xlsx-or-csv>" --output "<confirmed-standardized.xlsx>" --platform "<platform>" --project-name "<research-project>" --product-name "<confirmed-product-name>"

# Only when the user confirms this is a new research project:
python scripts\standardize_excel_headers.py "<input.xlsx-or-csv>" --output "<confirmed-standardized.xlsx>" --platform "<platform>" --project-name "<research-project>" --initialize-project --confirm-project-key-creation "<research-project>" --product-name "<confirmed-product-name>"
```

Audit immediately after standardization and before user confirmation or cleaning:

```powershell
python scripts\audit_standardized_comments.py "<confirmed-standardized.xlsx>" --source "<exact-standardization-source.xlsx>" --output "<confirmed-standardized.audit.json>"
```

The audit exits nonzero when a deterministic structural or fixed-mapping equality check fails. It does not inspect or report raw comment content or raw identity values.

X 推文 post-standardization keyword retention, only after the user selected `推文`, the `twitter` profile matched, the standardization audit passed, and the two required X 推文 keyword confirmations completed. It does not apply to the separate `twitter-comments` X 评论 profile, which shares only the confirmed `twitter` hash namespace:

```powershell
python scripts\filter_comments_by_keywords.py "<standardized.xlsx>" --keep-keyword "<keyword1>" --keep-keyword "<keyword2>" --target-header "评论内容" --output "<twitter-keyword-filtered.xlsx>"
```

The command deletes rows whose `评论内容` lacks every confirmed keyword. It uses literal casefolded substring matching only and produces a temporary `.keyword-filter.summary.json` without raw comment text.

Clean without KOL words:

```powershell
python scripts\clean_excel_comments.py "<standardized.xlsx>" --target-header "评论内容" --platform "<confirmed-platform>" --output "<confirmed-cleaned.xlsx>"
```

The cleaner rejects any target header other than `评论内容`; `target_column` is not a supported fallback, even for internal calls.

Clean with confirmed KOL words:

```powershell
python scripts\clean_excel_comments.py "<standardized.xlsx>" --target-header "评论内容" --platform "<confirmed-platform>" --clean-word "<word1>" --clean-word "<word2>" --output "<confirmed-cleaned.xlsx>"
```

Clean with confirmed technical terms and KOL words:

```powershell
python scripts\clean_excel_comments.py "<standardized.xlsx>" --target-header "评论内容" --platform "<confirmed-platform>" --technical-term "<term1>" --technical-term "<term2>" --technical-term "<term3>" --technical-term "<term4>" --clean-word "<word1>" --output "<confirmed-cleaned.xlsx>"
```

Pass `--technical-term` only after the user confirms the complete per-run list. The canonical threshold is 4 distinct literal term matches in `评论内容`; repeated matching of one term counts once. No `--technical-term` option is passed when the user confirms there are no technical terms. These arguments do not create or alter a cleaner configuration file.

Clean up explicit intermediates:

```powershell
python scripts\cleanup_intermediate_outputs.py --intermediate "<raw-merged.xlsx>" --intermediate "<raw-merged.summary.json>" --intermediate "<reply-prefix-stripped-merged.xlsx>" --intermediate "<reply-prefix-stripped-merged.summary.json>" --intermediate "<platform-preprocessed.xlsx>" --intermediate "<platform-preprocessed.summary.json>" --intermediate "<standardized.xlsx>" --intermediate "<standardized.standardized.summary.json>" --intermediate "<standardized.audit.json>" --intermediate "<cleaned.deletions.csv>" --intermediate "<cleaned.summary.json>" --protect "<original-input.xlsx-or-csv>" --protect "<cleaned.xlsx>" --protect "<cleaned.csv>" --final-output "<cleaned.xlsx>" --final-output "<cleaned.csv>"
```

Do not include `--summary` in cleanup unless the user requested a cleanup audit summary before cleaning. Even then, it must not target the final cleaned workbook's `.deletions.csv` or `.summary.json` sidecar path.

At least one `--protect` path is mandatory. Pass every original input and both final cleaned outputs as protected paths. The cleanup CLI also requires exactly one existing final `.xlsx` and one existing final `.csv` through `--final-output`; it verifies both paths are protected before it deletes any intermediate.

Compare two cleaned workbooks only for an explicit audit request:

```powershell
python scripts\compare_cleaned_workbooks.py --left "<left.xlsx>" --right "<right.xlsx>" --output-dir "<comparison-directory>" --comment-column 2
```

Comparison preserves formula text and counts duplicate-row multiplicity. Comparison outputs use the same no-clobber rule as workflow outputs.

Existing outputs are rejected by CLI unless `--overwrite` is supplied after explicit confirmation. For every output that already exists, the CLI also requires one exact `--confirm-overwrite <exact-existing-path>` argument. All examples intentionally omit both flags.

The public preprocessing, standardization, hash-ID, audit, and cleaner commands refuse `--config` paths other than their canonical bundled configurations; do not create temporary per-run configuration files. The public cleaner CLI requires the exact `--target-header "评论内容"` and a nonblank confirmed `--platform`; it never falls back to column 3. Per-run platform-specific cleaner exceptions are prohibited, and canonical URL/link marker terms apply to every platform, including Twitter/X. The one canonical route-specific behavior is `twitter-comments` removal of literal `https://` URL text from `评论内容` only before normal cleaning; it does not access other fields or affect `twitter` X posts. After default cleanup deletes a final `.deletions.csv` or `.summary.json`, the cleaner refuses to regenerate either artifact at the same final output path. `cleanup_intermediate_outputs.py` refuses both final sidecar paths as `--summary` targets and requires the verified final `.xlsx` and `.csv` even when invoked as a Python function.

## Runtime Requirements

- Python 3.10 or newer is required.
- `openpyxl` is required.
- Install portable dependencies with `python -m pip install -r requirements.txt` from the Skill root.
- Use a Python runtime that includes `zoneinfo` timezone data for deterministic Beijing naming.
- When global `python` lacks dependencies, use the Codex bundled Python returned by `load_workspace_dependencies`.
- Automatic initialization and persistent storage of a new hash-ID research project requires Windows DPAPI under the current Windows user. On non-Windows systems, the Skill can load a securely pre-provisioned project key through the documented environment provider but cannot securely initialize and persist a new project key.
- Folder portability means the complete Skill can run outside the repository with its bundled scripts and configuration; it does not mean that a Windows DPAPI-protected project key can be moved to another operating system or Windows user.

## Validation

From the project root during development:

```powershell
python tools\sync_skill_bundle.py --check
python -m unittest discover -s tests
python -m compileall tools skills\product-user-comment-data-merge-cleaning\scripts tests
git diff --check
```

The Skill is ready only when:

- scripts/configuration match the project source;
- all tests pass;
- the Skill directory can be copied to an isolated folder and its bundled standardizer and cleaner still run;
- no original input is modified;
- no AI data judgment has been introduced.
