# Script And Configuration Reference

Run commands from the Skill root directory. The Agent runs these tools for the user; do not ask the user to open a terminal or type commands.

## Script Inventory

- `scripts/output_file_naming.py`: deterministically discover product/source candidates and plan the three output names.
- `scripts/merge_excel_workbooks.py`: merge explicit `.xlsx`, `.xlsm`, and `.csv` inputs into a new raw merged `.xlsx`.
- `scripts/strip_bilibili_reply_prefixes.py`: remove only fixed B站 `回复@xxx：`/`回复 @xxx:` prefixes in a separate workbook.
- `scripts/standardize_excel_headers.py`: map fixed aliases, reorder complete columns, convert configured dates, and omit non-standard columns.
- `scripts/clean_excel_comments.py`: apply deterministic main-comment, KOL, fixed-word, random-heap, duplicate, and subcomment rules.
- `scripts/cleanup_intermediate_outputs.py`: delete only explicitly supplied current-run intermediates while protecting inputs and final outputs.
- `scripts/compare_cleaned_workbooks.py`: optional audit-only workbook comparison; it is not part of the default workflow.
- `scripts/csv_excel_compat.py`: text-preserving CSV compatibility shared by the other scripts.

## Configuration Inventory

- `config/comment-cleaner.json`: active cleaning thresholds, exact text, fixed contains terms, random-heap thresholds, duplicate policy, subcomment rules, and CSV encoding.
- `config/header-standardizer.json`: exact standard output order, fixed aliases, required/optional columns, and known dropped headers.

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
python scripts\standardize_excel_headers.py "<input.xlsx-or-csv>" --output "<confirmed-standardized.xlsx>"
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

## Validation

From the project root during development:

```powershell
python tools\sync_skill_bundle.py --check
python -m unittest discover -s tests
python -m compileall tools skills\bazhuayu-excel-cleaning\scripts tests
git diff --check
```

The Skill is ready only when:

- scripts/configuration match the project source;
- all tests pass;
- the Skill directory can be copied to an isolated folder and its bundled standardizer and cleaner still run;
- no original input is modified;
- no AI data judgment has been introduced.
