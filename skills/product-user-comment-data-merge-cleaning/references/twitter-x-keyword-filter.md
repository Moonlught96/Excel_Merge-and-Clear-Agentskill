# Twitter/X Keep-Keyword Retention Filter

## Scope And Order

This is a platform-specific deterministic filter for the registered `twitter` preprocessing profile only. `Twitter`, `twitter`, `X`, and `x` are fixed aliases for the same profile and the same `twitter` hash namespace.

Run it only after all of the following have occurred:

1. the exact Twitter/X preprocessing signature has matched;
2. common standardization has completed;
3. the standardized-output audit has passed; and
4. the user has approved the standardized workbook.

It runs before the universal KOL clean-word gate and before `clean_excel_comments.py`. It does not replace KOL clean words, fixed delete words, duplicate rules, or any common cleaner rule.

## Confirmation Gate

Ask exactly:

```text
请提供本轮 Twitter/X 评论保留关键词。仅保留“评论内容”包含任一关键词的整行数据；请一次性提供所有关键词。
```

After one or more keywords are supplied, ask exactly:

```text
是否已经提供完成所有 Twitter/X 保留关键词？你确认后我将执行关键词筛选，再进入通用 KOL 清理词与清洗流程。
```

Do not run the filter before the user explicitly confirms the list is complete. At least one nonblank keyword is required; an empty keyword list is a deterministic configuration error and does not mean “keep all rows.”

## Deterministic Matching Contract

- Invoke `scripts/filter_comments_by_keywords.py` using one `--keep-keyword` argument per confirmed keyword.
- The input must contain exactly one `评论内容` header per worksheet. Missing or duplicate target headers stop the run without an output.
- Trim outer whitespace from each keyword, remove duplicate keywords by Unicode `casefold()` key while preserving the first confirmed spelling, and compare with a Unicode `casefold()` literal substring check.
- A row is retained only when its `评论内容` contains at least one confirmed keyword. A blank comment or a comment with no match causes that complete row to be deleted.
- The filter does not translate, segment, normalize Unicode, expand abbreviations, infer product references, score relevance, use regular-expression guesses, or apply semantic/fuzzy/AI matching.
- It preserves every cell in a retained row exactly as loaded. It changes only row membership in a new output workbook.

For example, the confirmed keyword `screenbar` retains `ScreenBar` through deterministic case folding. It does not retain a comment that is merely related to a monitor lamp unless the literal keyword is present.

## Output, Privacy, And Cleanup

- The filter writes a new temporary `.xlsx` plus `.keyword-filter.summary.json`; it never overwrites the standardized workbook or an original input.
- The summary contains only paths, target header, confirmed keywords, workbook/sheet counts, and retained/deleted row counts. It must not contain raw comments, raw account IDs, nicknames, or hash secret material.
- Pass the filtered workbook to the universal KOL and common-cleaning scripts.
- After final cleaned `.xlsx` and `.csv` verification, explicitly delete the temporary filtered workbook and its summary with the other current-run intermediates. Protect original inputs and final outputs.

All filtering is pure deterministic tooling. Do not use AI at any point in this stage.
