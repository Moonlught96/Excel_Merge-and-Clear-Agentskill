# Header Standardization Standard

## Contents

- [Standard Output Schema](#standard-output-schema)
- [Fixed Header Aliases](#fixed-header-aliases)
- [Platform Preprocessing Profiles](#platform-preprocessing-profiles)
  - [Amazon Japan And Amazon US Profiles](#amazon-japan-and-amazon-us-profiles)
  - [Twitter/X Post And Comment Profiles](#twitterx-post-and-comment-profiles)
  - [Reddit Profile](#reddit-profile)
  - [Rakuten Market Profile](#rakuten-market-profile)
  - [Mixed Rakuten Variant Batch Merge](#mixed-rakuten-variant-batch-merge)
- [Required And Blank Columns](#required-and-blank-columns)
- [Taobao Date And Product Split](#taobao-date-and-product-split)
- [Date And Time Conversion](#date-and-time-conversion)
- [Sensitive And Omitted Columns](#sensitive-and-omitted-columns)
- [Output And Summary](#output-and-summary)
- [Hash ID Derivation](#hash-id-derivation)

## Standard Output Schema

Standardization outputs only these columns, in this exact order:

1. `评论日期`
2. `评论内容`
3. `产品名`
4. `电商平台评分`
5. `用户属性`
6. `哈希ID`
7. `点赞数`
8. `子评论数/追评数`
9. `一级评论`
10. `二级评论`
11. `三级评论`

Standardization must move the matched header and its complete column data together. It must not merely rename or reorder header text.

## Fixed Header Aliases

Only exact aliases registered in `config/header-standardizer.json` may be used.

- `评论日期`: `评论日期`, `评论时间`, `评论日期与产品`, `timestamp`, `createTime`, `create_time`, `createdAt`, `created_at`, `createDate`, `create_date`, `publishedAt`, `published_at`, `publishedTime`, `published_time`, `published`, `date`, `Date`, `time`, `Time`, `commentTime`, `comment_time`, `Comment Published`, `Published At`
- `评论内容`: `评论内容`, `评论`, `content`, `text`, `Text`, `comment`, `Comment`, `commentText`, `comment_text`, `Comment Text`, `message`, `body`
- `产品名`: `产品名`, `购买产品`, `商品名称`, `商品`, `评论日期与产品`
- `电商平台评分`: `电商平台评分`
- `用户属性`: direct `用户属性`; otherwise deterministic composite source headers `性别` then `年龄`
- `点赞数`: `点赞数`, `点赞量`, `Digg Count`, `like_count`, `likeCount`, `Like Count`, `likes`, `Likes`, `diggCount`, `digg_count`
- `子评论数/追评数`: `子评论数/追评数`, `子评论数`, `子评论数（追评数）`, `追评数`, `评论数`, `回复数`, `replyCount`, `reply_count`, `Reply Count`, `replyCommentTotal`, `reply_comment_total`, `replies`, `Replies`
- `一级评论`: `一级评论`, `一级评论内容`, `追评`, `replyText`, `reply_text`, `Reply Text`
- `二级评论`: `二级评论`, `二级评论内容`, `引用的评论内容`
- `三级评论`: `三级评论`, `三级评论内容`

Do not use AI, semantic similarity, spelling similarity, or content inspection to infer an unregistered alias. If the user confirms a new alias, add it only to the matching `aliases` entry.

## Platform Preprocessing Profiles

`config/platform-preprocessing.json` is the deterministic platform splitter used before the common standardizer. A registered platform may contain one legacy `header_signature` or multiple named exact variants. A variant is selected only when its complete ordered `header_signature` exactly equals the source header row. Extra, missing, duplicate, reordered, blank, or renamed headers reject the profile. It is not a fuzzy classifier and it does not inspect comment meaning.

- Existing confirmed platforms continue to use their existing fixed aliases in `config/header-standardizer.json` until the user explicitly approves a profile migration.
- New platform-specific raw-field transformations belong in a separate profile, not in the common alias list.
- When the selected profile does not match, the tool stops with `No configured platform signature matched`; it must not guess a different platform.
- A profile writes a separate temporary workbook. The common standardizer then only applies the locked final column order, sensitive-field omission, and hash-ID rules.

### Amazon Japan And Amazon US Profiles

`amazon-japan` and `amazon-us` are separate deterministic platform profiles and separate hash namespaces. `amazon-japan` has one named `default` variant requiring this exact 13-column ordered signature: `标题`, `标题链接`, `图片`, `aprofile_链接`, `名称`, `aiconalt`, `查看`, `状态`, `查看1`, `asizebase`, `crhelpfultext`, `asizebase_链接`, and `asizebase2`. `amazon-us` requires this exact 10-column ordered signature: `标题`, `标题链接`, `图片`, `aprofile_链接`, `名称`, `aiconalt`, `查看`, `状态`, `查看1`, and `asizebase`. A workbook is not routed by a familiar individual field; its whole source header row must exactly equal the registered profile selected from the confirmed region.

Japan parses `查看` as `评论日期`. US has no confirmed date source, so it uses the fixed `empty` operation and outputs a blank `评论日期`; it must never parse or infer a date from `查看`. Both profiles use `标题` plus `查看1` for comment content, `aiconalt` for e-commerce rating, `asizebase` for likes, and `名称` only as the temporary display-name source for `哈希ID`. They intentionally do not copy links, images, status fields, auxiliary columns, or any other source column.

| Source field(s) | Configured operation | Preprocessing output |
| --- | --- | --- |
| Japan `查看` | `amazon_review_date` | `评论日期`: a fixed `YYYY年M月D日在…发布评论` value becomes `YYYY-MM-DD`; an unexpected nonblank value is preserved unchanged rather than guessed. |
| US `评论日期` | `empty` | No registered source date exists; always output a blank value. |
| `标题` + `查看1` | `join_trimmed` | `评论内容`: trimmed nonblank parts are joined in fixed order with one blank line (`\n\n`); if one part is blank, use the other part alone. |
| `aiconalt` | `amazon_star_rating` | `电商平台评分`: preprocessing recognizes the fixed Japanese-interface `X 颗星，最多 5 颗星` form. The common post-mapping normalizer used by every platform additionally converts exact `N out of 5 stars` and the Japanese form to numeric `N`; unexpected nonblank input is preserved unchanged. |
| `asizebase` | `amazon_helpful_count` | `点赞数`: preprocessing recognizes fixed `N 个人发现此评论有用`. The common post-mapping normalizer used by every platform additionally converts exact `One person found this helpful` and `N person/people found this helpful` to integer `N`; blank remains blank at this temporary preprocessing stage, then common standardization writes numeric `0`; unexpected nonblank input is preserved unchanged. |
| `名称` | `copy` | Temporary identity field only; it is used as the registered Amazon display-name input to derive `哈希ID`, then omitted from standard and cleaned outputs. |

The Amazon parser uses only the registered exact headers, fixed regular expressions, fixed source-field order, and fixed string joining. It never uses AI, translation, semantic inference, or row-level judgment.

### Twitter/X Post And Comment Profiles

The registered `twitter` X 推文 profile and the registered `twitter-comments` X 评论 profile each have the same exact ordered signature: `id`, `created_at`, `full_text`, `media`, `screen_name`, `name`, `profile_image_url`, `user_id`, `in_reply_to`, `retweeted_status`, `quoted_status`, `media_tags`, `favorite_count`, `retweet_count`, `bookmark_count`, `quote_count`, `reply_count`, `views_count`, `favorited`, `retweeted`, `bookmarked`, `url`, and `metadata`.

The same signature is intentional because these exports have the same physical format. A file is not routed as Twitter/X merely because it contains `user_id`, `full_text`, `created_at`, or another familiar field. The user must first select `推文` or `评论`; that selection passes `twitter` or `twitter-comments` explicitly. Automatic signature detection sees both profiles and stops as ambiguous rather than guessing. `Twitter`, `twitter`, `X`, and `x` are aliases for the `twitter` X 推文 profile; `twitter-comments` is the explicit X 评论 route label.

| Source field | Configured operation | Preprocessing output |
| --- | --- | --- |
| `created_at` | `copy` | Temporary `评论日期`, then common standardization applies its fixed Beijing-date conversion. |
| `full_text` | `copy` | Temporary `评论内容`. |
| `favorite_count` | `copy` | Temporary `点赞数`; a blank value remains blank at this temporary preprocessing stage, then common standardization writes numeric `0`. |
| `reply_count` | `copy` | Temporary `子评论数/追评数`. |
| `user_id` | `copy` | Temporary `Twitter用户ID`, used only as the registered stable account-ID input for `哈希ID`. |
| `screen_name` | `copy` | Temporary `Twitter昵称`, used only as the registered display-name fallback when the whole `Twitter用户ID` column is empty. |

`id`, `media`, `name`, `profile_image_url`, `in_reply_to`, `retweeted_status`, `quoted_status`, `media_tags`, `retweet_count`, `bookmark_count`, `quote_count`, `views_count`, `favorited`, `retweeted`, `bookmarked`, `url`, and `metadata` are intentionally omitted from either preprocessing output. The temporary Twitter identity fields are omitted from standardized and cleaned outputs, logs, and summaries after deterministic hash derivation. `twitter-comments` and `twitter` share the confirmed `twitter` hash namespace, so equal `user_id` values in the same project receive equal hash IDs; only `twitter` runs the X 推文 keep-keyword filter. Both profiles use no AI, source-value semantics, or partial-header matching.

### Reddit Profile

The registered `reddit` profile has one exact ordered signature: `记录类型`, `标题`, `作者`, `时间`, `内容`, `点赞数`, `评论/回复数`, `层级`, `是否回复`, `评论ID`, and `父ID`. `Reddit` and `reddit` are fixed aliases for the one `reddit` profile. The profile is selected only when the complete source header row has exactly that order and column count; a familiar field such as `作者`, `内容`, `评论ID`, or `父ID` alone never selects it.

| Source field(s) | Configured operation | Preprocessing output |
| --- | --- | --- |
| `时间` | `copy` | Temporary `评论日期`, then common standardization applies its existing fixed Beijing-date conversion. |
| `标题` + `内容` | `join_trimmed` | `评论内容`: trimmed nonblank parts are joined in fixed order with one blank line (`\n\n`); ordinary comment rows with a blank `标题` retain only `内容`. |
| `点赞数` | `copy` | Temporary `点赞数`; a blank value remains blank at this temporary stage, then common standardization writes numeric `0`. |
| `评论/回复数` | `copy` | Temporary `子评论数/追评数`. |
| `作者` | `copy` | Temporary `Reddit作者`, used only as the approved weak display-name fallback for `哈希ID`. |

`记录类型`, `层级`, `是否回复`, `评论ID`, and `父ID` are intentionally omitted from the preprocessing output. Every source row, including the one main post and all comments/replies, remains one independent output row in the original order. The profile does not move reply text into `一级评论`/`二级评论`/`三级评论`, copy a parent comment, infer a hierarchy, or associate a child with its parent. `Reddit作者` is omitted from standardized and cleaned outputs, logs, and summaries after deterministic hash derivation. This profile uses only fixed header equality, fixed column copies, and fixed joining; it never uses AI, semantic inference, or fuzzy matching.

### Rakuten Market Profile

The registered `rakuten` profile has 5 named exact variants. A match is valid only for one whole listed header row; a familiar field such as `レビュー本文`, `投稿日`, or `レビュー投稿者` alone never selects this profile.

| Variant | Exact ordered signature |
| --- | --- |
| `reviewer-title-body-review-date` | `レビュータイトル`, `評価`, `レビュー本文`, `レビュー投稿者`, `レビュー投稿日`, `注文日`, `レビュアー属性`, `参考になった数` |
| `reviewer-date-body-title` | `レビュー投稿者`, `評価`, `投稿日`, `レビュー本文`, `レビュータイトル`, `レビュアー属性`, `参考になった数` |
| `title-review-date-body-reviewer` | `レビュータイトル`, `評価`, `レビュー投稿日`, `レビュー本文`, `レビュー投稿者`, `注文日`, `レビュアー属性`, `参考になった数` |
| `poster-title-body-review-date` | `レビュータイトル`, `評価`, `レビュー投稿日`, `投稿者名`, `レビュー本文`, `レビュアー属性`, `参考になった数` |
| `reviewer-name-title-content` | `レビュアー名`, `評価`, `投稿日`, `カラー`, `レビュータイトル`, `レビュー内容`, `レビュアー属性`, `参考になった数` |

Each Rakuten variant writes the same temporary columns in this order: `评论日期`, `评论内容`, `电商平台评分`, `用户属性`, `点赞数`, `乐天市场昵称`.

| Source field(s) | Configured operation | Preprocessing output |
| --- | --- | --- |
| `レビュー投稿日` or `投稿日` | `rakuten_review_date` | `评论日期`: exact `M/D/YYYY`, `YYYY/M/D`, `YYYY-M-D`, or an actual Excel date becomes `YYYY-MM-DD`. Any unexpected nonblank value is preserved unchanged. |
| `レビュータイトル` + `レビュー本文` or `レビュー内容` | `join_trimmed` | `评论内容`: trimmed nonblank parts are joined in fixed title-then-body order with one blank line (`\n\n`). It does not deduplicate equal title/body text. |
| `評価` | `copy` | `电商平台评分`: source value is copied as captured; no range inference, rounding, or rewrite is performed. |
| `レビュアー属性` | `rakuten_user_attribute` | `用户属性`: only fixed `男性` or `女性` and fixed numeric age tokens such as `50代`, `70代以上`, `30歳`, or `30才` are retained, joined with one ASCII space. All other portions, including `自分用｜実用品・普段使い｜はじめて`, are omitted. If no registered gender/age token exists, leave blank. |
| `参考になった数` | `rakuten_helpful_count` | `点赞数`: exact `N人` becomes integer `N`; blank remains blank at this temporary preprocessing stage, then common standardization writes numeric `0`; unexpected nonblank input is preserved unchanged. |
| `レビュー投稿者`, `投稿者名`, or `レビュアー名` | `rakuten_display_name` | Temporary `乐天市场昵称` used only for the approved Rakuten display-name hash. Exact trimmed `購入者さん` becomes blank and never produces a `哈希ID`; any other source display name is trimmed and used only in memory during common standardization. |

`注文日`, `カラー`, and every other Rakuten source field are intentionally omitted from the preprocessing output. `乐天市场昵称` is omitted from standardized and cleaned output, logs, and summaries after hash derivation. The Rakuten parser uses only the registered full signatures, fixed regular expressions, fixed source-field order, and fixed text handling. It never uses AI, translation, semantic inference, or row-level judgment.

### Mixed Rakuten Variant Batch Merge

Ordinary raw merge remains mandatory when all supplied files have the same original header signature. If it raises `HeaderMismatchError` because a confirmed Rakuten batch contains multiple listed variants, run the deterministic `--merge-registered-variants` mode instead. Every input worksheet must exactly match one of the five listed signatures; then each row is transformed with that variant's fixed operations and appended, in supplied input order, to one platform-preprocessed merged workbook using the shared temporary headers above.

This mode does not alter any original input, does not infer a missing field, and does not permit a partial signature or another platform profile. Its output goes directly into common standardization and is not preprocessed a second time.

## Required And Blank Columns

- `评论日期` and `评论内容` require one unambiguous source match.
- `点赞数` is always retained. When its configured source column is absent, or a mapped cell is null/empty/whitespace-only, common standardization writes numeric `0`. Across all platforms, an already numeric value, digits-only text, exact `One person found this helpful`, exact `N person/people found this helpful`, or exact `N 个人发现此评论有用` is written as numeric `N`; unmatched nonblank values remain unchanged and are never guessed, translated, or abbreviated.
- `产品名`, `电商平台评分`, `用户属性`, `子评论数/追评数`, `一级评论`, `二级评论`, and `三级评论` remain in the output when the source has no matching column; their values stay blank.
- `用户属性` retains a nonblank direct `用户属性` value. If that value is blank or the direct source column is absent, the script trims and joins nonblank registered `性别` then `年龄` values with one ASCII space. It never infers, translates, classifies, or completes an attribute.
- `电商平台评分` normally contains a source value from 1 through 5. Across all platforms, an already numeric value, exact `N out of 5 stars`, or exact `N 颗星，最多 5 颗星` is written as numeric `N` when the fixed textual score is in the 1-5 range; a whole number is written as an integer and a fractional rating remains numeric. Other nonblank values remain unchanged and are not validated, inferred, rounded, translated, or semantically interpreted. The Amazon profile's `amazon_star_rating` parser is a fixed, user-confirmed extraction step before this common normalizer. `用户属性` is a retained output field only and never a `哈希ID` identity source.
- `子评论数/追评数` is required in the standard output schema even when the source header is absent.
- If a required source header is missing or any standard column matches more than one source column, stop and report the actual headers. Do not guess.
- Do not infer `四级评论` or deeper levels unless the user explicitly extends the fixed schema.

## Taobao Date And Product Split

For the source header `评论日期与产品`, use only this fixed parser:

- A leading `YYYY年M月D日`, `YYYY/M/D`, or `YYYY-M-D` becomes `评论日期`.
- Text after the optional fixed marker `已购：` becomes `产品名`.
- If the value does not match the fixed date-leading pattern, preserve the original value in `评论日期` and leave `产品名` blank.
- If the source has `产品名`, `购买产品`, `商品名称`, or `商品`, map that source column directly instead.

Do not use AI or semantic judgment to split product names.

## Date And Time Conversion

- Platform time aliases accept deterministic Unix seconds, Unix milliseconds, ISO timestamps, and configured relative-time formats.
- Eight-digit `YYYYMMDD` values are parsed as calendar dates before Unix timestamp detection.
- Convert absolute platform timestamps to Beijing date (`UTC+8`) in `YYYY-MM-DD` format.
- Keep only year, month, and day; do not output hours, minutes, or seconds.
- For Chinese `评论时间` or `评论日期`, convert only numeric timestamps or date-time text that includes a time component. Preserve plain date-only text as provided.
- Relative platform time values such as `1年前`, `9个月前`, `1 year ago`, and `9 months ago` are converted deterministically from the current Beijing date.
- Before a configured relative, ISO, or fixed date parser runs, either known literal trailing suffix `(edited)` or `（修改过）` is removed only for parsing. Unknown suffixes and unmatched nonblank values remain unchanged.
- Relative year values output only `YYYY`; relative month values output only `YYYY-MM`.
- Relative day and week values output `YYYY-MM-DD`.
- Do not infer missing month or day beyond the fixed relative-time granularity.

## Sensitive And Omitted Columns

The standardized workbook omits every column outside the standard schema. Confirmed sensitive, identity, and metadata headers include:

`IP地址`, `IP属地`, `用户名称`, `用户昵称`, `昵称`, `乐天市场昵称`, `Reddit作者`, `rpid`, `parent_rpid`, `username`, `ip_location`, `id`, `comment_id`, `commentId`, `评论ID`, `父ID`, `cid`, `uid`, `user_id`, `userId`, `uniqueId`, `author`, `作者`, `authorName`, `author_name`, `authorDisplayName`, `authorChannelId`, `authorChannelUrl`, `channelId`, `channel_id`, `channelUrl`, `profileUrl`, `profile_url`, `avatar`, `videoId`, `video_id`, `videoUrl`, `url`, and `permalink`.

These raw columns remain omitted from standardized and cleaned outputs even when `config/hash-id.json` registers one of them as an in-memory identity source. Registration permits only deterministic hashing; it never preserves the raw column.

`parent_rpid` is a parent-comment ID, not a subcomment count. Never map it to `子评论数/追评数`.

Unknown columns that are not configured standard aliases are omitted. They are not guessed into the standard schema.

## Output And Summary

- Never overwrite the original or raw merged workbook.
- Process every worksheet with row 1 as the header.
- Preserve formulas as formulas with `data_only=False`.
- Export a separate standardized `.xlsx`.
- Record selected, omitted, and configured dropped headers in `.standardized.summary.json`.

## Hash ID Derivation

- `哈希ID` is always generated; never map or preserve a source column named `哈希ID`.
- Platform and research-project context are required whenever a registered account-ID or display-name column is selected.
- Stable account ID is selected first for the whole worksheet when a registered account-ID column contains at least one nonblank value.
- Display-name fallback is allowed only when no registered account-ID column contains any nonblank value.
- The literal exporter null marker `None` is blank only for stable account-ID selection, after trimming outer whitespace and case-folding. It never blanks a literal display name; an all-`None` account-ID column therefore permits the configured worksheet-wide display-name fallback.
- Header selection is worksheet-wide and follows configuration order. It never falls back per row.
- Exact account-ID mappings:
  - YouTube: `author_channel_id`, then `authorChannelId`, then `Author Channel ID`.
  - 小红书: `用户ID`.
  - 亚马逊日本: none.
  - 亚马逊美国: none.
  - 乐天市场: none.
  - Twitter/X 推文和 X 评论: `Twitter用户ID`.
  - Reddit: none.
- Exact display-name fallback mappings:
  - YouTube: `author`, then `author_name`.
  - 小红书: `用户名称`.
  - B站: `username`.
  - TikTok: `用户名`, then `昵称`; never `用户身份`.
  - 淘宝: `用户名称`, then `用户名`.
  - 京东: `用户名`.
  - 亚马逊日本: `名称`.
  - 亚马逊美国: `名称`.
  - 乐天市场: `乐天市场昵称`.
  - Twitter/X 推文和 X 评论: `Twitter昵称`.
  - Reddit: `Reddit作者`.
- The same normalized display name in the same research project and platform produces the same hash regardless of which registered display-name header supplied it.
- Account-ID and display-name hashes use separate identity domains. Cross-project, cross-platform, and account-ID/display-name hashes differ.
- Display-name linkage is weak pseudonymization, not legal anonymization: nickname changes can split the same user, and different users with the same normalized name can merge.
- Raw account IDs, usernames, and nicknames remain omitted from standardized and cleaned outputs, logs, and summaries; approved identity values are read only in memory for hashing.
- `rpid`, `parent_rpid`, all comment IDs and parent IDs, URLs, profile links, IP fields, `用户身份`, source-provided `哈希ID`, and other ambiguous fields are never identity sources.
- Hashing and identity selection use deterministic tooling only; do not use AI.
- Hashing uses project-scoped, platform-isolated HMAC-SHA256 and emits 64 lowercase hexadecimal characters.
- The summary may contain project ID/name, platform, key version/fingerprint, identity type, source header, and counts. It must not contain a raw identity value or secret key.
