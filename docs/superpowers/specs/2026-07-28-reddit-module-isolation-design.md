# Reddit Reconstruction Module Isolation Design

## Goal

Move the Reddit JSON plus copied-page-text reconstruction capability into a
dedicated module that is parallel to, and has no runtime dependency on,
`skills/product-user-comment-data-merge-cleaning/`.  Keep it in the existing
repository and publish code only to the existing GitHub remote.

## Scope

The dedicated module accepts one Reddit JSON export and one copied Reddit page
text file.  It produces a paired XLSX and CSV whose rows are:

1. one post row containing the post title, author, content, page-derived time,
   page-derived score, and page-reported comment count;
2. every JSON comment in original JSON order, with JSON-derived author, time,
   content, depth, parent ID, and all-descendant reply count;
3. a page-derived comment score only when a normalized comment body is unique
   on both sides of the mapping.

The recommended runtime mode remains JSON-primary page metrics.  It must keep
all JSON comments, preserve unknown page metrics as blank cells, and never
infer values with AI or fuzzy matching.

## Non-goals

- Do not invoke the generic merge, header-standardization, pseudonymization,
  or cleaning workflow.
- Do not alter `skills/product-user-comment-data-merge-cleaning/` or its
  configuration.
- Do not upload raw Reddit JSON, copied page text, generated XLSX/CSV files,
  or local previews to GitHub.
- Do not add network scraping, browser automation, API credentials, or an AI
  model dependency.

## Module Boundary

Create a top-level `reddit_reconstruction/` package, parallel to `skills/`.
It owns all runtime code needed for reconstruction:

```text
reddit_reconstruction/
  __init__.py
  __main__.py
  cli.py
  json_export.py
  page_text.py
  merge.py
  output_safety.py
  requirements.txt
  README.md
  tests/
```

`output_safety.py` is copied into the module so the package does not import a
utility from the broader repository.  The module may import only its own
files, Python standard-library modules, and `openpyxl` within the declared
version range.  It must not import `tools.*`, `skills.*`, generic cleaner
configuration, or any web/AI library.

The public command is:

```text
python -m reddit_reconstruction \
  --json <reddit-export.json> \
  --page-text <copied-page.txt> \
  --output-xlsx <result.xlsx> \
  --output-csv <result.csv> \
  --json-primary-page-metrics
```

Existing implementation behavior is retained, including paired atomic output,
output-path protection, no-overwrite-by-default behavior, and the strict
parser route when the opt-in JSON-primary flag is absent.

## Data Contract

The output uses exactly these 11 columns, in this order:

```text
记录类型, 标题, 作者, 时间, 内容, 点赞数, 评论/回复数, 层级, 是否回复, 评论ID, 父ID
```

The first data row is the post row.  `评论/回复数` in that row is the
page-reported/API-reported total, even when it differs from the collected JSON
comment count.  Comment rows must never be dropped merely because page text
does not expose a score.  Unknown, unavailable, duplicate, or non-unique
page-score matches are blank, never zero.

## Tests and Documentation

Move or recreate only the relevant deterministic tests inside
`reddit_reconstruction/tests/`:

- JSON parsing and graph validation;
- copied-page parsing and score candidate handling;
- JSON-primary score matching, row construction, and all-descendant counts;
- paired XLSX/CSV writing and no-overwrite safety;
- CLI behavior for the JSON-primary route;
- blank `post.content` acceptance for photo/media posts while comment content
  remains nonblank.

`reddit_reconstruction/README.md` documents inputs, the no-AI deterministic
mapping rule, output columns, common gaps between reported and collected
comments, and exact run/test commands.  The package-local `.gitignore` or
root ignore rules must keep `outputs/`, raw JSON/TXT files, `__pycache__/`, and
local test scratch files out of version control.

## Publishing Boundary

Publish source, tests, README, dependency manifest, and non-sensitive design
documentation to the existing remote repository on the dedicated
`codex/reddit-data-reconstruction` branch.  Do not publish input or output
data.  A pull request can be opened only after GitHub CLI authentication is
available; a direct branch push still requires verified write access.

## Verification

Before publishing, run the isolated module test suite from its own directory
and verify it has no imports from the generic cleaning Skill.  Run the full
repository suite after relocation to confirm the generic workflow remains
unchanged.  Run a JSON-primary sample into a new ignored output directory and
verify:

- XLSX and CSV have identical cells;
- the post row is first;
- all JSON comments appear in original order;
- comment score classifications reconcile to the JSON comment count;
- descendant reply counts match an independently recomputed graph.
