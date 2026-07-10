# Data Contract And Safety Boundaries

## Deterministic Processing Boundary

- Do not use AI or semantic judgment to map headers, split values, choose columns, reorder rows, delete comments, classify text, or infer dates/products.
- AI may call scripts, verify generated files, and report paths.
- Do not delete comments based on sentiment, quality, relevance, suspected advertising, tone, intent, or language-model judgment.
- Do not use fuzzy or semantic matching unless the user explicitly defines and approves a new rule.
- Do not use the old RPA canvas or a nonexistent Bazhuayu CLI.

## Input Contract

- Supported inputs are `.xlsx`, `.xlsm`, and `.csv`.
- CSV inputs must use the deterministic compatibility layer.
- Preserve CSV cell values as text. Do not infer numeric, date, ID, or timestamp types while loading CSV.
- Process every worksheet in each workbook.
- Treat row 1 as the header row and data as beginning at row 2.
- During merge, B站 reply-prefix stripping, and standardization, load workbook formulas as formulas (`data_only=False`) so missing cached values do not turn formulas into blanks.
- Never modify an original input workbook or CSV file.

## Standard Output Data Contract

The standardized workbook contains exactly these columns in this order:

`评论日期`、`评论内容`、`产品名`、`点赞数`、`子评论数/追评数`、`一级评论`、`二级评论`、`三级评论`

- Move each matched source header and all values below it together. Standardization must not only rename header text.
- Omit all non-configured columns, including nickname, account, ID, IP, profile, and link metadata.
- Missing allowed columns remain present and blank according to the header-standardization reference.
- Do not dynamically infer a fourth or deeper comment level.

## Merge Contract

- Merge only the explicit file list and preserve its order.
- Create a new independent Excel workbook, not a new worksheet in an original workbook.
- Never use an input path as the merge output path.
- Process every worksheet in every supplied workbook.
- Write the first worksheet header once, then append rows from row 2 onward.
- Skip completely blank rows.
- Reject a later worksheet whose header differs from the first header.
- Do not standardize, clean, delete, deduplicate, classify, summarize, or rewrite data during merge.
- Keep original inputs, raw merged output, prefix-stripped output, and standardized output as separate files until the final retention step.

## Cleaning Contract

- Legacy direct cleaning targets column 3 only.
- Standardized cleaning targets the column whose header is `评论内容`.
- Main-comment rules may delete an entire row only when a deterministic configured rule matches.
- Subcomment duplicate and short-text rules clear only the affected subcomment cell; they must not delete the row or modify `评论内容`.
- Deduplicate only within the same worksheet.

## Non-Destructive Guarantees

- Do not overwrite original inputs.
- Do not overwrite the raw merged workbook during reply-prefix stripping or standardization.
- Do not delete original input files.
- Do not delete final cleaned `.xlsx` or `.csv` files.
- Cleanup may delete only explicitly passed current-run intermediate paths.
- Never scan a directory to decide what to delete.
