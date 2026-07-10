# Naming, Output, And Retention

## Filename Standard

Use Beijing date (`Asia/Shanghai`) and this exact pattern:

```text
YYYYMMDD_产品名_数据来源_步骤名
```

The only workflow step names are:

- `合并总表`
- `标准化总表`
- `清洗后总表`

Examples:

```text
20260707_ScreenBar Halo2_淘宝评论数据_合并总表.xlsx
20260707_ScreenBar Halo2_淘宝评论数据_标准化总表.xlsx
20260707_ScreenBar Halo2_淘宝评论数据_清洗后总表.xlsx
20260707_ScreenBar Halo2_淘宝评论数据_清洗后总表.csv
```

Confirm product name and data source once. After confirmation, do not ask again for later output names; replace only the step name.

## Deterministic Name Discovery

Product name may be discovered only from:

- filename text;
- parent folder names;
- configured workbook headers `产品名`, `购买产品`, `商品名称`, or `商品`;
- the fixed `评论日期与产品` parser.

Data source may be discovered only from fixed keywords including:

`淘宝`, `天猫`, `京东`, `小红书`, `抖音`, `微博`, `B站`, `哔哩哔哩`, `TikTok`, `TTCommentExporter`, `YouTube`, `youtube`, and `yt-comments`.

If product name or data source is absent or ambiguous, ask the user. Do not use AI or semantic inference to guess it.

Before multi-file merge, show product name, data source, and all three planned filenames, then use the exact prompt from `workflow.md`.

## Phase Outputs

At the merge checkpoint, return:

- raw merged `.xlsx`;
- merge summary only when needed for verification or explicitly requested.

At the standardization checkpoint, return:

- standardized `.xlsx`;
- standardization summary only when needed for verification or explicitly requested.

After cleaning, the default retained outputs are only:

- cleaned `.xlsx`;
- cleaned first-worksheet `.csv`.

Keep only the final cleaned `.xlsx` and `.csv` by default.

## Audit Outputs

The tools may generate:

- merge `.summary.json`;
- reply-prefix `.summary.json`;
- `.standardized.summary.json`;
- `.deletions.csv`;
- cleaning `.summary.json`.

Retain and return these only when the user explicitly requests audit logs or summaries before cleaning.

## Automatic Intermediate Cleanup

After verifying the final cleaned `.xlsx` and `.csv`:

- run cleanup immediately without a separate user confirmation;
- pass each raw merged, prefix-stripped, standardized, deletion-log, and summary path explicitly as an intermediate;
- pass every original input plus final cleaned `.xlsx` and `.csv` as protected paths;
- omit cleanup `--summary` by default so cleanup creates no extra retained file;
- keep only audit artifacts requested before cleaning.

Do not delete original input files.

Do not delete the final cleaned `.xlsx` or `.csv`. Do not scan a folder for deletion candidates.
