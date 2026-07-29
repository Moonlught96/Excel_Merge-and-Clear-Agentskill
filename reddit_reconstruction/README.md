# Portable Reddit Reconstruction Module

This package deterministically reconstructs a post and its comments from a Reddit JSON export plus copied Reddit page text. It requires Python and the dependency in `requirements.txt`.

## Output contract

Both output files use these 11 columns, in this order:

1. `记录类型`
2. `标题`
3. `作者`
4. `时间`
5. `内容`
6. `点赞数`
7. `评论/回复数`
8. `层级`
9. `是否回复`
10. `评论ID`
11. `父ID`

JSON is the source of truth for post and comment identity, comment order, hierarchy, comment text, and reported comment total. In JSON-primary page-metrics mode, copied page text supplements the first post row with its displayed post time, post score, and reported comment count, while JSON continues to control identity and structure. Copied page text can supply a comment score only when a normalized comment body occurs exactly once in JSON and exactly once on the page. A missing, ambiguous, or unavailable score is written as blank, never as zero.

The reported-versus-collected count gap is retained as `reportedByApi - collectedCommentCount`; it represents comments reported by Reddit but not collected in the JSON export. The module uses deterministic parsing and mapping rules only: it does not use AI to infer, alter, match, or remove content.

## Run

```powershell
python -m reddit_reconstruction --json export.json --page-text page.txt --output-xlsx result.xlsx --output-csv result.csv --json-primary-page-metrics
```

## Test

```powershell
& '<bundled-python>' -m unittest discover -s reddit_reconstruction/tests -p 'test_*.py' -v
```
