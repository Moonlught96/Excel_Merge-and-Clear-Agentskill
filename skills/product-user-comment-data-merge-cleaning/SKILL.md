---
name: product-user-comment-data-merge-cleaning
description: Use when one or more Excel or CSV files containing collected user comments need deterministic processing, pseudonymized standardization, cleaning, or reusable workflow extensions.
---

# 产品用户评论数据合并与清洗 Skill

**功能描述：** 为抓取的大量用户评论数据进行文档合并、标准化和清洗工作，并输出为 XLSX 与 CSV 格式文档。

**输入描述：** 目前输入不受限制，支持 Excel 与 CSV 文件。

## Skill Responsibilities

- Merge only the Excel/CSV files explicitly supplied by the user into a new workbook.
- Standardize platform-specific headers, derive project-scoped hash IDs from a worksheet-wide registered account ID or approved display-name fallback, and move complete columns into the fixed output schema.
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
- Filename, output, audit, and retention rules: [references/naming-and-retention.md](references/naming-and-retention.md)
- Script purposes, command shapes, and validation: [references/tool-reference.md](references/tool-reference.md)
- Rules for safe future extensions: [references/extension-policy.md](references/extension-policy.md)
- Confirmed failure modes and deterministic resolutions: [references/known-issues.md](references/known-issues.md)

The executable configuration is in `config/comment-cleaner.json`, `config/header-standardizer.json`, and `config/hash-id.json`.

## Execution Steps

1. Accept only the file paths explicitly provided by the user. Never scan a folder for additional inputs.
2. Confirm the research project name once, then determine the product name and data source by the fixed rules in `references/naming-and-retention.md`, show all planned output filenames, and obtain the required confirmation.
3. For one input file, obtain confirmation that it is the only intended file, then skip merge. For multiple files, run `scripts/merge_excel_workbooks.py`, return the raw merged workbook, and wait for merge-completion confirmation.
4. For B站 data, run `scripts/strip_bilibili_reply_prefixes.py` before standardization. In a multi-file run, use the raw merged workbook; in a confirmed single-file run, use the original input as the source. Always write a separate temporary workbook and never overwrite either source. Do not infer or move reply hierarchy.
5. Run `scripts/standardize_excel_headers.py` with the confirmed project and platform. Create a protected project key only for a user-confirmed new research project; otherwise load the existing project. The tool selects the first registered stable account-ID column containing a nonblank value and uses a configured display-name fallback only when every registered account-ID column is entirely blank; details and risks are in `references/header-standardization.md` and `references/data-contract.md`. Return the standardized workbook and wait for explicit approval before cleaning.
6. Ask whether KOL clean words exist. If words are provided, wait for confirmation that the list is complete. Pass each word as a separate `--clean-word`; pass none when the user says there are no words.
7. Run `scripts/clean_excel_comments.py` against the standardized `评论内容` column. Do not perform any AI review or rewriting of table values.
8. Verify the cleaned `.xlsx` and `.csv`, then run `scripts/cleanup_intermediate_outputs.py` with explicit intermediate and protected paths.
9. Return only the retained outputs defined in `references/naming-and-retention.md`.

Use `scripts/output_file_naming.py` for deterministic naming and `scripts/compare_cleaned_workbooks.py` only when the user explicitly requests a comparison or audit.

## Output Standard

During the workflow:

- return the raw merged `.xlsx` at the merge checkpoint;
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

This Skill folder is self-contained. It must remain runnable after the entire `product-user-comment-data-merge-cleaning` directory is copied outside this repository. Automatic creation of a new protected hash-ID project requires Windows DPAPI; non-Windows runtimes can load only a securely pre-provisioned environment project key.
