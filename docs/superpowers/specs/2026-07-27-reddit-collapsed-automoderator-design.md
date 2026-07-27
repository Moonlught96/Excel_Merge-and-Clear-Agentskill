# Reddit collapsed AutoModerator handling

## Purpose

Allow the deterministic Reddit JSON + copied-page-text workflow to reconstruct
the human comments when the copied Reddit page shows a collapsed AutoModerator
system banner instead of an interactive AutoModerator comment block.

The output's `Post Comment Count` represents the number of comments actually
verified and exported. The original page's displayed count remains an internal
cross-check against the JSON post count.

## Scope and non-goals

This change applies only to the one exact collapsed system banner described
below. It does not relax author, order, content, score, or hierarchy matching.
It does not omit ordinary AutoModerator comments, infer missing comments, or
count promoted content as a comment.

## Exact eligibility rule

At the start of the copied comment area, ignoring blank clipboard-object lines,
the first four nonblank lines must be exactly:

1. `AutoModerator`
2. `这是自动化账户。`
3. `版主`
4. One existing accepted Reddit relative-time label

The JSON export must have a first comment that is all of the following:

- author exactly `AutoModerator` after existing author normalization;
- a top-level comment (`depth == 0` and `parent_id == post.id`);
- has no child comment in the JSON export.

When all of those checks pass, the parser records only that first JSON comment
ID as excluded and removes only the four-line banner from page-text matching.
All remaining page comment blocks must still match the remaining JSON comments
exactly by order, author, and normalized content.

Any nonmatching or incomplete banner, a nonmatching JSON first comment, or an
AutoModerator comment with a child must fail safely. A normal AutoModerator
comment with a body and interactive controls is not a collapsed banner and is
handled by the pre-existing strict matching flow.

## Data flow

1. Parse the JSON export unchanged, retaining the source post count.
2. Parse the copied page header and require its displayed count to equal the
   JSON post count. This remains the source-integrity check.
3. Detect the exact collapsed banner at the start of the comment area. If it
   qualifies, record the matching first JSON comment ID as excluded.
4. Pair the remaining page metrics with the remaining JSON comments using the
   existing strict checks.
5. Build rows only for the retained JSON comments. Set every row's
   `Post Comment Count` to `len(retained_comments)`.

For the current live sample, the source page and JSON both report 11 comments,
one collapsed AutoModerator item is excluded, and the output contains 10 rows
with `Post Comment Count` equal to 10.

## Component changes

- `tools/reddit_page_text.py`: add an immutable, default-empty tuple of
  excluded comment IDs to `RedditPageText`; add the narrow banner detector;
  match page blocks against JSON comments after that one validated exclusion.
- `tools/reddit_json_text_merge.py`: validate the exclusion list again before
  using it, remove only the validated comment, and use the retained row count
  for `Post Comment Count`.
- `tools/reconstruct_reddit_comments.py`: retain its existing safe CLI output;
  it will naturally report the original JSON count and the reduced verified
  page-match count without adding source text to stdout.

## Failure behavior

The tool must stop without creating either output if any of these occur:

- page displayed count and JSON post count differ;
- the leading pattern resembles but does not exactly match the collapsed banner;
- the matching JSON comment is absent, not first, not top-level, or has a child;
- the exclusion list is duplicated, unknown, or otherwise invalid;
- any remaining page block does not match JSON author/content/order exactly.

## Verification

Automated tests will cover:

- exact collapsed-banner exclusion and correct retained ordering;
- output `Post Comment Count` equal to the actual retained-row count;
- normal interactive AutoModerator comments remaining included;
- near-miss banners, invalid first JSON comments, and child-comment cases
  failing safely;
- invalid exclusion identifiers failing safely;
- the existing clipboard-object and `共享` action-label handling remaining
  compatible;
- a real JSON + copied-page-text CLI run producing a new XLSX and CSV, with
  the workbook inspected after generation.
