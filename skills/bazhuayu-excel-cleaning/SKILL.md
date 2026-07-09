---
name: bazhuayu-excel-cleaning
description: Deterministic cleaning workflow for Bazhuayu/Octoparse exported Excel or CSV comment tables. Use when the user asks to clean a spreadsheet file, process Bazhuayu social-media comment exports, merge explicit files, preserve fixed deletion rules, or add features without changing the approved base cleaning behavior.
---

# Bazhuayu Excel Cleaning

## Purpose

Use this skill to standardize headers, merge, and clean Bazhuayu/Octoparse exported Excel or CSV comment tables with deterministic tool rules. Do not use AI to decide whether a row should be reordered, merged, or deleted.

The approved base behavior is locked. Do not change any base rule unless the user explicitly names the exact rule to modify.

## Fixed User Flow

When the user provides an `.xlsx`, `.xlsm`, or `.csv` file and asks to clean it:

1. If the file path is missing, ask for the file.
2. Determine product name and data source with deterministic rules from input paths, filenames, and workbook cells.
3. Show the planned `标准化总表` and `清洗后总表` filenames and ask the user to confirm the output naming.
4. If only one workbook is provided, ask `当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。`
5. Do not skip merge on a single workbook until the user confirms it is the only intended file.
6. After the user confirms there is only one intended workbook, skip merge and standardize the single workbook.
7. Return the standardized workbook and wait for the user to confirm it before any cleaning step.
8. If KOL clean words are not specified after standardized-workbook confirmation, ask only:

   ```text
   是否有 KOL 清理词？没有就回复“没有”；有的话请一次性发来所有清理词。
   ```

9. If the user says there are no clean words, pass no `--clean-word` arguments and continue.
10. If the user provides one or more clean words, stop and ask:

   ```text
   是否已经提供完成所有 KOL 清理词？你确认后我再进行清洗。
   ```

11. Do not run cleaning with provided KOL clean words until the user confirms the clean-word list is complete.
12. After the user confirms the clean-word list is complete, run the project tools directly. Do not ask the user to type commands.
13. Clean the standardized workbook with `tools/clean_excel_comments.py --target-header "评论内容"`.
14. Pass each clean word as one separate `--clean-word` argument.
15. After the cleaned `.xlsx` and `.csv` are generated and verified, immediately run cleanup for current-run intermediates.
16. Return only the cleaned `.xlsx` and `.csv` links unless the user asked before cleaning to keep logs or summaries for audit.

When the user provides multiple `.xlsx`, `.xlsm`, or `.csv` files and asks to merge them:

1. Use only the files explicitly provided by the user.
2. Do not scan a folder for extra Excel files.
3. Do not ask the user to open WPS, Excel, or a command line.
4. Before merging, determine product name and data source with deterministic rules from input paths, filenames, and workbook cells.
5. Confirm product name and data source once before merging.
6. Use `YYYYMMDD_产品名_数据来源_步骤名` for all main workbook filenames.
7. Step names are `合并总表`, `标准化总表`, and `清洗后总表`.
8. Show the planned `合并总表`, `标准化总表`, and `清洗后总表` filenames.
9. After product name and data source are confirmed once, do not ask again for later step filenames.
10. Ask `请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。` before running merge.
11. Do not run merge until the user confirms both the naming and entering the merge flow.
12. Merge the original provided workbooks first with `tools/merge_excel_workbooks.py`.
13. Always merge into a separate new Excel workbook file (`.xlsx` document); never use an input workbook path as the output.
14. This means creating a new Excel document as the merged master workbook, not adding a worksheet/sheet inside any original workbook.
15. After merge succeeds, return the raw merged workbook to the user and ask whether all intended Excel files have been provided and merged.
16. Do not standardize the raw merged workbook until the user confirms all intended files are included.
17. For B站 exports, strip fixed `回复@xxx：` or `回复 @xxx:` prefixes on the raw merged workbook before standardization.
18. Do not move reply rows or infer parent-child hierarchy during this prefix-stripping step.
19. After merge-completion confirmation, standardize the reply-prefix-stripped merged workbook with `tools/standardize_excel_headers.py`.
20. Return the standardized merged workbook to the user and wait for the user to confirm it before any cleaning step.
21. Do not clean the standardized merged workbook until the user confirms the standardized workbook can enter cleaning.
22. If the user confirms the standardized workbook and also wants cleaning, then run the fixed cleaning flow on the standardized merged workbook, not on any original workbook.
23. Clean a standardized or merged-standardized workbook with `--target-header "评论内容"`.
24. If KOL clean words were not already specified, ask the standard KOL clean-word question only after standardized-workbook confirmation.
25. If the user provides KOL clean words, also confirm that the clean-word list is complete before cleaning.
26. After cleaned outputs are generated and verified, immediately clean up current-run intermediate files unless the user asked before cleaning to keep audit files.

## Validated Multi-File Workflow

Use this as the default workflow for same-platform batches, where the user provides multiple files exported from one source with the same original format.

1. Show the product name, data source, and planned output filenames.
2. Ask `请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。`
3. Merge the original provided workbook files into a raw merged workbook.
4. Run this merge only after the user confirms both the naming and entering the merge flow.
5. Return the raw merged workbook before standardization.
6. Ask `是否已经提供并合并完所有需要合并的表格？你确认后我再进行标准化。`
7. For B站 exports, strip fixed `回复@xxx：` or `回复 @xxx:` prefixes on the raw merged workbook before standardization.
8. Do not move reply rows or infer parent-child hierarchy during this prefix-stripping step.
9. Standardize the reply-prefix-stripped merged workbook into a separate standardized merged workbook.
10. Return the standardized merged workbook and wait for the user to confirm it before cleaning.
11. Clean only after standardized-workbook confirmation and KOL clean-word completion confirmation.
12. Clean the standardized merged workbook with `tools/clean_excel_comments.py --target-header "评论内容"`.
13. After cleaned outputs are generated and verified, immediately delete intermediate workflow files unless the user asked before cleaning to keep logs.
14. Return only the cleaned `.xlsx` and `.csv` unless the user asked to keep logs.
15. Keep only the final cleaned `.xlsx` and `.csv` as the default retained outputs.

- Do not standardize individual source workbooks before merging same-platform batches.
- The original provided workbooks, raw merged workbook, and standardized merged workbook must remain separate files. Later steps must not overwrite earlier files.
- Before step 1, confirm the product name and data source once; use those confirmed values for all three step filenames.
- If only one workbook is provided, ask `当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。`
- Do not skip merge on a single workbook until the user confirms it is the only intended file.
- Do not standardize until the user confirms all intended workbooks have been included in the raw merged workbook.
- Do not clean until the user confirms the standardized merged workbook can enter cleaning.

## Final Cleanup Rules

- Run cleanup immediately after the cleaned `.xlsx` and `.csv` are generated and verified.
- Do not ask for a separate cleanup confirmation after cleaning.
- If the user asked before cleaning to keep logs or summaries for audit, keep only the requested audit files.
- Delete only intermediate workflow files generated by the current run: raw merged workbook, reply-prefix-stripped merged workbook, standardized workbook, their summary files, cleaning deletion log, and cleaning summary.
- Delete cleaning logs and summary files by default unless the user explicitly asks to keep them for audit.
- Keep only the final cleaned `.xlsx` and `.csv` as the default retained outputs.
- Do not delete original input files.
- Do not delete the cleaned `.xlsx` or cleaned `.csv`.
- Do not scan a folder for files to delete; pass each intermediate path explicitly to `tools/cleanup_intermediate_outputs.py`.
- If the user asks to keep logs, do not delete the deletion log or summary files requested by the user.

## B站 Reply Prefix Rules

- Run `tools/strip_bilibili_reply_prefixes.py` only on the raw merged workbook before standardization.
- This step strips only deterministic prefixes matching `回复@xxx：`, `回复 @xxx：`, `回复@xxx:`, or `回复 @xxx:` from the content column.
- The remaining text after the first Chinese or English colon stays in the same content cell.
- Do not move reply rows or infer parent-child hierarchy during this prefix-stripping step.
- Do not add hierarchy columns during this step.
- Do not delete rows during this step.
- Save a separate reply-prefix-stripped merged workbook; never overwrite the original raw merged workbook.

## Output Naming Rules

- Confirm product name and data source once before merging.
- If product name or data source is missing or ambiguous, ask the user for the missing field before merging.
- Product name and data source can be detected only through deterministic rules:
  - filename text such as `ScreenBar Halo2淘宝评论数据`;
  - parent folder names such as `明基MA`;
  - exact workbook headers such as `产品名`, `购买产品`, `商品名称`, `商品`, or fixed `评论日期与产品` parsing.
- Data source can be detected only through fixed keywords such as `淘宝`, `京东`, `小红书`, `抖音`, `微博`, `B站`, `TikTok`, `TTCommentExporter`, `YouTube`, `youtube`, `yt-comments`, or path text such as `社媒_小红书`.
- Do not use AI or semantic inference to extract product name or data source.
- Use Beijing date (`Asia/Shanghai`) in `YYYYMMDD` format.
- Use `YYYYMMDD_产品名_数据来源_步骤名` for all main workbook filenames.
- Step names are `合并总表`, `标准化总表`, and `清洗后总表`.
- After product name and data source are confirmed once, do not ask again for later step filenames; only change the step name.
- Ask `请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。` before running merge.
- If only one workbook is provided, ask `当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。`
- The cleaned CSV uses the same base name as `清洗后总表` with `.csv`.

## Base Rules

These rules are fixed and must remain unchanged during future feature additions unless the user explicitly changes one of them.

- Supported inputs: `.xlsx`, `.xlsm`, and `.csv`.
- CSV inputs are loaded through the deterministic compatibility layer before standardization, merge, or direct cleaning.
- CSV values are preserved as text; do not infer numeric, date, ID, or timestamp types from CSV cells.
- Process every worksheet in the workbook.
- Treat row 1 as the header row.
- Start cleaning at row 2.
- For direct legacy cleaning, use column 3 as the comment/content column.
- For standardized workbooks, locate the comment/content column by the header `评论内容`.
- Trim leading and trailing whitespace before evaluating the comment.
- Chinese comments whose trimmed length is less than or equal to 7 characters are deleted.
- Delete comments exactly equal to:
  - `该用户未填写评价内容`
  - `此用户未填写评价内容`
- Delete comments containing any user-provided KOL clean word.
- Before using provided KOL clean words, confirm that the user has provided the complete clean-word list.
- Fixed delete words are appended to the original `链接` rule; do not replace or remove `链接`.
- Chinese comments delete by character length; non-Chinese comments delete by deterministic word count.
- Non-Chinese comments with four or fewer words are deleted.
- For unspaced non-Chinese scripts, only very short text with four or fewer characters is deleted by the short-text rule.
- Pure numeric comments keep the legacy seven-character threshold for backward compatibility.
- When adding a fixed delete word later, add confirmed equivalents for Chinese, English, Japanese, Korean, Spanish, Thai, and Hindi where applicable.
- The complete fixed delete word lists are stored in `config/comment-cleaner.json`; the configured coverage currently includes Chinese, English, Japanese, Korean, Spanish, Thai, and Hindi terms.
- Delete comments containing any configured fixed delete word. Current fixed delete words include: `链接`, `凑字数`, `水经验`, `赚积分`, `为了金币`, `赚硬币`, `赚京豆`, `淘气值`, `为了评论而评论`, `混个脸熟`, `完成任务`, `代下`, `代买`, `内部券`, `加微`, `加v`, `私聊我`, `主页看`, `点击链接`, `http://`, `https://`, `第一`, `打卡`, `路过`, `来了`, `冒泡`, `占座`, `测试`, `test`, `无`, `无内容`, `略`, `暂无评价`, `蹲`, `蹲一个`, `求链接`, `求分享`, `多少钱`, `怎么卖`, `啥牌子`, `什么牌子`, `求品牌`, `求私`, `加群`, `裙内`, `互赞`, `互粉`, `互关`, `回关`, `秒回`, `交朋友`, `リンク`, `プロフィール見て`, `プロフ見て`, `DMして`, `フォロー返し`, `相互フォロー`, `テスト`, `内容なし`, `評価なし`, `コメント稼ぎ`, `링크`, `맞팔`, `테스트`, `내용 없음`.
- `加v` is matched case-insensitively so `加v` and `加V` are both deleted. English fixed delete words are also matched case-insensitively, including `link in bio`, `click link`, `click the link`, `check my profile`, `see my profile`, `visit my profile`, `dm me`, `message me`, `follow me`, `follow back`, `follow for follow`, `sub4sub`, `sub for sub`, `subscribe to my channel`, `earn coins`, `free coins`, `for coins`, `comment for points`, `promo code`, `coupon code`, `discount code`, `whatsapp`, `telegram`, `first`, `test`, `n/a`, `no content`, `no comment`, and `nothing to say`.
- Delete no-Chinese random alphanumeric heap comments only by deterministic regex and thresholds; do not use AI or normal-English semantic judgment for this rule.
- Remove duplicate comments only within the same worksheet.
- For duplicates in one worksheet, keep the last occurrence and delete earlier occurrences.
- For duplicate values in `一级评论`, `二级评论`, or `三级评论`, keep the last occurrence and clear only the earlier duplicate subcomment cell.
- Clear `一级评论`, `二级评论`, and `三级评论` cells whose trimmed length is less than or equal to 5 characters.
- Subcomment deduplication must not delete the row and must not modify the main `评论内容` column.
- Short subcomment cleanup must not delete the row and must not modify the main `评论内容` column.
- Subcomment deduplication uses exact text matching only; do not use AI, semantic similarity, or fuzzy matching.
- Never modify the original workbook; always save a new workbook.
- Export a cleaned `.xlsx`.
- Export a `.csv` from the first worksheet.
- Export a deletion log `.deletions.csv`; row deletion records use `delete_row`, and subcomment cell-clearing records use `clear_cell`.
- Export a summary `.summary.json`.

## Header Standardization Rules

These rules run after merge for multi-file workflows and before cleaning for single-file workflows, unless the user explicitly asks for the old direct-cleaning behavior.

- Use only deterministic header matching; do not use AI or semantic inference.
- Process every worksheet in the workbook.
- Treat row 1 as the header row.
- Never modify the original workbook or raw merged workbook; always create a separate standardized workbook.
- Standardization must move the cell values under each matched source column together with the header. It must not only rename or reorder header text.
- Output only these columns, in this exact order:
  1. `评论日期`
  2. `评论内容`
  3. `产品名`
  4. `点赞数`
  5. `子评论数/追评数`
  6. `一级评论`
  7. `二级评论`
  8. `三级评论`
- Accepted deterministic aliases:
  - `评论日期`: `评论日期`, `评论时间`, `评论日期与产品`, `timestamp`, `createTime`, `create_time`, `createdAt`, `created_at`, `createDate`, `create_date`, `publishedAt`, `published_at`, `publishedTime`, `published_time`, `published`, `date`, `Date`, `time`, `Time`, `commentTime`, `comment_time`, `Comment Published`, `Published At`
  - `评论内容`: `评论内容`, `评论`, `content`, `text`, `Text`, `comment`, `Comment`, `commentText`, `comment_text`, `Comment Text`, `message`, `body`
  - `产品名`: `产品名`, `购买产品`, `商品名称`, `商品`, `评论日期与产品`
  - `点赞数`: `点赞数`, `点赞量`, `Digg Count`, `like_count`, `likeCount`, `Like Count`, `likes`, `Likes`, `diggCount`, `digg_count`
  - `子评论数/追评数`: `子评论数/追评数`, `子评论数`, `子评论数（追评数）`, `追评数`, `评论数`, `回复数`, `replyCount`, `reply_count`, `Reply Count`, `replyCommentTotal`, `reply_comment_total`, `replies`, `Replies`
  - `一级评论`: `一级评论`, `一级评论内容`, `追评`, `replyText`, `reply_text`, `Reply Text`
  - `二级评论`: `二级评论`, `二级评论内容`, `引用的评论内容`
  - `三级评论`: `三级评论`, `三级评论内容`
- When the source header is `评论日期与产品`, split its cell value with a deterministic parser only:
  - The leading `YYYY年M月D日`, `YYYY/M/D`, or `YYYY-M-D` text becomes `评论日期`.
  - Text after the optional fixed marker `已购：` becomes `产品名`.
  - If the value does not match this fixed date-leading pattern, keep the original value in `评论日期` and leave `产品名` blank.
- When the source header is `timestamp`, `createTime`, `create_time`, `createdAt`, `created_at`, `publishedAt`, `published_at`, `publishedTime`, `published_time`, `date`, `Date`, `time`, `Time`, or another configured platform time alias, convert Unix seconds/milliseconds or ISO timestamps deterministically to Beijing date (`UTC+8`) in `YYYY-MM-DD` format. Keep only year, month, and day; do not output hours, minutes, or seconds.
- For Chinese `评论时间` or `评论日期` source columns, convert only numeric timestamps or date-time text that includes a time component to `YYYY-MM-DD`; preserve plain date-only values as originally provided.
- Relative platform time values such as `1年前`, `9个月前`, `1 year ago`, and `9 months ago` are converted deterministically from the current Beijing date. Relative year values output only `YYYY`; relative month values output only `YYYY-MM`. Relative day/week values output `YYYY-MM-DD`. Do not infer missing month/day beyond this fixed granularity.
- The standardized output keeps only the configured columns. `IP地址`, `IP属地`, `用户名称`, `用户昵称`, `昵称`, `rpid`, `parent_rpid`, `username`, `ip_location`, `id`, `comment_id`, `commentId`, `cid`, `uid`, `user_id`, `userId`, `uniqueId`, `author`, `authorName`, `authorDisplayName`, `authorChannelId`, `channelId`, `profileUrl`, `avatar`, `videoId`, `videoUrl`, `url`, `permalink`, and any other non-configured columns are omitted from the standardized workbook.
- `parent_rpid` is a parent-comment ID, not a subcomment count. Do not map it to `子评论数/追评数`.
- `产品名`, `一级评论`, `二级评论`, and `三级评论` are kept as output columns even if a source workbook lacks one of them; missing optional values are left blank to keep merge headers stable.
- `子评论数/追评数` is a required standard output column, but the source header may be missing. If no matching source header exists, keep the output column and leave its cells blank.
- Do not infer `四级评论` or deeper levels dynamically. Add them only after the user explicitly extends the fixed schema.
- Record omitted headers and configured dropped headers in `.standardized.summary.json`.
- If a required header is missing or matches more than one source column, stop and report the problem. Do not guess.
- If the source uses a different name for the same column, add that source header as an explicit alias in `config/header-standardizer.json`; do not infer it with AI.
- When the user supplements the alias mapping table, update only the relevant `aliases` entry unless the user explicitly changes the standard output schema.
- Export a `.standardized.xlsx`.
- Export a `.standardized.summary.json`.

## Merge Rules

These rules govern the merge step. They do not change the base cleaning rules.

- Merge only explicit files provided by the user.
- Never merge every Excel file in a folder unless the user explicitly provides those files as the input list.
- Supported merge inputs: `.xlsx`, `.xlsm`, and `.csv`.
- Do not run merge until the user confirms `请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。`.
- When only one workbook is provided, do not skip merge until the user confirms it is the only intended file.
- Merge the original provided workbooks first; standardize the merged workbook only after the user confirms the merge set is complete.
- Preserve the user-provided file order.
- Process every worksheet in each provided workbook.
- Treat row 1 of each worksheet as the header row.
- Write the header only once, using the first worksheet's header from the first provided workbook.
- Append data rows from row 2 onward.
- Skip rows that are completely blank.
- Reject the merge if any later worksheet has a different header from the first header.
- Do not clean, delete, deduplicate, classify, summarize, or semantically interpret rows during merge.
- Do not use AI during merge; only copy workbook cell values with the deterministic tool.
- Merge into a separate newly created Excel workbook file; never merge into one of the original workbooks.
- This new file is the merged master workbook, not a new worksheet/sheet inside any original workbook.
- Reject any merge where the output path equals one of the input file paths.
- Return the newly created raw merged workbook document to the user before standardization.
- After merging, pause before standardization and confirm with the user that all intended files have been included.
- Never run standardization on a merged workbook until the user gives merge-completion confirmation.
- After standardization, return the standardized merged workbook to the user and wait for standardized-workbook confirmation before cleaning.
- Never run the cleaning step on a standardized merged workbook until the user gives standardized-workbook confirmation.
- Do not modify any original workbook.
- Export a merged `.xlsx`.
- Export a merge summary `.summary.json`.

## Prohibited Behavior

- Do not use AI or semantic judgment to decide header mapping, column deletion, or row deletion.
- Do not use AI or semantic judgment during header standardization.
- Do not use AI or semantic judgment during workbook merging.
- Do not use AI or semantic judgment to split `评论日期与产品`; use only the fixed parser documented in the header-standardization rules.
- Do not delete comments based on sentiment, quality, suspected advertising, relevance, tone, or intent.
- Do not do fuzzy matching unless the user explicitly adds such a rule.
- Do not add unconfirmed KOL clean words.
- Do not clean columns other than column 3 in legacy direct-cleaning mode, or the `评论内容` header in standardized mode.
- Do not deduplicate across different worksheets.
- Do not delete a row only because `一级评论`, `二级评论`, or `三级评论` repeats; clear the duplicate subcomment cell instead.
- Do not delete a row only because `一级评论`, `二级评论`, or `三级评论` is too short; clear the short subcomment cell instead.
- Do not modify `评论内容` while deduplicating subcomment columns.
- Do not modify the original input file.
- Do not use the old RPA canvas or a nonexistent Bazhuayu CLI.
- Do not change the base rules while adding new features.
- Do not proceed from merge to standardization without explicit user confirmation that the merge set is complete.
- Do not enter merge before explicit user confirmation of both output filename naming and entering the merge flow.
- Do not skip merge for a one-file input without explicit user confirmation that there is only one intended file.
- Do not proceed from standardization to cleaning without explicit user confirmation that the standardized workbook is approved for cleaning.
- Do not clean with provided KOL clean words without explicit user confirmation that the clean-word list is complete.

## Tool Usage

Primary script:

```text
tools/clean_excel_comments.py
```

Header standardization script:

```text
tools/standardize_excel_headers.py
```

Merge script:

```text
tools/merge_excel_workbooks.py
```

B站 reply prefix script:

```text
tools/strip_bilibili_reply_prefixes.py
```

Intermediate cleanup script:

```text
tools/cleanup_intermediate_outputs.py
```

Output naming planner:

```text
tools/output_file_naming.py
```

Default config:

```text
config/comment-cleaner.json
```

Header standardization config:

```text
config/header-standardizer.json
```

Preferred command shape:

```powershell
python tools\clean_excel_comments.py "<input.xlsx-or.csv>" --clean-word "<word1>" --clean-word "<word2>" --output-dir "<output-dir>"
```

Preferred standardized cleaning command shape:

```powershell
python tools\standardize_excel_headers.py "<input.xlsx-or.csv>" --output-dir "<output-dir>"
python tools\clean_excel_comments.py "<standardized.xlsx>" --target-header "评论内容" --clean-word "<word1>" --output "<confirmed-cleaned.xlsx>"
```

Preferred merge command shape:

```powershell
python tools\output_file_naming.py "<file1.xlsx-or.csv>" "<file2.xlsx-or.csv>" "<file3.xlsx-or.csv>"
python tools\merge_excel_workbooks.py "<file1.xlsx-or.csv>" "<file2.xlsx-or.csv>" "<file3.xlsx-or.csv>" --output "<raw-merged.xlsx>"
python tools\strip_bilibili_reply_prefixes.py "<raw-merged.xlsx>" --output "<reply-prefix-stripped-merged.xlsx>"
python tools\standardize_excel_headers.py "<reply-prefix-stripped-merged.xlsx>" --output "<confirmed-standardized.xlsx>"
python tools\clean_excel_comments.py "<standardized-merged.xlsx>" --target-header "评论内容" --clean-word "<word1>" --output "<confirmed-cleaned.xlsx>"
python tools\cleanup_intermediate_outputs.py --intermediate "<raw-merged.xlsx>" --intermediate "<reply-prefix-stripped-merged.xlsx>" --intermediate "<confirmed-standardized.xlsx>" --intermediate "<confirmed-cleaned.deletions.csv>" --intermediate "<confirmed-cleaned.summary.json>" --protect "<confirmed-cleaned.xlsx>" --protect "<confirmed-cleaned.csv>" --summary "<cleanup-summary.json>"
```

When global `python` is unavailable, use the bundled Codex Python path from `load_workspace_dependencies` or the existing runtime path already used in this project.

## Output

For a cleaned workbook, return:

- The cleaned `.xlsx`.
- The cleaned `.csv`.

Only include these when the user asks to audit logs:

- `.standardized.summary.json`
- `.deletions.csv`
- `.summary.json`

For a raw merged workbook that has not yet been cleared for standardization, return the raw merged `.xlsx`, then ask:

```text
是否已经提供并合并完所有需要合并的表格？你确认后我再进行标准化。
```

Before merge, combine naming confirmation and merge-entry confirmation in one prompt:

```text
请确认以上产品名、数据来源和文件命名是否正确，并确认是否可以进入合并流程。
```

When only one workbook is provided, ask before skipping merge:

```text
当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。
```

For a standardized merged workbook that has not yet been cleared for cleaning, return the standardized merged `.xlsx`, then ask:

```text
标准化后的表格已生成，请确认是否可以进入清洗流程？你确认后我再询问 KOL 清理词并清洗。
```

For a workbook waiting on KOL clean-word completion confirmation, ask:

```text
是否已经提供完成所有 KOL 清理词？你确认后我再进行清洗。
```

## Validation

After changing code, config, or the skill:

1. Run the test suite:

   ```powershell
   python -m unittest discover -s tests
   ```

2. Confirm tests pass before saying the workflow is ready.
3. If changing a base rule, add or update a test that proves the exact rule.
4. If adding a new feature, add tests for the feature and verify all base-rule tests still pass.

Current required base-rule coverage includes:

- KOL clean words are optional.
- Chinese comments with 7 or fewer characters are deleted.
- Non-Chinese comments with four or fewer words are deleted, while unspaced non-Chinese scripts use only the four-character short-text fallback.
- Pure numeric comments keep the legacy seven-character threshold.
- Comments with 8 or more characters can be retained when no other rule deletes them.
- Fixed delete words are appended to the original `链接` rule, including later additions such as `为了金币`, `暂无评价`, `蹲一个`, and `交朋友`.
- `加v` fixed-word matching is case-insensitive.
- No-Chinese random alphanumeric heap comments are deleted by deterministic thresholds while normal English phrases can be retained.
- Duplicate comments keep the last occurrence within a worksheet.
- Duplicate `一级评论`, `二级评论`, or `三级评论` values clear earlier duplicate cells without deleting rows or changing `评论内容`.
- `一级评论`, `二级评论`, and `三级评论` values with trimmed length less than or equal to 5 clear only that cell without deleting rows or changing `评论内容`.
- CSV input files can be cleaned through the compatibility layer while preserving CSV values as text.

Current required merge coverage includes:

- Multiple explicitly provided workbooks merge into one workbook.
- Explicit CSV inputs can be merged into a new workbook.
- Only one header row is written.
- User-provided input order is preserved.
- Header mismatches are rejected.
- B站 reply prefixes can be stripped from the raw merged workbook without moving rows, adding columns, or deleting rows.
- Intermediate cleanup protects final cleaned `.xlsx` and `.csv` while deleting only explicitly passed process files.

Current required header-standardization coverage includes:

- Headers can be reordered into the approved eight-column schema.
- `评论日期与产品` can be split into `评论日期` and `产品名` without AI.
- `IP地址`, `用户名称`, `rpid`, `parent_rpid`, `username`, and `ip_location` are omitted from standardized output.
- `timestamp`, `content`, and `like_count` map to `评论日期`, `评论内容`, and `点赞数`.
- `timestamp` values convert to Beijing date (`UTC+8`) in `YYYY-MM-DD` format, keeping only year, month, and day.
- Chinese `评论时间` or `评论日期` columns convert numeric timestamps or date-time text with a time component to `YYYY-MM-DD`, while plain date-only values are preserved.
- Relative year values output only `YYYY`; relative month values output only `YYYY-MM`.
- TikTok aliases such as `createTime`, `评论`, `text`, `Digg Count`, `diggCount`, `回复数`, and `replyCommentTotal` map deterministically to the standard schema.
- YouTube aliases such as `publishedAt`, `commentText`, `likeCount`, `replyCount`, and `replyText` map deterministically to the standard schema, with ISO timestamps converted to Beijing date.
- Required missing headers are rejected instead of guessed.
- Missing source headers for `子评论数/追评数` keep that standard output column blank instead of failing.
- Standardized cleaning can target the `评论内容` header.
- CSV inputs can be standardized through the same header mapping rules.

## Feature Additions

When adding future functionality:

- Keep this skill as the source of truth for base cleaning rules.
- Add new behavior behind explicit user confirmation, config fields, or new scripts.
- Preserve backward compatibility for the fixed cleaning flow.
- Prefer deterministic rules over AI classification.
- If a proposed feature conflicts with a base rule, ask the user to confirm the exact rule change before editing code.
- Treat user-provided header alias mappings as deterministic rules and add tests for representative aliases.
