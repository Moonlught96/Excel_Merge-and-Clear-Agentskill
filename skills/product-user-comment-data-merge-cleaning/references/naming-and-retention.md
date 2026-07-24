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

`淘宝`, `天猫`, `京东`, `乐天市场`, `Rakuten`, `rakuten`, `亚马逊`, `Amazon`, `amazon`, `小红书`, `抖音`, `微博`, `B站`, `哔哩哔哩`, `TikTok`, `TTCommentExporter`, `Twitter`, `twitter`, `YouTube`, `youtube`, and `yt-comments`.

Amazon display naming is determined only from registered path/file keywords:

- `亚马逊日本`, `Amazon Japan`, or `amazon.co.jp` -> `亚马逊日本评论数据`.
- `亚马逊美国`, `Amazon USA`, `Amazon US`, or `amazon.com` -> `亚马逊美国评论数据`.
- A generic Amazon keyword without one of the above region keywords -> `亚马逊评论数据`.

Japan and US inputs both use the same `amazon` preprocessing profile. The display source name never selects a profile, creates a different standardized schema, or changes the deterministic header-signature requirement. If one input batch contains more than one detected Amazon region, source naming is ambiguous and the workflow must stop for user confirmation.

Rakuten display naming is determined only from the registered `乐天市场`, `Rakuten`, or `rakuten` path/file keyword and becomes `乐天市场评论数据`. It selects the planned `rakuten` preprocessing route for confirmation, but execution still requires one of the complete ordered Rakuten header signatures. For a Rakuten filename containing its platform keyword, the deterministic product-name parser removes only the platform keyword and outer separators; it preserves a product version token such as `ScreenBar 1` instead of treating it as numeric noise.

When a YouTube input path contains an exact `Shorts` directory segment, classify its display data source as `YouTube Shorts评论数据` before applying the generic YouTube rule. This display-name distinction does not change the shared `youtube` hash namespace.

Twitter file/path keywords `Twitter` or `twitter` deterministically produce `Twitter评论数据` and the planned `twitter` preprocessing route. The display source label does not select the profile by itself: execution still requires the complete registered Twitter/X ordered header signature.

The naming CLI must emit JSON as UTF-8 and remain usable when input filenames contain characters unsupported by the active Windows console code page, including emoji. Console encoding must not change filename parsing or output naming.

If product name or data source is absent or ambiguous, ask the user. Do not use AI or semantic inference to guess it.

Before multi-file merge, show product name, data source, and all four planned filenames: merged `.xlsx`, standardized `.xlsx`, cleaned `.xlsx`, and cleaned `.csv`. Then use the exact prompt from `workflow.md`.

When a registered source name has a planned platform-preprocessing profile, the same confirmation must show the profile name and the fixed statement that the actual branch requires a complete ordered header-signature match after merge. This is a confirmation of the intended deterministic route, not a permission to bypass its signature validation.

返回文件链接时，链接文字必须使用实际完整文件名（含扩展名），不得使用泛化标签。

## Phase Outputs

At the merge checkpoint, return:

- raw merged `.xlsx`;
- merge summary only when needed for verification or explicitly requested.

At the standardization checkpoint, return:

- standardized `.xlsx`;
- standardization summary only when needed for verification or explicitly requested.

Run the standardized-output audit before this checkpoint. When it passes, its `.audit.json` remains an internal current-run intermediate; return it only when the user explicitly requests audit artifacts. When it fails, stop and report the deterministic failure before returning a standardization checkpoint artifact.

After cleaning, the default retained outputs are only:

- cleaned `.xlsx`;
- cleaned first-worksheet `.csv`.

Keep only the final cleaned `.xlsx` and `.csv` by default.

## Audit Outputs

The tools may generate:

- merge `.summary.json`;
- reply-prefix `.summary.json`;
- `.standardized.summary.json`;
- `.audit.json`;
- platform-preprocessing `.summary.json`;
- Twitter/X `.keyword-filter.summary.json`;
- `.deletions.csv`;
- cleaning `.summary.json`.

Retain and return these only when the user explicitly requests audit logs or summaries before cleaning.

## Automatic Intermediate Cleanup

After verifying the final cleaned `.xlsx` and `.csv`:

- run cleanup immediately without a separate user confirmation;
- pass each raw merged, prefix-stripped, platform-preprocessed, standardized, Twitter/X keyword-filtered, audit, deletion-log, and summary path explicitly as an intermediate;
- pass every original input plus final cleaned `.xlsx` and `.csv` as protected paths;
- At least one `--protect` path is mandatory; cleanup refuses to run without protected paths.
- omit cleanup `--summary` by default so cleanup creates no extra retained file;
- keep only audit artifacts requested before cleaning.

Do not delete original input files.

Do not delete the final cleaned `.xlsx` or `.csv`. Do not scan a folder for deletion candidates.

## Existing Output Policy

Existing outputs are rejected by CLI unless `--overwrite` is supplied after explicit confirmation. Never add `--overwrite` merely to make a failed command succeed. First show the exact destination that would be replaced and obtain explicit user approval.
