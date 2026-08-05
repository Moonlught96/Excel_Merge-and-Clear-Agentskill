# Workflow And Confirmation Gates

## Contents

- [Global Order](#global-order)
- [Identity Selection During Standardization](#identity-selection-during-standardization)
- [Initial File Handling](#initial-file-handling)
- [X Data-Type Gate](#x-data-type-gate)
- [Single-File Workflow](#single-file-workflow)
- [Multi-File Workflow](#multi-file-workflow)
- [Technical-Term Gate](#technical-term-gate)
- [KOL Clean-Word Gate](#kol-clean-word-gate)
- [X Tweet Keep-Keyword Gate](#x-tweet-keep-keyword-gate)
- [B站 Reply Prefix Step](#b站-reply-prefix-step)
- [Platform Preprocessing](#platform-preprocessing)
- [Standardized Output Audit](#standardized-output-audit)
- [Execution Safeguards](#execution-safeguards)
- [Completion](#completion)

## Global Order

The fixed workflow is:

1. When the user identifies the input as X/Twitter, require the X data-type selection before a route or output name is planned.
2. Confirm research project name, product name, data source, and planned filenames once. For a new research project, separately confirm the DPAPI project-key privacy notice before initialization.
3. Confirm whether the supplied file list is complete enough to enter merge or, for one file, whether it is the only intended input.
4. Merge multiple raw inputs into a new raw merged workbook, except for a validated registered mixed-variant batch.
5. Return the raw merged workbook, or the platform-preprocessed merged workbook for that exception, and wait for merge-completion confirmation.
6. For B站 data, create a separate reply-prefix-stripped temporary workbook from the confirmed single input or raw merged workbook.
7. When an exact registered platform profile applies, preprocess that temporary or raw workbook through the deterministic platform splitter.
8. Standardize the raw, prefix-stripped, or platform-preprocessed workbook into a new standardized workbook.
9. Audit the standardized workbook automatically before it may reach the user-approval or cleaning gate.
10. Return the standardized workbook only after the audit passes, then wait for approval.
11. For the registered `twitter` X 推文 profile only, collect and confirm X 推文 keep keywords, then run its deterministic row-retention filter.
12. Ask for optional technical terms and, when terms exist, confirm the list is complete.
13. Ask for optional KOL clean words and, when words exist, confirm the list is complete.
14. Clean with deterministic tools.
15. Verify final `.xlsx` and `.csv`, clean up current-run intermediates, and return retained outputs.

Do not collapse or reorder the confirmation gates.

## Identity Selection During Standardization

For each worksheet, the deterministic standardizer applies this order before processing rows:

1. Select the first registered stable account-ID column for the confirmed platform that contains at least one nonblank value.
2. Only when every registered account-ID column is entirely blank, select the first configured display-name fallback.
3. Use that one selected column for the whole worksheet; never switch identity sources row-by-row.
4. After selecting a nonblank account-ID column, keep `哈希ID` blank for individual rows whose selected account-ID cell is blank; never fall back row-by-row.
5. Omit raw account IDs, usernames, and nicknames from standardized and cleaned outputs, logs, and summaries.

When the workflow creates a new research project, show the privacy confirmation template before standardization. Only after the user confirms it may the Agent run `scripts/standardize_excel_headers.py` with `--initialize-project --confirm-project-key-creation <exact-project-name>`. A later run for the same project loads the existing protected key and must not reinitialize it.

Do not use AI to choose, normalize, or hash an identity source. The exact mappings and risk limits are in `header-standardization.md` and `data-contract.md`.

## Initial File Handling

- If no file path is provided, ask the user to provide the files.
- Accept `.xlsx`, `.xlsm`, and `.csv`.
- Use only files explicitly provided by the user. Never scan a folder for additional files.
- Reject duplicate input paths before merge instead of silently duplicating their rows.
- When reporting a file, platform, or product total, run `scripts/inventory_comment_inputs.py` on the exact supplied input paths and report only its logical `data_rows`. Never count CSV physical lines or reuse a remembered total.
- Confirm research project name, product name, and data source once per workflow. Reuse the existing protected key until the user explicitly identifies a new research project. Later phases change only the step name in the output filename.
- When the user identifies the inputs as X/Twitter, run the X data-type gate before confirming a planned platform-preprocessing route or output names.

## X Data-Type Gate

This gate is mandatory whenever the user identifies the supplied files as X/Twitter data. Run it before output naming, merge entry, or `scripts/preprocess_platform_comments.py`. Do not infer `推文` or `评论` from filenames, headers, row values, content, user IDs, or AI judgment.

Ask exactly:

```text
检测到 X/Twitter 数据，请选择本轮数据类型：
[1] 推文：使用既有 `twitter` 推文分流和推文保留关键词流程。
[2] 评论：使用独立的 X 评论分流，不套用推文分流或推文保留关键词流程。

请回复“推文”或“评论”。
```

- `推文` selects the registered `twitter` profile. Only this branch runs the X 推文 keep-keyword gate after standardization approval.
- `评论` selects the registered `twitter-comments` profile. It has the same complete ordered exporter signature as `twitter`, so omitting the selected profile is an ambiguity error rather than permission to choose either route.
- X 评论使用独立的 `twitter-comments` 分流。它固定复制 `created_at`、`full_text`、`favorite_count`、`reply_count`、`user_id`、`screen_name` 到与推文相同的临时列；不得套用 `twitter` 推文分流或保留关键词筛选。
- `twitter-comments` 与 `twitter` 共用 `twitter` 哈希命名空间，并共用已确认的 `Twitter用户ID`、`Twitter昵称` 身份优先级；X 评论不执行 X 推文保留关键词筛选，标准化审批后直接进入技术名词闸门。
- Both answers are independent from the merge-completion, standardization-approval, technical-term, KOL-word, and output-overwrite confirmation gates.

## Single-File Workflow

After showing product name, data source, and the planned `标准化总表` and `清洗后总表` filenames, ask exactly:

```text
当前只收到 1 个文件，请确认是否只有这一个文件需要处理？你确认后我将跳过合并，直接进入标准化。
```

- Do not skip merge until the user confirms this is the only intended input.
- After confirmation, apply the fixed B站 prefix step when applicable, then apply an exact registered platform-preprocessing profile when applicable, each into a separate workbook.
- Standardize the resulting workflow source into a separate workbook, then run the standardized-output audit against that exact source.
- Return the standardized workbook only after the audit passes, and wait for approval before asking for X 推文 keep keywords when applicable, then technical terms, KOL clean words, and cleaning.

## Multi-File Workflow

This is the default for same-platform batches with the same original format.

1. Show product name, data source, the planned platform-preprocessing profile, its required full ordered-header-signature validation, and all four planned filenames, including the cleaned `.csv`.
2. Ask exactly:

   ```text
   请确认以上产品名、数据来源、平台预处理分流和文件命名是否正确，并确认是否可以进入合并流程。
   ```

3. Do not run merge until the user confirms naming, the intended platform-preprocessing route, and entry into merge. The planned route never bypasses the required full ordered header-signature validation after merge.
4. Merge the explicitly provided original files in their provided order into a new raw merged `.xlsx`.
5. If raw merge raises `HeaderMismatchError`, do not create a partial output. When the confirmed profile has registered variants, run `scripts/preprocess_platform_comments.py` with `--merge-registered-variants` only if every input sheet exactly matches one registered variant. This creates one platform-preprocessed merged workbook with the shared registered temporary output schema; it does not modify an original input and it is not a raw merge fallback for unrelated headers.
6. Return the raw merged workbook or the validated platform-preprocessed merged workbook before standardization.
7. Ask exactly:

   ```text
   是否已经提供并合并完所有需要合并的表格？你确认后我再进行标准化。
   ```

8. Do not standardize until the user confirms all intended files are included.

9. Pass the product name already confirmed at the naming gate to standardization as `--product-name`. It is a deterministic literal fallback only for an absent or blank source product value; a nonblank mapped source product value remains unchanged.
10. If the data source is B站, run the fixed reply-prefix step on the merged workbook and create a separate output.
11. If an exact registered platform profile applies and the merge checkpoint was raw, run it against the raw merged or B站 prefix-stripped workbook and write a separate temporary workbook. If the merge checkpoint is already platform-preprocessed, pass it directly to standardization; otherwise retain the existing fixed platform standardization flow.
12. Standardize into a new workbook; never overwrite the raw merged workbook or platform-preprocessed merged workbook.
13. Run the standardized-output audit with the exact workbook used as the standardization source. If it fails, stop before asking for technical terms, KOL words, or standardization approval.
14. Return the standardized workbook only after the audit passes and ask exactly:

    ```text
    标准化后的表格已生成，请确认是否可以进入清洗流程？你确认后我将先询问技术名词，再询问 KOL 清理词并清洗。
    ```

15. Do not clean until the user explicitly approves the standardized workbook. For the registered `twitter` X 推文 profile, run the X 推文 keep-keyword gate defined below before the technical-term gate, which is always before the KOL clean-word gate.

Do not standardize individual files before merging a same-platform batch.

## Technical-Term Gate

After standardized-workbook approval and, for the registered `twitter` X 推文 profile, after its keep-keyword filter completes, ask exactly:

```text
是否有技术名词需要清洗？没有就回复“没有”；有的话请一次性提供所有技术名词。
```

- If the user says there are no technical terms, pass no `--technical-term` arguments and continue to the KOL clean-word gate.
- If one or more terms are provided, do not clean yet. Ask exactly:

  ```text
  是否已经提供完成所有技术名词？你确认后我再询问 KOL 清理词。
  ```

- Only after confirmation, pass each confirmed term as a separate `--technical-term` argument. The common cleaner deletes a main-comment row only when it matches 4 个及以上不同技术名词.
- Repeated occurrences of the same term count once. Latin terms use deterministic case-insensitive complete-term matching; Chinese, Japanese, Korean, Thai, Hindi, and mixed-script terms use exact literal containment. Do not translate, expand, fuzzy-match, normalize by meaning, or use AI.
- Never add an unconfirmed technical term or persist a per-run list into the canonical fixed delete-word configuration.

## KOL Clean-Word Gate

After the technical-term gate completes and, for the registered `twitter` X 推文 profile, after its keep-keyword filter completes, ask exactly:

```text
是否有 KOL 清理词？没有就回复“没有”；有的话请一次性发来所有清理词。
```

- If the user says there are no KOL clean words, pass no `--clean-word` arguments and continue.
- If one or more words are provided, do not clean yet. Ask exactly:

  ```text
  是否已经提供完成所有 KOL 清理词？你确认后我再进行清洗。
  ```

- After confirmation, pass each clean word as a separate `--clean-word` argument.
- Never add an unconfirmed KOL clean word.

## X Tweet Keep-Keyword Gate

This gate applies only when the user selected `推文` in the X data-type gate and the confirmed platform-preprocessing profile is `twitter`. It runs after standardization audit and user approval, and before the universal technical-term and KOL clean-word gates. It does not apply to X 评论.

Ask exactly:

```text
请提供本轮 X 推文保留关键词。仅保留“评论内容”包含任一关键词的整行数据；请一次性提供所有关键词。
```

- Require one or more nonblank keywords. Do not silently skip this gate for X 推文 and do not invent a keyword.
- When the user supplies one or more keywords, do not filter yet. Ask exactly:

  ```text
  是否已经提供完成所有 X 推文保留关键词？你确认后我将执行关键词筛选，再进入通用技术名词、KOL 清理词与清洗流程。
  ```

- After confirmation, run `scripts/filter_comments_by_keywords.py` with one `--keep-keyword` argument per confirmed keyword. Its output is the input to the common technical-term, KOL clean-word, and cleaning stages.
- The filter is deterministic and literal: it deletes every row whose `评论内容` does not contain at least one confirmed keyword. It does not translate, expand, fuzzy-match, or interpret a keyword.
- Treat the filtered workbook and its keyword-filter summary as current-run intermediates. After final verification, delete them through explicit-path cleanup while protecting original inputs and final outputs.

## B站 Reply Prefix Step

- Run the step before standardization for every B站 workflow.
- In a multi-file workflow, run it on the raw merged workbook only after merge-completion confirmation.
- In a single-file workflow, run it on the original input only after the user confirms it is the only intended file.
- Process only a fixed prefix in `content` or `评论内容` matching `回复@xxx：`, `回复 @xxx：`, `回复@xxx:`, or `回复 @xxx:`.
- Keep only the text after the first matching Chinese or English colon in the same cell.
- Save a separate temporary reply-prefix-stripped workbook.
- Do not overwrite the original input or raw merged workbook.
- Do not move reply rows, infer parent-child hierarchy, add hierarchy columns, or delete rows.

## Platform Preprocessing

- `scripts/preprocess_platform_comments.py` is a deterministic splitter before the common standardizer. It selects only one registered platform/profile variant by a full exact header signature from `config/platform-preprocessing.json`.
- The registered profiles are `amazon-japan`, `amazon-us`, `rakuten`, `twitter` (X 推文), `twitter-comments` (X 评论), and `reddit`. Amazon Japan and Amazon US use separate profiles and separate hash namespaces: Japan's 13-column profile parses its registered date field, while the US 10-column profile emits a blank date because no date source is registered. `rakuten` contains five explicitly registered exact variants for its confirmed export layouts; all retain the same `rakuten` hash namespace and common standard output schema. `twitter` and `twitter-comments` deliberately register the same exact full exporter signature, so automatic signature detection stops with an ambiguity error and the selected X type must supply the profile. Both use the confirmed `twitter` hash namespace and identity fields; only `twitter` runs the X 推文 keyword-retention gate. `reddit` has one exact full export signature; it preserves every source row independently, uses only the temporary `Reddit作者` display-name fallback, and does not have the X 推文 keyword-retention gate.
- The Agent may invoke the splitter only for a registered profile or to inspect the supplied headers deterministically. It must never use AI, fuzzy matching, source-value semantics, or filename guesswork to choose a profile.
- For a multi-file batch whose raw merge raises `HeaderMismatchError`, `--merge-registered-variants` may preprocess every input sheet using its own full exact registered variant, then append the common configured temporary columns into one platform-preprocessed merged workbook. All output-column headers and order must be identical across those variants. The result is the merge checkpoint and must not be sent through the splitter again.
- If any input sheet fails its selected profile signature, stop. Do not fall back to another profile, a partial field match, or a partial merged output.
- If the configured profile or one of its registered variants does not match, the script stops with `No configured platform signature matched`. Do not route the workbook into another profile or continue with another platform's rule.
- An unregistered legacy platform remains on its existing fixed standardization flow. This is not a fallback profile match and does not change existing mappings.
- The preprocessed workbook and its summary are current-run intermediates. Do not overwrite its source or return it as a normal confirmation checkpoint.

## Standardized Output Audit

Immediately after standardization, run `scripts/audit_standardized_comments.py` with the standardized workbook and the exact source workbook passed to the standardizer.

The audit is deterministic and must pass all of these checks before the standardized workbook is returned for user confirmation:

1. Every sheet has the exact locked output headers in the exact order.
2. No duplicate or raw identity header is present in standardized output.
3. Each nonblank `哈希ID` is exactly 64 lowercase hexadecimal characters.
4. Standardized worksheet names/order and data-row counts match the workbook supplied to standardization.
5. Every standardized data row has a nonblank `点赞数`; source blanks or an absent source column must already have been written as numeric `0` by standardization.
6. When the exact source has registered fixed aliases, each non-hash standardized value matches the applicable deterministic source mapping, date/rating/likes normalization, or permitted confirmed product fallback. The audit records only mismatch counts and issue codes, never source or output cell values.

Standardization captures one Beijing calendar date for the entire workbook and records it in the standardization summary. The audit reuses that exact `reference_date` when verifying relative source times, so a run crossing Beijing midnight cannot create a false mapping mismatch.

The audit report records only structural metadata, counts, header names, and issue codes; it must not record a raw identity value or comment text. It does not judge semantic quality, sentiment, language, product relevance, or whether a row should be deleted. If any check fails, stop the workflow before user confirmation, technical-term collection, KOL-word collection, or cleaning.

## Execution Safeguards

- Run preprocessing, standardization, hash-ID, audit, and cleaning only with their bundled canonical configuration files. Do not create, copy, load, or pass an external or temporary configuration for one batch.
- Run the public cleaner CLI only with the exact `--target-header 评论内容` and the confirmed nonblank `--platform`. Canonical URL/link marker terms apply to every platform, including Twitter/X, and may not be bypassed through a per-run configuration. The one canonical `twitter-comments` exception strips literal `https://` URL text from the `评论内容` cell only before matching; it does not touch other columns, does not apply to `twitter` X posts, and leaves `http://` active.
- The merge, merge-completion, standardized-workbook, and word-list confirmation gates require an explicit reply in the current conversation. Do not treat a CLI option, JSON marker, old log, historical approval, or urgency request as confirmation.
- If a planned output already exists, first show every exact replacement path and obtain explicit user confirmation. The CLI must then receive `--overwrite` and one `--confirm-overwrite <exact-existing-path>` argument for every existing file it will replace, including generated summaries or CSV sidecars. `--overwrite` by itself is not confirmation.
- If default retention has removed a final cleaner `.deletions.csv` or `.summary.json`, that artifact is finalized. Do not rerun the cleaner at the same final `.xlsx` path to recreate either artifact, do not copy either one back, and do not use cleanup `--summary` to write a replacement. Use a new confirmed output path for a fresh run.

## Completion

- Verify the cleaned `.xlsx` and `.csv` exist before cleanup.
- Pass those exact two existing files as the two `--final-output` values and also as protected paths. Both the cleanup CLI and its callable function must stop before deleting any intermediate if either declared final output is missing or unprotected.
- Do not ask for another cleanup confirmation.
- Return only the final cleaned `.xlsx` and `.csv` unless the user requested audit files before cleaning.
- Do not overwrite an existing phase or final output unless the user explicitly confirms that exact replacement.
