# Script And Configuration Reference

Run commands from the Skill root directory. The Agent runs these tools for the user; do not ask the user to open a terminal or type commands.

## Script Inventory

- `scripts/output_file_naming.py`: deterministically discover product/source candidates and plan the three output names.
- `scripts/merge_excel_workbooks.py`: merge explicit `.xlsx`, `.xlsm`, and `.csv` inputs into a new raw merged `.xlsx`.
- `scripts/strip_bilibili_reply_prefixes.py`: remove only fixed B站 `回复@xxx：`/`回复 @xxx:` prefixes in a separate workbook.
- `scripts/hash_id_pseudonymizer.py`: select a worksheet-wide registered account ID or display-name fallback, normalize the value, and compute project/platform/identity-type-isolated HMAC-SHA256 values.
- `scripts/hash_id_project_store.py`: create/load protected project keys; Windows uses current-user DPAPI.
- `scripts/standardize_excel_headers.py`: map fixed aliases, derive `哈希ID`, reorder complete columns, convert configured dates, and omit non-standard columns.
- `scripts/clean_excel_comments.py`: apply deterministic main-comment, KOL, fixed-word, random-heap, duplicate, and subcomment rules.
- `scripts/cleanup_intermediate_outputs.py`: delete only explicitly supplied current-run intermediates while protecting inputs and final outputs.
- `scripts/compare_cleaned_workbooks.py`: optional audit-only workbook comparison; it is not part of the default workflow.
- `scripts/csv_excel_compat.py`: text-preserving CSV compatibility shared by the other scripts.

## Configuration Inventory

- `config/comment-cleaner.json`: active cleaning thresholds, exact text, fixed contains terms, random-heap thresholds, duplicate policy, subcomment rules, and CSV encoding.
- `config/header-standardizer.json`: exact standard output order, fixed aliases, required/optional columns, and known dropped headers.
- `config/hash-id.json`: platform aliases plus ordered `user_id_headers` and `display_name_headers`; do not add ambiguous identity fields.
- `schema_version` must be `2`; schema version `1` is rejected.
- `algorithm_version` remains `bazhuayu-hash-id-v1`, and this schema migration does not change hash outputs.


## Hash Identity Tool Contract

- Stable account ID is selected first for the whole worksheet.
- Display-name fallback is allowed only when no registered account-ID column exists.
- The selected header applies to all rows in that worksheet; blank account-ID cells do not fall back row-by-row.
- Display-name hashes include a separate identity domain, so they cannot equal account-ID hashes for the same normalized text.
- The exact registered mappings and priority order are defined in `config/hash-id.json` and documented in `header-standardization.md`.
- Raw account IDs, usernames, and nicknames are read only in memory and remain omitted from outputs, logs, and summaries.
- Comment IDs, parent IDs, URLs, IP fields, `用户身份`, and ambiguous fields are never identity sources.
- Identity selection, normalization, and hashing are deterministic tooling only; do not use AI.
## Command Reference

Plan output names:

```powershell
python scripts\output_file_naming.py "<file1.xlsx-or-csv>" "<file2.xlsx-or-csv>"
```

Merge explicit inputs:

```powershell
python scripts\merge_excel_workbooks.py "<file1.xlsx-or-csv>" "<file2.xlsx-or-csv>" --output "<raw-merged.xlsx>"
```

Strip B站 reply prefixes only when applicable:

```powershell
python scripts\strip_bilibili_reply_prefixes.py "<raw-merged.xlsx>" --output "<reply-prefix-stripped-merged.xlsx>"
```

Standardize:

```powershell
python scripts\standardize_excel_headers.py "<input.xlsx-or-csv>" --output "<confirmed-standardized.xlsx>" --platform "<platform>" --project-name "<research-project>"

# Only when the user confirms this is a new research project:
python scripts\standardize_excel_headers.py "<input.xlsx-or-csv>" --output "<confirmed-standardized.xlsx>" --platform "<platform>" --project-name "<research-project>" --initialize-project
```

Clean without KOL words:

```powershell
python scripts\clean_excel_comments.py "<standardized.xlsx>" --target-header "评论内容" --output "<confirmed-cleaned.xlsx>"
```

Clean with confirmed KOL words:

```powershell
python scripts\clean_excel_comments.py "<standardized.xlsx>" --target-header "评论内容" --clean-word "<word1>" --clean-word "<word2>" --output "<confirmed-cleaned.xlsx>"
```

Clean up explicit intermediates:

```powershell
python scripts\cleanup_intermediate_outputs.py --intermediate "<raw-merged.xlsx>" --intermediate "<raw-merged.summary.json>" --intermediate "<reply-prefix-stripped-merged.xlsx>" --intermediate "<reply-prefix-stripped-merged.summary.json>" --intermediate "<standardized.xlsx>" --intermediate "<standardized.standardized.summary.json>" --intermediate "<cleaned.deletions.csv>" --intermediate "<cleaned.summary.json>" --protect "<original-input.xlsx-or-csv>" --protect "<cleaned.xlsx>" --protect "<cleaned.csv>"
```

Do not include `--summary` in cleanup unless the user requested a cleanup audit summary before cleaning.

## Runtime Requirements

- Python 3.10 or newer is recommended.
- `openpyxl` is required.
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
