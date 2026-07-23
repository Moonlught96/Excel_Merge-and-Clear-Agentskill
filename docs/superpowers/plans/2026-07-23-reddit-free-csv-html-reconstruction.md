# Reddit Free CSV + HTML Reconstruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic Python tool that enriches a free Reddit CSV with post statistics, comment scores, levels, and parent IDs from a saved Reddit HTML file, then writes matching XLSX and CSV outputs.

**Architecture:** Separate parsers normalize the free CSV and saved HTML into typed records. A strict ID-based merger refuses missing hierarchy data, then an output layer writes the approved 15-column contract through safe, atomic paths. The CLI only coordinates those units and never uses AI, fuzzy matching, or external services.

**Tech Stack:** Python 3.11+, standard library (`csv`, `html.parser`, `argparse`, `dataclasses`), existing `openpyxl`, existing `tools.csv_excel_compat`, existing `tools.output_path_safety`, `unittest`.

---

## File map

```text
tools/
├── reddit_free_csv.py                 Parse the custom metadata + comment CSV
├── reddit_saved_html.py               Parse fixed Reddit post/comment attributes
└── reconstruct_reddit_comments.py     Merge, validate, write outputs, expose CLI

tests/
├── test_reddit_free_csv.py
├── test_reddit_saved_html.py
└── test_reconstruct_reddit_comments.py
```

Do not modify the existing merge, header-standardization, pseudonymization, or cleaning configuration. This tool produces a structured raw table.

### Task 1: Parse the free Reddit CSV deterministically

**Files:**
- Create: `tools/reddit_free_csv.py`
- Create: `tests/test_reddit_free_csv.py`

- [ ] **Step 1: Write the failing happy-path test**

```python
# tests/test_reddit_free_csv.py
from __future__ import annotations

import csv
import shutil
import unittest
from pathlib import Path

from tools.reddit_free_csv import parse_free_reddit_csv


class FreeRedditCsvTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path.cwd() / ".tmp-tests" / "reddit-free-csv"
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_rows(self, rows: list[list[str]], encoding: str = "utf-8-sig") -> Path:
        path = self.tmp / "free.csv"
        with path.open("w", encoding=encoding, newline="") as stream:
            csv.writer(stream).writerows(rows)
        return path

    def test_parses_metadata_and_comments_in_source_order(self) -> None:
        path = self.write_rows([
            ["title", "Post title"],
            ["body", "Line one\nLine two"],
            ["url", "https://www.reddit.com/r/x/comments/post1/title/"],
            [],
            ["author_name", "date_time", "comment", "upvote_number", "comment_url"],
            ["alpha", "2026-07-01T00:00:00.000Z", "First", "", "https://www.reddit.com/r/x/comments/post1/comment/c1/"],
            ["beta", "2026-07-01T00:01:00.000Z", "Second", "", "https://www.reddit.com/r/x/comments/post1/comment/c2/"],
        ])

        result = parse_free_reddit_csv(path)

        self.assertEqual("Post title", result.title)
        self.assertEqual("Line one\nLine two", result.body)
        self.assertEqual("post1", result.post_id)
        self.assertEqual(["c1", "c2"], [item.comment_id for item in result.comments])
        self.assertEqual(["First", "Second"], [item.comment for item in result.comments])
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_free_csv -v
```

Expected: FAIL because `tools.reddit_free_csv` does not exist.

- [ ] **Step 3: Implement the minimal typed parser**

```python
# tools/reddit_free_csv.py
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

try:
    from tools.csv_excel_compat import read_csv_rows
except ImportError:
    from csv_excel_compat import read_csv_rows


COMMENT_ID_RE = re.compile(r"/comment/([a-z0-9]+)/?(?:[?#].*)?$", re.IGNORECASE)
POST_ID_RE = re.compile(r"/comments/([a-z0-9]+)/", re.IGNORECASE)
METADATA_KEYS = ("title", "body", "url")
COMMENT_HEADERS = ("author_name", "date_time", "comment", "comment_url")


@dataclass(frozen=True)
class FreeComment:
    author: str
    time: str
    comment: str
    comment_url: str
    comment_id: str


@dataclass(frozen=True)
class FreeRedditExport:
    title: str
    body: str
    url: str
    post_id: str
    comments: tuple[FreeComment, ...]


def _single_metadata(metadata: dict[str, list[str]], key: str) -> str:
    values = metadata.get(key, [])
    if len(values) != 1:
        raise ValueError(f"Free CSV must contain exactly one {key!r} row")
    return values[0]


def _comment_id(url: str) -> str:
    match = COMMENT_ID_RE.search(url.strip())
    if not match:
        raise ValueError(f"Invalid Reddit comment URL: {url}")
    return match.group(1).lower()


def parse_free_reddit_csv(path: Path) -> FreeRedditExport:
    rows = read_csv_rows(path).rows
    header_index = next(
        (
            index
            for index, row in enumerate(rows)
            if set(COMMENT_HEADERS).issubset(set(row))
        ),
        None,
    )
    if header_index is None:
        raise ValueError(
            "Free CSV comment header must include: "
            + ", ".join(COMMENT_HEADERS)
        )

    metadata: dict[str, list[str]] = {}
    for row in rows[:header_index]:
        if not row or not any(cell.strip() for cell in row):
            continue
        key = row[0].strip()
        if key in METADATA_KEYS:
            metadata.setdefault(key, []).append(row[1] if len(row) > 1 else "")

    title = _single_metadata(metadata, "title")
    body = _single_metadata(metadata, "body")
    url = _single_metadata(metadata, "url")
    post_match = POST_ID_RE.search(url)
    if not post_match:
        raise ValueError(f"Invalid Reddit post URL: {url}")

    header = rows[header_index]
    indexes = {name: header.index(name) for name in COMMENT_HEADERS}
    comments: list[FreeComment] = []
    seen: set[str] = set()
    for row in rows[header_index + 1 :]:
        if not row or not any(cell for cell in row):
            continue
        values = {
            name: row[index] if index < len(row) else ""
            for name, index in indexes.items()
        }
        comment_id = _comment_id(values["comment_url"])
        if comment_id in seen:
            raise ValueError(f"Duplicate Reddit comment ID: {comment_id}")
        seen.add(comment_id)
        comments.append(
            FreeComment(
                author=values["author_name"],
                time=values["date_time"],
                comment=values["comment"],
                comment_url=values["comment_url"],
                comment_id=comment_id,
            )
        )

    return FreeRedditExport(
        title=title,
        body=body,
        url=url,
        post_id=post_match.group(1).lower(),
        comments=tuple(comments),
    )
```

- [ ] **Step 4: Add strict metadata, header, URL, duplicate, and encoding tests**

Append to `tests/test_reddit_free_csv.py`:

```python
    def test_rejects_missing_or_duplicate_metadata(self) -> None:
        missing = self.write_rows([
            ["title", "Title"],
            ["url", "https://www.reddit.com/r/x/comments/p1/title/"],
            ["author_name", "date_time", "comment", "comment_url"],
        ])
        with self.assertRaisesRegex(ValueError, "body"):
            parse_free_reddit_csv(missing)

        duplicate = self.write_rows([
            ["title", "Title"],
            ["title", "Other"],
            ["body", "Body"],
            ["url", "https://www.reddit.com/r/x/comments/p1/title/"],
            ["author_name", "date_time", "comment", "comment_url"],
        ])
        with self.assertRaisesRegex(ValueError, "title"):
            parse_free_reddit_csv(duplicate)

    def test_rejects_missing_header_and_invalid_or_duplicate_comment_ids(self) -> None:
        missing_header = self.write_rows([
            ["title", "Title"],
            ["body", "Body"],
            ["url", "https://www.reddit.com/r/x/comments/p1/title/"],
        ])
        with self.assertRaisesRegex(ValueError, "comment header"):
            parse_free_reddit_csv(missing_header)

        invalid = self.write_rows([
            ["title", "Title"],
            ["body", "Body"],
            ["url", "https://www.reddit.com/r/x/comments/p1/title/"],
            ["author_name", "date_time", "comment", "comment_url"],
            ["a", "t", "c", "https://example.com/no-id"],
        ])
        with self.assertRaisesRegex(ValueError, "Invalid Reddit comment URL"):
            parse_free_reddit_csv(invalid)

        duplicate = self.write_rows([
            ["title", "Title"],
            ["body", "Body"],
            ["url", "https://www.reddit.com/r/x/comments/p1/title/"],
            ["author_name", "date_time", "comment", "comment_url"],
            ["a", "t1", "one", "https://www.reddit.com/r/x/comments/p1/comment/c1/"],
            ["b", "t2", "two", "https://www.reddit.com/r/x/comments/p1/comment/c1/"],
        ])
        with self.assertRaisesRegex(ValueError, "Duplicate Reddit comment ID"):
            parse_free_reddit_csv(duplicate)

    def test_uses_registered_utf16_and_gb18030_decoding(self) -> None:
        rows = [
            ["title", "标题"],
            ["body", "正文"],
            ["url", "https://www.reddit.com/r/x/comments/p1/title/"],
            ["author_name", "date_time", "comment", "comment_url"],
            ["作者", "时间", "评论", "https://www.reddit.com/r/x/comments/p1/comment/c1/"],
        ]
        for encoding in ("utf-16", "gb18030"):
            with self.subTest(encoding=encoding):
                path = self.write_rows(rows, encoding=encoding)
                result = parse_free_reddit_csv(path)
                self.assertEqual("标题", result.title)
                self.assertEqual("评论", result.comments[0].comment)
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_free_csv -v
```

Expected: all free CSV parser tests pass.

- [ ] **Step 6: Commit Task 1**

```powershell
git add tools/reddit_free_csv.py tests/test_reddit_free_csv.py
git commit -m "feat: parse free Reddit CSV exports"
```

### Task 2: Parse fixed Reddit HTML attributes

**Files:**
- Create: `tools/reddit_saved_html.py`
- Create: `tests/test_reddit_saved_html.py`

- [ ] **Step 1: Write failing HTML parser tests**

```python
# tests/test_reddit_saved_html.py
from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from tools.reddit_saved_html import parse_saved_reddit_html


class SavedRedditHtmlTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path.cwd() / ".tmp-tests" / "reddit-html"
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_html(self, text: str) -> Path:
        path = self.tmp / "post.html"
        path.write_text(text, encoding="utf-8")
        return path

    def test_parses_post_and_comment_attributes(self) -> None:
        path = self.write_html("""
        <html><body>
          <shreddit-post thingid="t3_post1" author="poster"
            score="267" comment-count="65"></shreddit-post>
          <shreddit-comment thingid="t1_c1" parentid="t3_post1"
            depth="0" score="4"></shreddit-comment>
          <shreddit-comment thingid="t1_c2" parentid="t1_c1"
            depth="1"></shreddit-comment>
        </body></html>
        """)

        result = parse_saved_reddit_html(path)

        self.assertEqual("post1", result.post_id)
        self.assertEqual("poster", result.post_author)
        self.assertEqual("267", result.post_score)
        self.assertEqual("65", result.post_comment_count)
        self.assertEqual("post1", result.comments["c1"].parent_id)
        self.assertEqual(0, result.comments["c1"].thread_level)
        self.assertEqual("4", result.comments["c1"].score)
        self.assertEqual("", result.comments["c2"].score)
```

- [ ] **Step 2: Run the test and verify failure**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_saved_html -v
```

Expected: FAIL because `tools.reddit_saved_html` does not exist.

- [ ] **Step 3: Implement the fixed-attribute HTML parser**

```python
# tools/reddit_saved_html.py
from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


REGISTERED_SCORE_ATTRIBUTES = ("score", "data-score")
REGISTERED_COMMENT_COUNT_ATTRIBUTES = ("comment-count", "commentcount")


def _attrs(values: list[tuple[str, str | None]]) -> dict[str, str]:
    return {key.lower(): value or "" for key, value in values}


def _strip_fullname(value: str) -> str:
    for prefix in ("t1_", "t3_"):
        if value.lower().startswith(prefix):
            return value[len(prefix) :].lower()
    return value.lower()


def _first(attributes: dict[str, str], names: tuple[str, ...]) -> str:
    for name in names:
        if attributes.get(name, "") != "":
            return attributes[name]
    return ""


@dataclass(frozen=True)
class HtmlComment:
    comment_id: str
    parent_id: str
    thread_level: int | None
    score: str


@dataclass(frozen=True)
class SavedRedditHtml:
    post_id: str
    post_author: str
    post_score: str
    post_comment_count: str
    comments: dict[str, HtmlComment]


class _RedditHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.post_id = ""
        self.post_author = ""
        self.post_score = ""
        self.post_comment_count = ""
        self.comments: dict[str, HtmlComment] = {}

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attributes = _attrs(attrs)
        if tag.lower() == "shreddit-post":
            post_id = _strip_fullname(attributes.get("thingid", ""))
            if self.post_id and post_id and self.post_id != post_id:
                raise ValueError("Saved HTML contains multiple Reddit post IDs")
            self.post_id = post_id or self.post_id
            self.post_author = attributes.get("author", self.post_author)
            self.post_score = _first(
                attributes,
                REGISTERED_SCORE_ATTRIBUTES,
            ) or self.post_score
            self.post_comment_count = _first(
                attributes,
                REGISTERED_COMMENT_COUNT_ATTRIBUTES,
            ) or self.post_comment_count
            return

        if tag.lower() != "shreddit-comment":
            return
        comment_id = _strip_fullname(attributes.get("thingid", ""))
        if not comment_id:
            return
        if comment_id in self.comments:
            raise ValueError(f"Duplicate HTML comment ID: {comment_id}")
        parent_id = _strip_fullname(attributes.get("parentid", ""))
        depth_text = attributes.get("depth", "")
        depth = int(depth_text) if depth_text.isdigit() else None
        self.comments[comment_id] = HtmlComment(
            comment_id=comment_id,
            parent_id=parent_id,
            thread_level=depth,
            score=_first(attributes, REGISTERED_SCORE_ATTRIBUTES),
        )


def parse_saved_reddit_html(path: Path) -> SavedRedditHtml:
    parser = _RedditHtmlParser()
    parser.feed(path.read_text(encoding="utf-8-sig"))
    parser.close()
    if not parser.post_id:
        raise ValueError("Saved HTML does not contain a registered Reddit post node")
    return SavedRedditHtml(
        post_id=parser.post_id,
        post_author=parser.post_author,
        post_score=parser.post_score,
        post_comment_count=parser.post_comment_count,
        comments=parser.comments,
    )
```

- [ ] **Step 4: Add duplicate, multi-post, and unregistered-structure tests**

Append to `tests/test_reddit_saved_html.py`:

```python
    def test_rejects_duplicate_comment_and_multiple_post_ids(self) -> None:
        duplicate = self.write_html("""
        <shreddit-post thingid="t3_p1"></shreddit-post>
        <shreddit-comment thingid="t1_c1" parentid="t3_p1" depth="0"></shreddit-comment>
        <shreddit-comment thingid="t1_c1" parentid="t3_p1" depth="0"></shreddit-comment>
        """)
        with self.assertRaisesRegex(ValueError, "Duplicate HTML comment ID"):
            parse_saved_reddit_html(duplicate)

        multiple = self.write_html("""
        <shreddit-post thingid="t3_p1"></shreddit-post>
        <shreddit-post thingid="t3_p2"></shreddit-post>
        """)
        with self.assertRaisesRegex(ValueError, "multiple Reddit post IDs"):
            parse_saved_reddit_html(multiple)

    def test_rejects_html_without_registered_post_node(self) -> None:
        path = self.write_html("<html><body><article>Post</article></body></html>")
        with self.assertRaisesRegex(ValueError, "registered Reddit post node"):
            parse_saved_reddit_html(path)
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_saved_html -v
```

Expected: all saved HTML parser tests pass.

- [ ] **Step 6: Commit Task 2**

```powershell
git add tools/reddit_saved_html.py tests/test_reddit_saved_html.py
git commit -m "feat: parse saved Reddit HTML"
```

### Task 3: Merge strictly by Comment ID

**Files:**
- Create: `tools/reconstruct_reddit_comments.py`
- Create: `tests/test_reconstruct_reddit_comments.py`

- [ ] **Step 1: Write failing strict-merge tests**

```python
# tests/test_reconstruct_reddit_comments.py
from __future__ import annotations

import unittest

from tools.reconstruct_reddit_comments import (
    OUTPUT_HEADERS,
    reconstruct_rows,
)
from tools.reddit_free_csv import FreeComment, FreeRedditExport
from tools.reddit_saved_html import HtmlComment, SavedRedditHtml


class ReconstructRedditRowsTests(unittest.TestCase):
    def free_export(self) -> FreeRedditExport:
        return FreeRedditExport(
            title="Title",
            body="Body",
            url="https://www.reddit.com/r/x/comments/p1/title/",
            post_id="p1",
            comments=(
                FreeComment(
                    author="alpha",
                    time="2026-07-01T00:00:00.000Z",
                    comment="Root",
                    comment_url="https://www.reddit.com/r/x/comments/p1/comment/c1/",
                    comment_id="c1",
                ),
                FreeComment(
                    author="beta",
                    time="2026-07-01T00:01:00.000Z",
                    comment="Reply",
                    comment_url="https://www.reddit.com/r/x/comments/p1/comment/c2/",
                    comment_id="c2",
                ),
            ),
        )

    def html_export(self) -> SavedRedditHtml:
        return SavedRedditHtml(
            post_id="p1",
            post_author="poster",
            post_score="99",
            post_comment_count="2",
            comments={
                "c1": HtmlComment("c1", "p1", 0, "4"),
                "c2": HtmlComment("c2", "c1", 1, ""),
            },
        )

    def test_merges_in_free_csv_order_and_derives_reply_status(self) -> None:
        rows = reconstruct_rows(self.free_export(), self.html_export())

        self.assertEqual(15, len(OUTPUT_HEADERS))
        self.assertEqual(["c1", "c2"], [row["Comment ID"] for row in rows])
        self.assertEqual(["No", "Yes"], [row["Is Reply"] for row in rows])
        self.assertEqual(["4", ""], [row["Score"] for row in rows])
        self.assertTrue(all(row["Post Score"] == "99" for row in rows))
```

- [ ] **Step 2: Run the focused test and verify failure**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reconstruct_reddit_comments.ReconstructRedditRowsTests -v
```

Expected: FAIL because `tools.reconstruct_reddit_comments` does not exist.

- [ ] **Step 3: Implement the data contract and strict merge**

```python
# tools/reconstruct_reddit_comments.py
from __future__ import annotations

from pathlib import Path

try:
    from tools.reddit_free_csv import FreeRedditExport
    from tools.reddit_saved_html import SavedRedditHtml
except ImportError:
    from reddit_free_csv import FreeRedditExport
    from reddit_saved_html import SavedRedditHtml


OUTPUT_HEADERS = (
    "Title",
    "Post Body",
    "Post URL",
    "Post Author",
    "Post Score",
    "Post Comment Count",
    "Author",
    "Time",
    "Score",
    "Thread Level",
    "Is Reply",
    "Comment",
    "Comment URL",
    "Comment ID",
    "Parent ID",
)


def _required_post_value(
    html_value: str,
    override: str | None,
    label: str,
) -> str:
    value = html_value if html_value != "" else (override or "")
    if value == "":
        raise ValueError(
            f"Saved HTML is missing {label}; provide the corresponding explicit CLI value"
        )
    return value


def reconstruct_rows(
    free: FreeRedditExport,
    html: SavedRedditHtml,
    *,
    post_author: str | None = None,
    post_score: str | None = None,
    post_comment_count: str | None = None,
) -> list[dict[str, str | int]]:
    if free.post_id != html.post_id:
        raise ValueError(
            f"Post ID mismatch: free CSV={free.post_id}, HTML={html.post_id}"
        )

    author = _required_post_value(
        html.post_author,
        post_author,
        "post author",
    )
    score = _required_post_value(
        html.post_score,
        post_score,
        "post score",
    )
    comment_count = _required_post_value(
        html.post_comment_count,
        post_comment_count,
        "post comment count",
    )

    missing_html: list[str] = []
    missing_hierarchy: list[str] = []
    rows: list[dict[str, str | int]] = []
    for comment in free.comments:
        html_comment = html.comments.get(comment.comment_id)
        if html_comment is None:
            missing_html.append(comment.comment_id)
            continue
        if (
            html_comment.parent_id == ""
            or html_comment.thread_level is None
        ):
            missing_hierarchy.append(comment.comment_id)
            continue
        rows.append({
            "Title": free.title,
            "Post Body": free.body,
            "Post URL": free.url,
            "Post Author": author,
            "Post Score": score,
            "Post Comment Count": comment_count,
            "Author": comment.author,
            "Time": comment.time,
            "Score": html_comment.score,
            "Thread Level": html_comment.thread_level,
            "Is Reply": "No" if html_comment.thread_level == 0 else "Yes",
            "Comment": comment.comment,
            "Comment URL": comment.comment_url,
            "Comment ID": comment.comment_id,
            "Parent ID": html_comment.parent_id,
        })

    errors: list[str] = []
    if missing_html:
        errors.append("comments missing from HTML: " + ", ".join(missing_html))
    if missing_hierarchy:
        errors.append(
            "comments missing parent ID or depth: "
            + ", ".join(missing_hierarchy)
        )
    if errors:
        raise ValueError("; ".join(errors))
    return rows
```

- [ ] **Step 4: Add post mismatch, fallback, and missing hierarchy tests**

Append to `tests/test_reconstruct_reddit_comments.py`:

```python
    def test_rejects_post_mismatch_missing_comment_and_missing_hierarchy(self) -> None:
        wrong_post = SavedRedditHtml(
            post_id="other",
            post_author="p",
            post_score="1",
            post_comment_count="1",
            comments={},
        )
        with self.assertRaisesRegex(ValueError, "Post ID mismatch"):
            reconstruct_rows(self.free_export(), wrong_post)

        missing = self.html_export()
        missing.comments.pop("c2")
        with self.assertRaisesRegex(ValueError, "c2"):
            reconstruct_rows(self.free_export(), missing)

        broken = self.html_export()
        broken.comments["c2"] = HtmlComment("c2", "", None, "2")
        with self.assertRaisesRegex(ValueError, "parent ID or depth"):
            reconstruct_rows(self.free_export(), broken)

    def test_uses_explicit_post_values_only_when_html_is_missing_them(self) -> None:
        html = self.html_export()
        html = SavedRedditHtml(
            post_id=html.post_id,
            post_author="",
            post_score="",
            post_comment_count="",
            comments=html.comments,
        )
        rows = reconstruct_rows(
            self.free_export(),
            html,
            post_author="explicit-author",
            post_score="267",
            post_comment_count="65",
        )
        self.assertEqual("explicit-author", rows[0]["Post Author"])
        self.assertEqual("267", rows[0]["Post Score"])
        self.assertEqual("65", rows[0]["Post Comment Count"])

        with self.assertRaisesRegex(ValueError, "post author"):
            reconstruct_rows(self.free_export(), html)

    def test_html_values_take_precedence_over_explicit_fallbacks(self) -> None:
        rows = reconstruct_rows(
            self.free_export(),
            self.html_export(),
            post_author="wrong",
            post_score="0",
            post_comment_count="0",
        )
        self.assertEqual("poster", rows[0]["Post Author"])
        self.assertEqual("99", rows[0]["Post Score"])
        self.assertEqual("2", rows[0]["Post Comment Count"])
```

- [ ] **Step 5: Run focused merge tests**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reconstruct_reddit_comments.ReconstructRedditRowsTests -v
```

Expected: all strict merge tests pass.

- [ ] **Step 6: Commit Task 3**

```powershell
git add tools/reconstruct_reddit_comments.py tests/test_reconstruct_reddit_comments.py
git commit -m "feat: reconstruct Reddit rows by comment ID"
```

### Task 4: Write safe matching XLSX and CSV outputs

**Files:**
- Modify: `tools/reconstruct_reddit_comments.py`
- Modify: `tests/test_reconstruct_reddit_comments.py`

- [ ] **Step 1: Write failing output tests**

Append imports to `tests/test_reconstruct_reddit_comments.py`:

```python
import csv
import shutil
from pathlib import Path

from openpyxl import load_workbook
from tools.output_path_safety import OutputPathConflictError
from tools.reconstruct_reddit_comments import write_outputs
```

Add a second test class:

```python
class ReconstructRedditOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path.cwd() / ".tmp-tests" / "reddit-output"
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp.mkdir(parents=True)
        self.input_csv = self.tmp / "free.csv"
        self.input_html = self.tmp / "post.html"
        self.input_csv.write_text("source", encoding="utf-8")
        self.input_html.write_text("<html></html>", encoding="utf-8")
        self.rows = [{
            header: value
            for header, value in zip(
                OUTPUT_HEADERS,
                (
                    "Title", "Body", "URL", "poster", "99", "1",
                    "author", "time", "4", 0, "No",
                    '=HYPERLINK("https://example.com")',
                    "comment-url", "c1", "p1",
                ),
            )
        }]

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_writes_identical_header_and_rows_to_xlsx_and_utf8_bom_csv(self) -> None:
        xlsx = self.tmp / "result.xlsx"
        csv_path = self.tmp / "result.csv"

        write_outputs(
            self.rows,
            input_paths=(self.input_csv, self.input_html),
            output_xlsx=xlsx,
            output_csv=csv_path,
            overwrite=False,
        )

        workbook = load_workbook(xlsx, data_only=False)
        sheet = workbook.active
        self.assertEqual(list(OUTPUT_HEADERS), [cell.value for cell in sheet[1]])
        self.assertEqual("s", sheet["L2"].data_type)
        self.assertTrue(str(sheet["L2"].value).startswith("="))

        with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
            csv_rows = list(csv.reader(stream))
        self.assertEqual(list(OUTPUT_HEADERS), csv_rows[0])
        self.assertEqual(sheet.max_row, len(csv_rows))
        self.assertEqual(sheet["L2"].value, csv_rows[1][11])
        self.assertTrue(csv_path.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_preserves_unicode_commas_quotes_newlines_and_formula_like_text(self) -> None:
        self.rows[0]["Title"] = '标题，"引用"'
        self.rows[0]["Post Body"] = "第一行\n第二行 🤝"
        self.rows[0]["Author"] = "+author"
        self.rows[0]["Time"] = "-2026-07-01"
        self.rows[0]["Comment"] = '@mention, "quoted"\nnext line'
        xlsx = self.tmp / "unicode.xlsx"
        csv_path = self.tmp / "unicode.csv"

        write_outputs(
            self.rows,
            input_paths=(self.input_csv, self.input_html),
            output_xlsx=xlsx,
            output_csv=csv_path,
            overwrite=False,
        )

        workbook = load_workbook(xlsx, data_only=False)
        sheet = workbook.active
        with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
            csv_rows = list(csv.reader(stream))
        for column in (1, 2, 7, 8, 12):
            self.assertEqual(sheet.cell(2, column).value, csv_rows[1][column - 1])
            self.assertEqual("s", sheet.cell(2, column).data_type)

    def test_rejects_existing_outputs_and_input_output_aliases(self) -> None:
        existing = self.tmp / "existing.xlsx"
        existing.write_text("keep", encoding="utf-8")
        with self.assertRaises(OutputPathConflictError):
            write_outputs(
                self.rows,
                input_paths=(self.input_csv, self.input_html),
                output_xlsx=existing,
                output_csv=self.tmp / "new.csv",
                overwrite=False,
            )
        self.assertEqual("keep", existing.read_text(encoding="utf-8"))

        with self.assertRaises(OutputPathConflictError):
            write_outputs(
                self.rows,
                input_paths=(self.input_csv, self.input_html),
                output_xlsx=self.input_csv,
                output_csv=self.tmp / "new.csv",
                overwrite=True,
            )
```

- [ ] **Step 2: Run output tests and verify failure**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reconstruct_reddit_comments.ReconstructRedditOutputTests -v
```

Expected: FAIL because `write_outputs` is not defined.

- [ ] **Step 3: Implement output validation and atomic writes**

Add imports to `tools/reconstruct_reddit_comments.py`:

```python
import csv
from contextlib import ExitStack

from openpyxl import Workbook

try:
    from tools.output_path_safety import (
        atomic_output_path,
        ensure_output_paths_safe,
    )
except ImportError:
    from output_path_safety import atomic_output_path, ensure_output_paths_safe
```

Append:

```python
def _write_xlsx(
    rows: list[dict[str, str | int]],
    path: Path,
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reddit Comments"
    sheet.append(list(OUTPUT_HEADERS))
    for row in rows:
        sheet.append([row[header] for header in OUTPUT_HEADERS])
    for sheet_row in sheet.iter_rows():
        for cell in sheet_row:
            if isinstance(cell.value, str):
                cell.data_type = "s"
    workbook.save(path)


def _write_csv(
    rows: list[dict[str, str | int]],
    path: Path,
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(
    rows: list[dict[str, str | int]],
    *,
    input_paths: tuple[Path, Path],
    output_xlsx: Path,
    output_csv: Path,
    overwrite: bool,
) -> None:
    ensure_output_paths_safe(
        list(input_paths),
        [output_xlsx, output_csv],
        overwrite=overwrite,
    )
    with ExitStack() as stack:
        staged_xlsx = stack.enter_context(atomic_output_path(output_xlsx))
        staged_csv = stack.enter_context(atomic_output_path(output_csv))
        _write_xlsx(rows, staged_xlsx)
        _write_csv(rows, staged_csv)
```

- [ ] **Step 4: Add a failure-before-replace test**

Append:

```python
    def test_does_not_leave_outputs_when_csv_staging_fails(self) -> None:
        from unittest.mock import patch

        xlsx = self.tmp / "result.xlsx"
        csv_path = self.tmp / "result.csv"
        with patch(
            "tools.reconstruct_reddit_comments._write_csv",
            side_effect=OSError("simulated"),
        ):
            with self.assertRaisesRegex(OSError, "simulated"):
                write_outputs(
                    self.rows,
                    input_paths=(self.input_csv, self.input_html),
                    output_xlsx=xlsx,
                    output_csv=csv_path,
                    overwrite=False,
                )
        self.assertFalse(xlsx.exists())
        self.assertFalse(csv_path.exists())
```

- [ ] **Step 5: Run output tests**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reconstruct_reddit_comments.ReconstructRedditOutputTests -v
```

Expected: all output tests pass.

- [ ] **Step 6: Commit Task 4**

```powershell
git add tools/reconstruct_reddit_comments.py tests/test_reconstruct_reddit_comments.py
git commit -m "feat: write safe Reddit reconstruction outputs"
```

### Task 5: Add the CLI and end-to-end workflow

**Files:**
- Modify: `tools/reconstruct_reddit_comments.py`
- Modify: `tests/test_reconstruct_reddit_comments.py`

- [ ] **Step 1: Write the failing CLI end-to-end test**

Append imports:

```python
import subprocess
import sys
```

Append test class:

```python
class ReconstructRedditCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path.cwd() / ".tmp-tests" / "reddit-cli"
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_cli_generates_both_outputs_without_printing_comment_content(self) -> None:
        free_csv = self.tmp / "free.csv"
        with free_csv.open("w", encoding="utf-8-sig", newline="") as stream:
            csv.writer(stream).writerows([
                ["title", "Title"],
                ["body", "SECRET-BODY"],
                ["url", "https://www.reddit.com/r/x/comments/p1/title/"],
                ["author_name", "date_time", "comment", "upvote_number", "comment_url"],
                ["SECRET-AUTHOR", "2026-07-01T00:00:00Z", "SECRET-COMMENT", "", "https://www.reddit.com/r/x/comments/p1/comment/c1/"],
            ])
        html = self.tmp / "post.html"
        html.write_text("""
        <shreddit-post thingid="t3_p1" author="poster"
          score="99" comment-count="1"></shreddit-post>
        <shreddit-comment thingid="t1_c1" parentid="t3_p1"
          depth="0" score="4"></shreddit-comment>
        """, encoding="utf-8")
        xlsx = self.tmp / "result.xlsx"
        csv_path = self.tmp / "result.csv"

        completed = subprocess.run(
            [
                sys.executable,
                "tools/reconstruct_reddit_comments.py",
                "--free-csv", str(free_csv),
                "--html", str(html),
                "--output-xlsx", str(xlsx),
                "--output-csv", str(csv_path),
            ],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertTrue(xlsx.exists())
        self.assertTrue(csv_path.exists())
        self.assertIn("评论总数: 1", completed.stdout)
        self.assertIn("HTML 匹配数: 1", completed.stdout)
        self.assertNotIn("SECRET-AUTHOR", completed.stdout)
        self.assertNotIn("SECRET-COMMENT", completed.stdout)
        self.assertNotIn("SECRET-BODY", completed.stdout)
```

- [ ] **Step 2: Run the CLI test and verify failure**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reconstruct_reddit_comments.ReconstructRedditCliTests -v
```

Expected: FAIL because the CLI entry point is absent.

- [ ] **Step 3: Implement the CLI**

Add imports:

```python
import argparse

try:
    from tools.reddit_free_csv import parse_free_reddit_csv
    from tools.reddit_saved_html import parse_saved_reddit_html
except ImportError:
    from reddit_free_csv import parse_free_reddit_csv
    from reddit_saved_html import parse_saved_reddit_html
```

Append:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministically reconstruct Reddit comment hierarchy from "
            "a free CSV export and saved HTML."
        )
    )
    parser.add_argument("--free-csv", required=True, type=Path)
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--output-xlsx", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--post-author")
    parser.add_argument("--post-score")
    parser.add_argument("--post-comment-count")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    free = parse_free_reddit_csv(args.free_csv)
    html = parse_saved_reddit_html(args.html)
    rows = reconstruct_rows(
        free,
        html,
        post_author=args.post_author,
        post_score=args.post_score,
        post_comment_count=args.post_comment_count,
    )
    write_outputs(
        rows,
        input_paths=(args.free_csv, args.html),
        output_xlsx=args.output_xlsx,
        output_csv=args.output_csv,
        overwrite=args.overwrite,
    )
    missing_scores = sum(row["Score"] == "" for row in rows)
    print(f"免费 CSV: {args.free_csv.resolve()}")
    print(f"Reddit HTML: {args.html.resolve()}")
    print(f"输出 XLSX: {args.output_xlsx.resolve()}")
    print(f"输出 CSV: {args.output_csv.resolve()}")
    print(f"评论总数: {len(rows)}")
    print(f"HTML 匹配数: {len(rows)}")
    print(f"缺失评论点赞数: {missing_scores}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Add overwrite and explicit post fallback CLI tests**

Append:

```python
    def test_cli_accepts_explicit_post_values_when_html_omits_them(self) -> None:
        free_csv = self.tmp / "free.csv"
        with free_csv.open("w", encoding="utf-8-sig", newline="") as stream:
            csv.writer(stream).writerows([
                ["title", "Title"],
                ["body", "Body"],
                ["url", "https://www.reddit.com/r/x/comments/p1/title/"],
                ["author_name", "date_time", "comment", "comment_url"],
                ["a", "t", "c", "https://www.reddit.com/r/x/comments/p1/comment/c1/"],
            ])
        html = self.tmp / "post.html"
        html.write_text("""
        <shreddit-post thingid="t3_p1"></shreddit-post>
        <shreddit-comment thingid="t1_c1" parentid="t3_p1"
          depth="0"></shreddit-comment>
        """, encoding="utf-8")
        xlsx = self.tmp / "result.xlsx"
        csv_path = self.tmp / "result.csv"
        command = [
            sys.executable,
            "tools/reconstruct_reddit_comments.py",
            "--free-csv", str(free_csv),
            "--html", str(html),
            "--output-xlsx", str(xlsx),
            "--output-csv", str(csv_path),
            "--post-author", "poster",
            "--post-score", "267",
            "--post-comment-count", "65",
        ]

        first = subprocess.run(
            command,
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
        second = subprocess.run(
            command,
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )
        overwritten = subprocess.run(
            [*command, "--overwrite"],
            cwd=Path.cwd(),
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, first.returncode, first.stderr)
        self.assertNotEqual(0, second.returncode)
        self.assertIn("already exists", second.stderr)
        self.assertEqual(0, overwritten.returncode, overwritten.stderr)
```

- [ ] **Step 5: Run CLI and all new tool tests**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_free_csv tests.test_reddit_saved_html tests.test_reconstruct_reddit_comments -v
```

Expected: all tests pass.

- [ ] **Step 6: Commit Task 5**

```powershell
git add tools/reconstruct_reddit_comments.py tests/test_reconstruct_reddit_comments.py
git commit -m "feat: add Reddit reconstruction CLI"
```

### Task 6: Validate against the real free export and protect the existing suite

**Files:**
- Modify only when a test proves a defect:
  - `tools/reddit_free_csv.py`
  - `tools/reddit_saved_html.py`
  - `tools/reconstruct_reddit_comments.py`
  - corresponding tests
- Do not create final data outputs until the user supplies the saved HTML

- [ ] **Step 1: Parse the real free CSV without producing outputs**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -c "from pathlib import Path; from tools.reddit_free_csv import parse_free_reddit_csv; r=parse_free_reddit_csv(Path(r'C:\Users\Eddie.J.Lu\Downloads\免费数据.csv')); print({'post_id': r.post_id, 'comments': len(r.comments), 'title_present': bool(r.title), 'body_present': bool(r.body)})"
```

Expected:

- post ID is `1tbschi`;
- exactly 62 comments parse successfully;
- title and body are present;
- the command prints counts only, not author names or comment content.

- [ ] **Step 2: Run all existing and new tests**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -p 'test_*.py'
```

Expected: the original 184 tests plus all new tests pass with zero failures.

- [ ] **Step 3: Run deterministic safety scans**

Run:

```powershell
rg -n "openai|anthropic|gemini|llm|fuzzy|difflib|requests|httpx|selenium|playwright" tools/reddit_free_csv.py tools/reddit_saved_html.py tools/reconstruct_reddit_comments.py
```

Expected: no matches.

Run:

```powershell
git status --short
```

Expected: no generated XLSX/CSV, saved HTML, downloaded comments, user identifiers, or unrelated files are staged.

- [ ] **Step 4: Validate the first 20 rows against the paid development sample after real HTML is supplied**

After the user provides the saved HTML, run the production CLI once to generate the candidate XLSX/CSV. Then run a development-only comparison that:

- reads `C:\Users\Eddie.J.Lu\Downloads\付费插件获取.csv` as text through `tools.csv_excel_compat`;
- reads the candidate CSV as UTF-8 BOM text;
- identifies the same first 20 comments by exact `Author`, `Time`, and `Comment` equality, never fuzzy matching;
- asserts equality for `Score`, `Thread Level`, and `Is Reply`;
- reports only row numbers and mismatched field names, never comment text or author names;
- remains test-only code and is not imported by `tools/reconstruct_reddit_comments.py`.

Expected: all 20 paid sample rows match. If exact content identity cannot associate a paid row, stop the validation and report the unmatched paid row number; do not change the production join key from `Comment ID`.

- [ ] **Step 5: Apply verification-before-completion**

Before claiming the program is ready:

- cite the exact full-suite command and fresh result;
- state that real end-to-end HTML validation is pending until the user provides the saved HTML;
- confirm no AI or external service is called;
- confirm inputs are never overwritten;
- confirm production does not require the paid CSV.
- cite the paid-sample comparison result once real HTML is available.

- [ ] **Step 6: Commit any test-proven fixes**

If Step 1 or Step 2 required code changes:

```powershell
git add tools/reddit_free_csv.py tools/reddit_saved_html.py tools/reconstruct_reddit_comments.py tests/test_reddit_free_csv.py tests/test_reddit_saved_html.py tests/test_reconstruct_reddit_comments.py
git commit -m "fix: validate Reddit reconstruction against real export"
```

If no code changes were required, do not create an empty commit.
