# Header Standardization Standard

## Standard Output Schema

Standardization outputs only these columns, in this exact order:

1. `评论日期`
2. `评论内容`
3. `产品名`
4. `哈希ID`
5. `点赞数`
6. `子评论数/追评数`
7. `一级评论`
8. `二级评论`
9. `三级评论`

Standardization must move the matched header and its complete column data together. It must not merely rename or reorder header text.

## Fixed Header Aliases

Only exact aliases registered in `config/header-standardizer.json` may be used.

- `评论日期`: `评论日期`, `评论时间`, `评论日期与产品`, `timestamp`, `createTime`, `create_time`, `createdAt`, `created_at`, `createDate`, `create_date`, `publishedAt`, `published_at`, `publishedTime`, `published_time`, `published`, `date`, `Date`, `time`, `Time`, `commentTime`, `comment_time`, `Comment Published`, `Published At`
- `评论内容`: `评论内容`, `评论`, `content`, `text`, `Text`, `comment`, `Comment`, `commentText`, `comment_text`, `Comment Text`, `message`, `body`
- `产品名`: `产品名`, `购买产品`, `商品名称`, `商品`, `评论日期与产品`
- `点赞数`: `点赞数`, `点赞量`, `Digg Count`, `like_count`, `likeCount`, `Like Count`, `likes`, `Likes`, `diggCount`, `digg_count`
- `子评论数/追评数`: `子评论数/追评数`, `子评论数`, `子评论数（追评数）`, `追评数`, `评论数`, `回复数`, `replyCount`, `reply_count`, `Reply Count`, `replyCommentTotal`, `reply_comment_total`, `replies`, `Replies`
- `一级评论`: `一级评论`, `一级评论内容`, `追评`, `replyText`, `reply_text`, `Reply Text`
- `二级评论`: `二级评论`, `二级评论内容`, `引用的评论内容`
- `三级评论`: `三级评论`, `三级评论内容`

Do not use AI, semantic similarity, spelling similarity, or content inspection to infer an unregistered alias. If the user confirms a new alias, add it only to the matching `aliases` entry.

## Required And Blank Columns

- `评论日期`, `评论内容`, and `点赞数` require one unambiguous source match.
- `产品名`, `子评论数/追评数`, `一级评论`, `二级评论`, and `三级评论` remain in the output when the source has no matching column; their values stay blank.
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
- Convert absolute platform timestamps to Beijing date (`UTC+8`) in `YYYY-MM-DD` format.
- Keep only year, month, and day; do not output hours, minutes, or seconds.
- For Chinese `评论时间` or `评论日期`, convert only numeric timestamps or date-time text that includes a time component. Preserve plain date-only text as provided.
- Relative platform time values such as `1年前`, `9个月前`, `1 year ago`, and `9 months ago` are converted deterministically from the current Beijing date.
- Relative year values output only `YYYY`; relative month values output only `YYYY-MM`.
- Relative day and week values output `YYYY-MM-DD`.
- Do not infer missing month or day beyond the fixed relative-time granularity.

## Sensitive And Omitted Columns

The standardized workbook omits every column outside the standard schema. Confirmed sensitive, identity, and metadata headers include:

`IP地址`, `IP属地`, `用户名称`, `用户昵称`, `昵称`, `rpid`, `parent_rpid`, `username`, `ip_location`, `id`, `comment_id`, `commentId`, `cid`, `uid`, `user_id`, `userId`, `uniqueId`, `author`, `authorName`, `author_name`, `authorDisplayName`, `authorChannelId`, `authorChannelUrl`, `channelId`, `channel_id`, `channelUrl`, `profileUrl`, `profile_url`, `avatar`, `videoId`, `video_id`, `videoUrl`, `url`, and `permalink`.

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
- Stable account ID is selected first for the whole worksheet.
- Display-name fallback is allowed only when no registered account-ID column exists.
- Header selection is worksheet-wide and follows configuration order. It never falls back per row.
- Exact account-ID mappings:
  - YouTube: `author_channel_id`, then `authorChannelId`, then `Author Channel ID`.
  - 小红书: `用户ID`.
- Exact display-name fallback mappings:
  - YouTube: `author`.
  - 小红书: `用户名称`.
  - B站: `username`.
  - TikTok: `用户名`, then `昵称`; never `用户身份`.
  - 淘宝: `用户名称`, then `用户名`.
  - 京东: `用户名`.
- The same normalized display name in the same research project and platform produces the same hash regardless of which registered display-name header supplied it.
- Account-ID and display-name hashes use separate identity domains. Cross-project, cross-platform, and account-ID/display-name hashes differ.
- Display-name linkage is weak pseudonymization, not legal anonymization: nickname changes can split the same user, and different users with the same normalized name can merge.
- Raw account IDs, usernames, and nicknames remain omitted from standardized and cleaned outputs, logs, and summaries; approved identity values are read only in memory for hashing.
- `rpid`, `parent_rpid`, all comment IDs and parent IDs, URLs, profile links, IP fields, `用户身份`, source-provided `哈希ID`, and other ambiguous fields are never identity sources.
- Hashing and identity selection use deterministic tooling only; do not use AI.
- Hashing uses project-scoped, platform-isolated HMAC-SHA256 and emits 64 lowercase hexadecimal characters.
- The summary may contain project ID/name, platform, key version/fingerprint, identity type, source header, and counts. It must not contain a raw identity value or secret key.
