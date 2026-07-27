# Reddit Collapsed AutoModerator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Deterministically exclude one validated collapsed AutoModerator system banner and report the actual exported comment count in reconstructed Reddit rows.

**Architecture:** The page-text parser owns narrow banner recognition and returns an immutable exclusion ID with strictly matched metrics. The JSON/text merger independently validates that exclusion, emits only retained JSON comments, and writes the retained-row count to Post Comment Count; the source page count remains a JSON integrity check.

**Tech Stack:** Python 3, dataclasses, unittest, openpyxl, existing deterministic Reddit JSON/page-text modules.

## Global Constraints

- Use only deterministic rules; do not use AI, fuzzy matching, or network access.
- Preserve the JSON export and copied page-text inputs unchanged.
- Only the exact collapsed Chinese AutoModerator banner at the start of the comment area may be excluded.
- Keep strict author, normalized-content, source-order, and page-count versus JSON-count checks for every retained comment.
- Never expose copied-page or JSON content in CLI errors or summary output.
- Post Comment Count in every output row must equal the number of actual retained/exported comments.
- Do not change the formal CLI option surface or its existing safe stdout contract.

---

## File structure

- tools/reddit_page_text.py — parse copied page text, detect the narrow collapsed banner, and return matched metrics plus an exclusion ID.
- tools/reddit_json_text_merge.py — validate the parser-provided exclusion again and assemble rows with the retained-comment count.
- tests/test_reddit_page_text.py — exact banner recognition, near-miss rejection, ordinary AutoModerator preservation, and child safety.
- tests/test_reddit_json_text_merge.py — row construction, actual-count semantics, and defensive exclusion validation.
- tests/test_reconstruct_reddit_comments.py — formal CLI/output regression for source count versus actual verified-row count.

### Task 1: Parse and validate the collapsed AutoModerator banner

**Files:**

- Modify: tools/reddit_page_text.py, RedditPageText data model, comment metrics, and parse_reddit_page_text.
- Test: tests/test_reddit_page_text.py.

**Interfaces:**

- Consumes: RedditJsonExport, normalized copied page lines, existing _COMMENT_TIME_PATTERN, normalize_author, and RedditJsonComment fields.
- Produces: RedditPageText(..., comments: tuple[PageCommentMetric, ...], excluded_comment_ids: tuple[str, ...] = ()).
- Produces: _split_collapsed_automoderator_banner(comment_lines: list[str], export: RedditJsonExport) -> tuple[list[str], tuple[str, ...]].

- [ ] **Step 1: Write the failing exact-banner tests**

Add a compact fixture with a first top-level JSON comment named AutoModerator, followed by two normal JSON comments. Put the following banner before the two interactive page blocks:

    AutoModerator
    这是自动化账户。
    版主
    4天前

Assert that only the first JSON ID is excluded and the two retained metrics remain in source order:

    result = parse_reddit_page_text(self.write_text(page), export)
    self.assertEqual(("comment1",), result.excluded_comment_ids)
    self.assertEqual([2, None], [metric.score for metric in result.comments])

Add separate negative cases for an account-label mismatch, a first JSON author that is not AutoModerator, and a child whose parent_id is the AutoModerator ID. Each must raise a category-only RedditPageTextError. Preserve the existing interactive FIRST_COMMENT fixture and assert that it yields an empty excluded_comment_ids tuple.

- [ ] **Step 2: Run the focused tests to verify red**

Run:

    python -m unittest tests.test_reddit_page_text.RedditPageTextTest.test_excludes_exact_collapsed_automoderator_banner_at_comment_area_start tests.test_reddit_page_text.RedditPageTextTest.test_rejects_invalid_collapsed_automoderator_banner -v

Expected: FAIL because RedditPageText has no exclusion field and the parser still requires an interactive page block for every JSON comment.

- [ ] **Step 3: Implement the narrow splitter and retained matching**

Append a default-empty immutable field without breaking existing four-argument RedditPageText construction:

    @dataclass(frozen=True)
    class RedditPageText:
        post_time: str
        post_score: int
        post_comment_count: int
        comments: tuple[PageCommentMetric, ...]
        excluded_comment_ids: tuple[str, ...] = ()

Add constants for the exact Chinese account and moderator labels. The splitter must only activate when the first nonblank page comment line is AutoModerator and the second nonblank line is exactly the account label. If that condition is absent, return the original lines with no exclusion; this preserves normal interactive AutoModerator comments.

If activation begins, require the third nonblank line to be the exact moderator label and the fourth to match _COMMENT_TIME_PATTERN. Otherwise raise RedditPageTextError("collapsed AutoModerator banner is invalid"). Validate the first JSON comment with all of these conditions:

    normalize_author(first.username) == "AutoModerator"
    first.depth == 0
    first.parent_id == export.post.id
    not any(item.parent_id == first.id for item in export.comments)

On validation failure, raise RedditPageTextError("collapsed AutoModerator banner does not match JSON"). On success, remove only the source lines through the accepted time line and return the first JSON ID as the one-element exclusion tuple.

Change _comment_metrics to accept the retained comment sequence. In parse_reddit_page_text, call the splitter before metric extraction; pass export.comments[1:] only when the helper returns the one permitted exclusion; store excluded_comment_ids on the result. Preserve current exact block-count, author, normalized-content, and score behavior.

- [ ] **Step 4: Run all parser tests to verify green**

Run:

    python -m unittest tests.test_reddit_page_text -v

Expected: PASS, including promoted-block, clipboard object replacement, 分享/共享, and ordinary interactive AutoModerator coverage.

- [ ] **Step 5: Commit Task 1**

    git add tools/reddit_page_text.py tests/test_reddit_page_text.py
    git commit -m "feat: handle collapsed AutoModerator banners"

### Task 2: Build rows from retained comments and use the actual count

**Files:**

- Modify: tools/reddit_json_text_merge.py.
- Test: tests/test_reddit_json_text_merge.py.

**Interfaces:**

- Consumes: RedditJsonExport, RedditPageText.excluded_comment_ids, and matched page metrics.
- Produces: _retained_comments(export: RedditJsonExport, page: RedditPageText) -> tuple[RedditJsonComment, ...].
- Produces: reconstruct_json_text_rows(...) rows where Post Comment Count equals len(retained_comments).

- [ ] **Step 1: Write the failing merger tests**

Extend the fixture with a first AutoModerator root, then a root and reply. Construct a page object with one exclusion and two metrics:

    page = RedditPageText(
        "8 hours ago", 99, 3,
        (PageCommentMetric(4), PageCommentMetric(None)),
        ("automod",),
    )
    rows = reconstruct_json_text_rows(export, page)
    self.assertEqual(["root", "reply"], [row["Comment ID"] for row in rows])
    self.assertEqual([2, 2], [row["Post Comment Count"] for row in rows])

Add tests for unknown, duplicated, nonfirst, and child-owning exclusions. Each must raise ValueError containing "collapsed AutoModerator exclusion". Update the ordinary fixture assertion so its two output rows have Post Comment Count 2 even though its page/JSON reported count remains 3.

- [ ] **Step 2: Run merger tests to verify red**

Run:

    python -m unittest tests.test_reddit_json_text_merge -v

Expected: FAIL because the merger currently requires metrics for all JSON comments and writes the page count to each row.

- [ ] **Step 3: Implement independent retention validation**

Add this private helper, importing normalize_author from tools.reddit_page_text:

    def _retained_comments(
        export: RedditJsonExport, page: RedditPageText
    ) -> tuple[RedditJsonComment, ...]:
        excluded_ids = page.excluded_comment_ids
        if not excluded_ids:
            return export.comments
        if len(excluded_ids) != 1 or len(set(excluded_ids)) != 1:
            raise ValueError("invalid collapsed AutoModerator exclusion")
        first = export.comments[0] if export.comments else None
        if (
            first is None
            or excluded_ids != (first.id,)
            or normalize_author(first.username) != "AutoModerator"
            or first.depth != 0
            or first.parent_id != export.post.id
            or any(item.parent_id == first.id for item in export.comments)
        ):
            raise ValueError("invalid collapsed AutoModerator exclusion")
        return export.comments[1:]

Keep this existing source-integrity check unchanged:

    if page.post_comment_count != export.post.num_comments:
        raise ValueError("page and JSON post comment counts differ")

Then compare len(page.comments) only with len(retained_comments), zip the retained comments with metrics, and set:

    "Post Comment Count": len(retained_comments)

- [ ] **Step 4: Run merger and output tests to verify green**

Run:

    python -m unittest tests.test_reddit_json_text_merge tests.test_reconstruct_reddit_comments.RedditOutputTests -v

Expected: PASS; output-writer behavior remains unchanged except for the intentional reconstructed-row count value.

- [ ] **Step 5: Commit Task 2**

    git add tools/reddit_json_text_merge.py tests/test_reddit_json_text_merge.py
    git commit -m "feat: count retained Reddit comments"

### Task 3: Exercise the formal CLI and supplied live input

**Files:**

- Modify: tests/test_reconstruct_reddit_comments.py, RedditJsonPageTextCliTests.
- Verify only: C:\Users\Eddie.J.Lu\Downloads\Reddit-desksetup-1v3t6z2 (1).json.
- Verify only: .tmp-tests\reddit-live-1v3t6z2\reddit-page.txt.
- Create at test time: .tmp-tests\reddit-live-1v3t6z2\reddit-reconstructed.xlsx and .tmp-tests\reddit-live-1v3t6z2\reddit-reconstructed.csv.

**Interfaces:**

- Consumes: unchanged formal CLI options and the parser/merger interfaces from Tasks 1–2.
- Produces: a 10-row XLSX/CSV for the supplied sample, with Post Comment Count 10 in every data row.

- [ ] **Step 1: Write a failing formal CLI regression**

Add fixture writers for a three-comment JSON input whose first comment is an eligible AutoModerator root and a copied page whose comment section begins with the exact collapsed banner followed by two interactive comments. Run self.run_cli(), then assert:

    self.assertEqual(0, completed.returncode, completed.stderr)
    self.assertIn("JSON comment count: 3", completed.stdout)
    self.assertIn("Page comment match count: 2", completed.stdout)
    sheet = load_workbook(self.output_xlsx, data_only=False).active
    self.assertEqual(3, sheet.max_row)
    self.assertEqual(2, sheet.cell(2, 6).value)
    self.assertEqual(2, sheet.cell(3, 6).value)

Assert the sheet contains the two retained IDs and no source secret appears in stdout/stderr.

- [ ] **Step 2: Run the focused CLI test to verify red**

Run:

    python -m unittest tests.test_reconstruct_reddit_comments.RedditJsonPageTextCliTests.test_collapsed_automoderator_cli_outputs_only_verified_comments -v

Expected: FAIL before Tasks 1–2 are integrated because the old parser requires three interactive page blocks.

- [ ] **Step 3: Run the whole automated suite**

Run:

    python -m unittest discover -s tests -p "test_*.py"

Expected: PASS with no test failures.

- [ ] **Step 4: Run the supplied real input with new output paths**

Run from the worktree:

    $py = 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    & $py 'tools\reconstruct_reddit_comments.py' --json 'C:\Users\Eddie.J.Lu\Downloads\Reddit-desksetup-1v3t6z2 (1).json' --page-text '.tmp-tests\reddit-live-1v3t6z2\reddit-page.txt' --output-xlsx '.tmp-tests\reddit-live-1v3t6z2\reddit-reconstructed.xlsx' --output-csv '.tmp-tests\reddit-live-1v3t6z2\reddit-reconstructed.csv'

Expected: success, original JSON count 11, page match count 10, and a new output pair without changing either input.

- [ ] **Step 5: Verify the generated spreadsheet without rewriting it**

Inspect the generated XLSX and CSV without exposing comment text. Verify exactly 14 headers, 10 data rows, identical comment-ID order across both formats, and Post Comment Count 10 in every row. Use the workspace spreadsheet runtime for inspection only; do not alter the formal CLI output.

- [ ] **Step 6: Commit Task 3**

    git add tests/test_reconstruct_reddit_comments.py
    git commit -m "test: cover collapsed AutoModerator CLI flow"

Do not add the user JSON, copied page text, generated XLSX, generated CSV, or .tmp-tests artifacts to Git.

## Plan self-review

- Spec coverage: Task 1 implements exact-banner recognition and safety checks; Task 2 implements independent exclusion validation and actual-count rows; Task 3 verifies the formal CLI, full suite, and supplied real sample.
- Placeholder scan: no unfinished markers, deferred work, or unspecified tests remain.
- Type consistency: Task 1 adds excluded_comment_ids; Task 2 consumes it through _retained_comments; Task 3 uses only the existing formal CLI and output schema.
