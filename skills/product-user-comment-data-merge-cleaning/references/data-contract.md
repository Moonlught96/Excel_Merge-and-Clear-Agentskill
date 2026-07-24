# Data Contract And Safety Boundaries

## Deterministic Processing Boundary

- Do not use AI or semantic judgment to map headers, split values, choose columns, reorder rows, delete comments, classify text, or infer dates/products.
- AI may call scripts, verify generated files, and report paths.
- Do not delete comments based on sentiment, quality, relevance, suspected advertising, tone, intent, or language-model judgment.
- Do not use fuzzy or semantic matching unless the user explicitly defines and approves a new rule.
- Do not use the old RPA canvas or a nonexistent Bazhuayu CLI.

## Input Contract

- Supported inputs are `.xlsx`, `.xlsm`, and `.csv`.
- Duplicate input paths are rejected before merge; the same file must never be appended twice in one invocation.
- CSV inputs must use the deterministic compatibility layer.
- CSV decoding supports UTF-8 with or without BOM, BOM-marked UTF-16, and GB18030. It must fail instead of guessing an unregistered encoding.
- Preserve CSV cell values as text. Do not infer numeric, date, ID, or timestamp types while loading CSV.
- CSV values beginning with `=` must remain text cells when written to XLSX during merge, reply-prefix processing, standardization, or direct cleaning; they must not be promoted to Excel formulas. Genuine formula cells from XLSX/XLSM inputs remain formulas because Excel inputs are read with `data_only=False`.
- Process every worksheet in each workbook.
- Treat row 1 as the header row and data as beginning at row 2.
- During merge, B站 reply-prefix stripping, and standardization, load workbook formulas as formulas (`data_only=False`) so missing cached values do not turn formulas into blanks.
- Never modify an original input workbook or CSV file.

## Platform Preprocessing Contract

- Platform preprocessing is a deterministic splitter before common standardization. Its profiles are stored in `config/platform-preprocessing.json`.
- A platform may register one legacy `header_signature` or multiple named exact variants. A variant may run only after the source header row is exactly equal, including header order and column count, to its registered `header_signature`. Extra, missing, repeated, reordered, blank, or renamed columns fail the signature. No AI, semantic matching, spelling similarity, row content, or fuzzy matching is allowed.
- The current `amazon` profile has the ordered `header_signature` `标题`, `标题链接`, `图片`, `aprofile_链接`, `名称`, `aiconalt`, `查看`, `状态`, `查看1`, `asizebase`, `crhelpfultext`, `asizebase_链接`, and `asizebase2`; the full fixed mappings are in `header-standardization.md`.
- The current `rakuten` profile has five registered named variants: `reviewer-title-body-review-date`, `reviewer-date-body-title`, `title-review-date-body-reviewer`, `poster-title-body-review-date`, and `reviewer-name-title-content`. Their full signatures and deterministic output rules are in `header-standardization.md`; a single shared header never selects a Rakuten variant.
- The current `twitter` profile has one exact registered signature. Its complete signature, temporary mapping, hash-input fields, and omission rules are in `header-standardization.md`; it never routes from a partial Twitter/X-like header set.
- Existing fixed platform aliases remain in `config/header-standardizer.json` until an explicitly confirmed profile migration. An unregistered platform must not be guessed into an existing profile.
- A profile must write a new temporary `.xlsx` and summary. It must not overwrite the raw input, raw merged workbook, or B站 prefix-stripped workbook.
- If no configured signature matches when the splitter is invoked, stop with `No configured platform signature matched`. Do not fall back to an unrelated profile.
- Profile output may retain an approved raw identity field only in the temporary workbook required for in-memory hash derivation. The common standardizer must omit that field from the standardized output, cleaned output, logs, and summaries.
- When a confirmed registered platform batch has multiple exact variants and the ordinary raw merge raises `HeaderMismatchError`, the splitter may run with `--merge-registered-variants`. It must validate every input sheet against one registered variant, require an identical ordered preprocessing output schema across those variants, and create one platform-preprocessed merged workbook. This is the only exception to the raw-merge-only path; it does not modify source files, does not use row-level inference, and must not be applied to unregistered or partially matching headers. Do not fall back to another profile.

## Standard Output Data Contract

The standardized workbook contains exactly these columns in this order:

`评论日期`、`评论内容`、`产品名`、`电商平台评分`、`用户属性`、`哈希ID`、`点赞数`、`子评论数/追评数`、`一级评论`、`二级评论`、`三级评论`

- Move each matched source header and all values below it together. Standardization must not only rename header text.
- For `产品名`, preserve a nonblank mapped source value. Only when the mapped product field is absent or blank may the deterministic `--product-name` value confirmed at the naming gate be written; it must be used literally and must not overwrite a nonblank source value or be inferred from comments.
- `电商平台评分` and `用户属性` are optional retained columns. Copy only a configured exact rating header and its complete source column; leave the output column blank when the source column is absent.
- `用户属性` is deterministic only: retain a nonblank direct `用户属性` source value; otherwise join nonblank registered `性别` then `年龄` source values after trimming their outer whitespace, using one ASCII space. Do not infer, supplement, translate, classify, or semantically rewrite values. If all registered sources are blank or absent, leave the output blank.
- E-commerce ratings normally use the source range 1-5. Outside a registered platform-preprocessing parser, the tool does not validate, infer, round, or rewrite a rating. A user-confirmed profile may use a fixed parser such as Amazon's `amazon_star_rating` or copy an exact raw rating field such as Rakuten `評価`; it must preserve unmatched source text rather than infer or round it. It must never infer user attributes.
- `电商平台评分` and `用户属性` are never identity sources and must not affect `哈希ID` selection or derivation.
- Omit raw account IDs, usernames, nicknames, IP, profile, and link metadata. A registered identity column may be read only in memory to generate `哈希ID`; its raw column is never copied to standardized or cleaned output.
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
- A platform-preprocessed merged workbook is a distinct current-run intermediate used only after the documented `HeaderMismatchError` exception. It contains only the fixed temporary columns from the confirmed platform profile and then enters common standardization directly; it is not a change to the ordinary raw merge contract.

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
- Existing outputs are rejected by CLI unless `--overwrite` is supplied after explicit confirmation.
- Output workbooks, CSV files, logs, and summaries are staged beside their destination and atomically replaced only after a successful write.

## Standardized Output Audit Contract

- Immediately after standardization, run `scripts/audit_standardized_comments.py` against the standardized workbook and the exact source workbook supplied to standardization.
- The audit checks only deterministic structure: fixed output header order, duplicate/unexpected identity headers, 64-character lowercase hexadecimal nonblank `哈希ID` values, worksheet name/order, and source-to-output row counts.
- The audit must not read, expose, classify, translate, or judge comment text or raw identity values. Its JSON report contains only paths, sheet names, counts, headers, and issue codes.
- A failed audit blocks the user-confirmation, KOL, and cleaning phases. A passed audit does not remove the existing user confirmation of the standardized workbook.
- The audit JSON is a current-run intermediate. Delete it with other intermediate outputs after successful cleaning unless the user explicitly asked to retain audit artifacts before cleaning.

## Twitter/X Keep-Keyword Filter Contract

- This contract applies only after a registered `twitter` preprocessing profile has matched, standardization/audit have passed, and the user has approved the standardized workbook.
- It runs before the universal KOL clean-word and common-cleaning stages. It is defined in detail in `twitter-x-keyword-filter.md`.
- The user must provide one or more nonblank keep keywords and explicitly confirm that the list is complete before execution.
- For each worksheet, the filter requires exactly one `评论内容` header and retains a row only when its comment contains at least one confirmed literal keyword through Unicode casefolded substring matching.
- Missing target headers, duplicate target headers, or an empty keyword list stop without output. No AI, translation, semantic relevance judgment, fuzzy match, synonym expansion, or unconfirmed keyword is allowed.
- It writes a separate temporary filtered workbook and summary; those paths are explicit cleanup intermediates after successful final output verification.

## Hash ID Pseudonymization Contract

- `哈希ID` is deterministic pseudonymization, not legal anonymization.
- Stable account ID is selected first for the whole worksheet when a registered account-ID column contains at least one nonblank value.
- Display-name fallback is allowed only when no registered account-ID column contains any nonblank value.
- Display-name normalization trims outer whitespace only.
- It preserves case, internal whitespace, punctuation, and Unicode code points.
- Do not apply Unicode normalization, full-width/half-width conversion, traditional/simplified Chinese conversion, or fuzzy matching.
- Selection is worksheet-wide, not row-by-row. Once a nonblank account-ID column is selected, a blank account-ID cell in an individual row stays blank and must not fall back to a display name from that row.
- Use HMAC-SHA256 with the protected key for the confirmed research project and a platform namespace.
- The same project, platform, identity type, and normalized identity value produces the same 64-character lowercase hexadecimal value.
- The same normalized display name in the same research project and platform produces the same hash regardless of whether the registered source header is `username`, `用户名`, `昵称`, `用户名称`, `author`, or `author_name`.
- `YouTube` and `YouTube Shorts` resolve to the same `youtube` platform namespace. They must not create separate hash domains for the same research project.
- `乐天市场`, `Rakuten`, and `rakuten` resolve to the same `rakuten` platform namespace. `乐天市场昵称` is an approved temporary display-name input only after a configured Rakuten preprocessing variant has produced it; exact `購入者さん` is blanked before hash selection and never produces a hash.
- `Twitter`, `twitter`, `X`, and `x` resolve to the same `twitter` platform namespace. Temporary `Twitter用户ID` is the stable account-ID source; only when that complete worksheet column is empty may temporary `Twitter昵称` be selected as the display-name fallback.
- Account-ID and display-name hashes use separate identity domains, so the same text hashed once as an account ID and once as a display name produces different values.
- Cross-project and cross-platform hashes differ.
- Display-name linkage is weak pseudonymization, not legal anonymization: nickname changes can split the same user, and different users with the same normalized name can merge.
- Raw account IDs, usernames, and nicknames remain omitted from standardized and cleaned outputs, logs, and summaries, even when an approved source field is read only in memory for hashing.
- Comment IDs, parent-comment IDs, URLs, profile links, IP fields, source-provided `哈希ID`, `用户身份`, and other ambiguous identity fields are never identity sources.
- `用户身份` is never an identity source.
- Do not expose raw identity values or secret keys in output, logs, summaries, errors, tests, or Git. Keep raw source files access-controlled.
- Existing merge, cleaning, naming, confirmation, and retention rules remain unchanged.
- The transformation and header selection are deterministic tools only; do not use AI.
