# Header Standardization Standard

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

### Amazon Profile

The registered `amazon` profile has this exact ordered signature: `标题`, `标题链接`, `图片`, `aprofile_链接`, `名称`, `aiconalt`, `查看`, `状态`, `查看1`, `asizebase`, `crhelpfultext`, `asizebase_链接`, and `asizebase2`. A workbook is not Amazon-preprocessed merely because it contains `名称`, `查看`, or any other familiar individual field; the whole source header row must match. It intentionally does not copy `crhelpfultext`, links, images, status fields, or any other source column.

Amazon Japan and Amazon US use this same one `amazon` profile. The region is a deterministic output-name/data-source display property only; it never selects a different header mapping or invokes a language/semantic classifier.

| Source field(s) | Configured operation | Preprocessing output |
| --- | --- | --- |
| `查看` | `amazon_review_date` | `评论日期`: a fixed `YYYY年M月D日在…发布评论` value becomes `YYYY-MM-DD`; an unexpected nonblank value is preserved unchanged rather than guessed. |
| `标题` + `查看1` | `join_trimmed` | `评论内容`: trimmed nonblank parts are joined in fixed order with one blank line (`\n\n`); if one part is blank, use the other part alone. |
| `aiconalt` | `amazon_star_rating` | `电商平台评分`: fixed `X 颗星，最多 5 颗星` text with `1 <= X <= 5` becomes the exact captured score text; unexpected nonblank input is preserved unchanged. |
| `asizebase` | `amazon_helpful_count` | `点赞数`: fixed `N 个人发现此评论有用` text becomes integer `N`; blank remains blank and unexpected nonblank input is preserved unchanged. |
| `名称` | `copy` | Temporary identity field only; it is used as the registered Amazon display-name input to derive `哈希ID`, then omitted from standard and cleaned outputs. |

The Amazon parser uses only the registered exact headers, fixed regular expressions, fixed source-field order, and fixed string joining. It never uses AI, translation, semantic inference, or row-level judgment.

### Twitter/X Profile

The registered `twitter` profile has one exact ordered signature: `id`, `created_at`, `full_text`, `media`, `screen_name`, `name`, `profile_image_url`, `user_id`, `in_reply_to`, `retweeted_status`, `quoted_status`, `media_tags`, `favorite_count`, `retweet_count`, `bookmark_count`, `quote_count`, `reply_count`, `views_count`, `favorited`, `retweeted`, `bookmarked`, `url`, and `metadata`.

The profile is selected only when the entire source header row has exactly that order and column count. A file is not routed as Twitter/X merely because it contains `user_id`, `full_text`, `created_at`, or another familiar field. `Twitter`, `twitter`, `X`, and `x` are fixed aliases for the one `twitter` profile.

| Source field | Configured operation | Preprocessing output |
| --- | --- | --- |
| `created_at` | `copy` | Temporary `评论日期`, then common standardization applies its fixed Beijing-date conversion. |
| `full_text` | `copy` | Temporary `评论内容`. |
| `favorite_count` | `copy` | Temporary `点赞数`. |
| `reply_count` | `copy` | Temporary `子评论数/追评数`. |
| `user_id` | `copy` | Temporary `Twitter用户ID`, used only as the registered stable account-ID input for `哈希ID`. |
| `screen_name` | `copy` | Temporary `Twitter昵称`, used only as the registered display-name fallback when the whole `Twitter用户ID` column is empty. |

`id`, `media`, `name`, `profile_image_url`, `in_reply_to`, `retweeted_status`, `quoted_status`, `media_tags`, `retweet_count`, `bookmark_count`, `quote_count`, `views_count`, `favorited`, `retweeted`, `bookmarked`, `url`, and `metadata` are intentionally omitted from the preprocessing output. The temporary Twitter identity fields are omitted from standardized and cleaned outputs, logs, and summaries after deterministic hash derivation. This profile never uses AI, source-value semantics, or partial-header matching.

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
| `参考になった数` | `rakuten_helpful_count` | `点赞数`: exact `N人` becomes integer `N`; blank remains blank and unexpected nonblank input is preserved unchanged. |
| `レビュー投稿者`, `投稿者名`, or `レビュアー名` | `rakuten_display_name` | Temporary `乐天市场昵称` used only for the approved Rakuten display-name hash. Exact trimmed `購入者さん` becomes blank and never produces a `哈希ID`; any other source display name is trimmed and used only in memory during common standardization. |

`注文日`, `カラー`, and every other Rakuten source field are intentionally omitted from the preprocessing output. `乐天市场昵称` is omitted from standardized and cleaned output, logs, and summaries after hash derivation. The Rakuten parser uses only the registered full signatures, fixed regular expressions, fixed source-field order, and fixed text handling. It never uses AI, translation, semantic inference, or row-level judgment.

### Mixed Rakuten Variant Batch Merge

Ordinary raw merge remains mandatory when all supplied files have the same original header signature. If it raises `HeaderMismatchError` because a confirmed Rakuten batch contains multiple listed variants, run the deterministic `--merge-registered-variants` mode instead. Every input worksheet must exactly match one of the five listed signatures; then each row is transformed with that variant's fixed operations and appended, in supplied input order, to one platform-preprocessed merged workbook using the shared temporary headers above.

This mode does not alter any original input, does not infer a missing field, and does not permit a partial signature or another platform profile. Its output goes directly into common standardization and is not preprocessed a second time.

## Required And Blank Columns

- `评论日期`, `评论内容`, and `点赞数` require one unambiguous source match.
- `产品名`, `电商平台评分`, `用户属性`, `子评论数/追评数`, `一级评论`, `二级评论`, and `三级评论` remain in the output when the source has no matching column; their values stay blank.
- `用户属性` retains a nonblank direct `用户属性` value. If that value is blank or the direct source column is absent, the script trims and joins nonblank registered `性别` then `年龄` values with one ASCII space. It never infers, translates, classifies, or completes an attribute.
- `电商平台评分` normally contains a source value from 1 through 5. Outside a registered platform-preprocessing parser, the script copies the configured source column as-is and does not validate, infer, round, or rewrite a rating. The Amazon profile's `amazon_star_rating` parser is a fixed, user-confirmed extraction exception; it does not infer or round a score. `用户属性` is a retained output field only and never a `哈希ID` identity source.
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
- Relative year values output only `YYYY`; relative month values output only `YYYY-MM`.
- Relative day and week values output `YYYY-MM-DD`.
- Do not infer missing month or day beyond the fixed relative-time granularity.

## Sensitive And Omitted Columns

The standardized workbook omits every column outside the standard schema. Confirmed sensitive, identity, and metadata headers include:

`IP地址`, `IP属地`, `用户名称`, `用户昵称`, `昵称`, `乐天市场昵称`, `rpid`, `parent_rpid`, `username`, `ip_location`, `id`, `comment_id`, `commentId`, `cid`, `uid`, `user_id`, `userId`, `uniqueId`, `author`, `authorName`, `author_name`, `authorDisplayName`, `authorChannelId`, `authorChannelUrl`, `channelId`, `channel_id`, `channelUrl`, `profileUrl`, `profile_url`, `avatar`, `videoId`, `video_id`, `videoUrl`, `url`, and `permalink`.

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
- Header selection is worksheet-wide and follows configuration order. It never falls back per row.
- Exact account-ID mappings:
  - YouTube: `author_channel_id`, then `authorChannelId`, then `Author Channel ID`.
  - 小红书: `用户ID`.
  - 亚马逊: none.
  - 乐天市场: none.
  - Twitter/X: `Twitter用户ID`.
- Exact display-name fallback mappings:
  - YouTube: `author`, then `author_name`.
  - 小红书: `用户名称`.
  - B站: `username`.
  - TikTok: `用户名`, then `昵称`; never `用户身份`.
  - 淘宝: `用户名称`, then `用户名`.
  - 京东: `用户名`.
  - 亚马逊: `名称`.
  - 乐天市场: `乐天市场昵称`.
  - Twitter/X: `Twitter昵称`.
- The same normalized display name in the same research project and platform produces the same hash regardless of which registered display-name header supplied it.
- Account-ID and display-name hashes use separate identity domains. Cross-project, cross-platform, and account-ID/display-name hashes differ.
- Display-name linkage is weak pseudonymization, not legal anonymization: nickname changes can split the same user, and different users with the same normalized name can merge.
- Raw account IDs, usernames, and nicknames remain omitted from standardized and cleaned outputs, logs, and summaries; approved identity values are read only in memory for hashing.
- `rpid`, `parent_rpid`, all comment IDs and parent IDs, URLs, profile links, IP fields, `用户身份`, source-provided `哈希ID`, and other ambiguous fields are never identity sources.
- Hashing and identity selection use deterministic tooling only; do not use AI.
- Hashing uses project-scoped, platform-isolated HMAC-SHA256 and emits 64 lowercase hexadecimal characters.
- The summary may contain project ID/name, platform, key version/fingerprint, identity type, source header, and counts. It must not contain a raw identity value or secret key.
