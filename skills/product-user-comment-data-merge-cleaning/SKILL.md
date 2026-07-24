---
name: product-user-comment-data-merge-cleaning
description: Use when one or more Excel or CSV files containing collected user comments need deterministic processing, pseudonymized standardization, cleaning, or reusable workflow extensions.
---

# 产品用户评论数据合并与清洗 Skill

**功能描述：** 为抓取的大量用户评论数据进行文档合并、标准化和清洗工作，并输出为 XLSX 与 CSV 格式文档。

**输入描述：** 支持任意数量的 `.xlsx`、`.xlsm` 与 `.csv` 用户评论文件；不支持旧版 `.xls`。

## Skill Responsibilities

- Merge only the Excel/CSV files explicitly supplied by the user into a new workbook.
- Route registered platform exports through exact configured preprocessing profiles, then standardize into the fixed output schema and derive project-scoped hash IDs from a worksheet-wide registered account ID or approved display-name fallback.
- Audit every standardized workbook with deterministic structural checks before it can enter the cleaning phase.
- Clean main comments and subcomments with deterministic configuration and scripts only.
- Preserve every original input file and enforce confirmation gates between workflow phases.
- Produce confirmed output filenames, verify artifacts, and remove only current-run intermediates.
- Keep approved base behavior locked unless the user explicitly changes a named rule.

AI may orchestrate scripts and report results. AI must not decide which data row, column, comment, timestamp, or product value should be changed or deleted.

## Trigger Scenarios

Use this Skill when the user:

- provides one or more `.xlsx`, `.xlsm`, or `.csv` comment exports;
- asks to merge comment workbooks or create a total workbook;
- asks to standardize headers, remove sensitive columns, or normalize dates/products;
- asks to clean comments with fixed rules or optional KOL clean words;
- adds a confirmed header alias, fixed clean word, language equivalent, or output rule;
- asks whether the workflow is deterministic, portable, or reusable by another Agent.

Do not use an RPA canvas, a nonexistent Bazhuayu CLI, AI classification, fuzzy matching, or semantic deletion.

## Required References

Read only the references needed for the current phase, but read `workflow.md` and `data-contract.md` before executing a new run.

- Workflow gates and required prompts: [references/workflow.md](references/workflow.md)
- Input/output invariants and prohibited behavior: [references/data-contract.md](references/data-contract.md)
- Standard schema, aliases, date conversion, and product splitting: [references/header-standardization.md](references/header-standardization.md)
- Main-comment and subcomment cleaning rules: [references/cleaning-rules.md](references/cleaning-rules.md)
- Twitter/X confirmed-keyword retention filter: [references/twitter-x-keyword-filter.md](references/twitter-x-keyword-filter.md)
- Filename, output, audit, and retention rules: [references/naming-and-retention.md](references/naming-and-retention.md)
- Script purposes, command shapes, and validation: [references/tool-reference.md](references/tool-reference.md)
- Rules for safe future extensions: [references/extension-policy.md](references/extension-policy.md)
- Confirmed failure modes and deterministic resolutions: [references/known-issues.md](references/known-issues.md)

The executable configuration is in `config/comment-cleaner.json`, `config/header-standardizer.json`, `config/hash-id.json`, and `config/platform-preprocessing.json`.

## Execution Steps

1. Accept only the file paths explicitly provided by the user. Never scan a folder for additional inputs.
2. Confirm the research project name once, then determine the product name and data source by the fixed rules in `references/naming-and-retention.md`, show the merge, standardized, cleaned XLSX, and cleaned CSV filenames, and obtain the required confirmation.
3. For one input file, obtain confirmation that it is the only intended file, then skip merge. For multiple files, first run `scripts/merge_excel_workbooks.py`. If it raises `HeaderMismatchError`, use the mixed-variant path only when the confirmed registered platform profile validates every input sheet against one of its complete exact variants: run `scripts/preprocess_platform_comments.py` with `--merge-registered-variants`, return the resulting platform-preprocessed merged workbook, and wait for merge-completion confirmation. Otherwise stop; do not guess a profile or header mapping.
4. For B站 data, run `scripts/strip_bilibili_reply_prefixes.py` before standardization. In a multi-file run, use the raw merged workbook; in a confirmed single-file run, use the original input as the source. Always write a separate temporary workbook and never overwrite either source. Do not infer or move reply hierarchy.
5. For a platform with a registered exact header signature, run `scripts/preprocess_platform_comments.py` before standardization. This is a deterministic splitter: it applies only that platform profile and writes a separate intermediate workbook. When step 3 already produced a platform-preprocessed merged workbook for mixed exact variants, pass that merged workbook directly to standardization and do not preprocess it a second time. Do not run it for an unregistered legacy platform profile, and never use AI or fuzzy matching to select a profile.
6. Run `scripts/standardize_excel_headers.py` with the confirmed project and platform. When a source product field is absent or blank, pass the product name confirmed at the naming gate through `--product-name`; it is a literal fallback and never overrides a nonblank source product value. Create a protected project key only for a user-confirmed new research project; otherwise load the existing project. The tool selects the first registered stable account-ID column containing a nonblank value and uses a configured display-name fallback only when every registered account-ID column is entirely blank; details and risks are in `references/header-standardization.md` and `references/data-contract.md`.
7. Immediately run `scripts/audit_standardized_comments.py` against the standardized workbook and the exact workbook supplied to standardization. If the audit fails, stop before the user-approval and cleaning gates. If it passes, return the standardized workbook and wait for explicit approval before cleaning.
8. For the registered `twitter` platform only, after standardized-workbook approval ask for the confirmed keep keywords, wait for confirmation that the list is complete, then run `scripts/filter_comments_by_keywords.py`. This temporary deterministic step retains only rows whose `评论内容` contains at least one confirmed literal keyword.
9. Ask whether KOL clean words exist. If words are provided, wait for confirmation that the list is complete. Pass each word as a separate `--clean-word`; pass none when the user says there are no words.
10. Run `scripts/clean_excel_comments.py` against the post-filter `评论内容` column, or the standardized column when no platform-specific filter applies. Do not perform any AI review or rewriting of table values.
11. Verify the cleaned `.xlsx` and `.csv`, then run `scripts/cleanup_intermediate_outputs.py` with explicit intermediate paths and at least one explicit protected path. Protect every original input and both final outputs.
12. Return only the retained outputs defined in `references/naming-and-retention.md`.

Use `scripts/output_file_naming.py` for deterministic naming and `scripts/compare_cleaned_workbooks.py` only when the user explicitly requests a comparison or audit.

CLI output writers reject existing destinations by default. Use `--overwrite` only after the user explicitly confirms replacement; library callers must make the same choice explicitly.

## Output Standard

During the workflow:

- return the raw merged `.xlsx`, or the platform-preprocessed merged `.xlsx` for a validated mixed-variant batch, at the merge checkpoint;
- return the standardized `.xlsx` at the standardization checkpoint;
- use the exact confirmation text defined in `references/workflow.md`.

After successful cleaning, retain and return by default only:

- `YYYYMMDD_产品名_数据来源_清洗后总表.xlsx`
- `YYYYMMDD_产品名_数据来源_清洗后总表.csv`

Retain logs or summaries only when the user requested them before cleaning. Never delete original inputs or final cleaned outputs.

## Bundled Resources

- `scripts/`: deterministic executable workflow tools.
- `config/`: active cleaner and header-mapping configuration.
- `references/`: complete approved workflow and data standards.
- `assets/`: reusable confirmation and rule-extension templates.
- `agents/openai.yaml`: Agent interface metadata.
- `requirements.txt`: portable Python dependency declaration.

This Skill folder is self-contained. It must remain runnable after the entire `product-user-comment-data-merge-cleaning` directory is copied outside this repository. Automatic creation of a new protected hash-ID project requires Windows DPAPI; non-Windows runtimes can load only a securely pre-provisioned environment project key.
