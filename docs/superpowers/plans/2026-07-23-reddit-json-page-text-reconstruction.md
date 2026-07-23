# Reddit JSON + Page Text Reconstruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a deterministic CLI that validates a Reddit JSON export, aligns its comments with copied Reddit page text, adds post/comment scores, and writes matching 14-column XLSX and CSV files.

**Architecture:** Add focused JSON and page-text adapters that return immutable typed records, then combine those records in a small exact merger. Keep the already-reviewed paired output transaction in `reconstruct_reddit_comments.py`, parameterize it by header contract, and replace only the production CLI path with JSON + TXT inputs; legacy CSV/HTML parsers remain testable but are no longer production dependencies.

**Tech Stack:** Python 3.11+, standard library (`argparse`, `csv`, `dataclasses`, `html`, `json`, `re`, `unicodedata`), existing `openpyxl`, existing output-safety helpers, `unittest`.

---

## File map

```text
tools/
├── reddit_json_export.py                 Validate and normalize JSON records
├── reddit_page_text.py                   Decode, parse, and align copied page text
├── reddit_json_text_merge.py             Build the fixed 14-column row contract
└── reconstruct_reddit_comments.py        Reuse paired writer; expose new formal CLI

tests/
├── test_reddit_json_export.py
├── test_reddit_page_text.py
├── test_reddit_json_text_merge.py
└── test_reconstruct_reddit_comments.py   Preserve writer tests; replace CLI tests
```

Do not change the existing product-comment cleaning, standardization, pseudonymization, or merge configuration. Do not delete the legacy free-CSV or saved-HTML parser tests.

### Task 1: Parse and validate the Reddit JSON export

**Files:**
- Create: `tools/reddit_json_export.py`
- Create: `tests/test_reddit_json_export.py`

- [ ] **Step 1: Write the failing typed-parser tests**

Create `tests/test_reddit_json_export.py` with a helper that writes this complete minimal fixture:

```python
from __future__ import annotations

import json
import shutil
import unittest
from pathlib import Path

from tools.reddit_json_export import parse_reddit_json


def valid_payload() -> dict[str, object]:
    return {
        "meta": {
            "collectedCommentCount": 2,
            "reportedByApi": 3,
            "discrepancy": 1,
            "completeness": "complete",
            "failedMore": 0,
            "failedNodes": "",
            "failedReasons": "",
            "failedDetails": "",
        },
        "post": {
            "id": "p1",
            "subreddit": "desksetup",
            "title": "Title",
            "content": "Body",
            "author": "poster",
            "num_comments": 3,
        },
        "comments": [
            {
                "id": "c1",
                "parent_id": "t3_p1",
                "content": "Root",
                "depth": 0,
                "username": "alpha",
                "date": "2026-07-01T00:00:00.000Z",
                "created_utc": 1782864000,
            },
            {
                "id": "c2",
                "parent_id": "t1_c1",
                "content": "Reply",
                "depth": 1,
                "username": "beta",
                "date": "2026-07-01T00:01:00.000Z",
                "created_utc": 1782864060,
            },
        ],
    }


class RedditJsonExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path.cwd() / ".tmp-tests" / "reddit-json"
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write_payload(
        self,
        payload: dict[str, object],
        *,
        encoding: str = "utf-8-sig",
    ) -> Path:
        path = self.tmp / "reddit.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding=encoding,
        )
        return path

    def test_parses_post_comments_and_normalizes_ids(self) -> None:
        export = parse_reddit_json(self.write_payload(valid_payload()))

        self.assertEqual("p1", export.post.id)
        self.assertEqual("desksetup", export.post.subreddit)
        self.assertEqual(3, export.post.num_comments)
        self.assertEqual(2, export.meta.collected_comment_count)
        self.assertEqual(1, export.meta.discrepancy)
        self.assertEqual(["c1", "c2"], [item.id for item in export.comments])
        self.assertEqual(["p1", "c1"], [item.parent_id for item in export.comments])
        self.assertEqual([0, 1], [item.depth for item in export.comments])
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_json_export -v
```

Expected: import failure because `tools.reddit_json_export` does not exist.

- [ ] **Step 3: Implement the typed JSON adapter**

Create `tools/reddit_json_export.py`:

```python
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RedditJsonError(ValueError):
    """Safe validation error that never includes source field contents."""


@dataclass(frozen=True)
class RedditMeta:
    collected_comment_count: int
    reported_by_api: int
    discrepancy: int


@dataclass(frozen=True)
class RedditPost:
    id: str
    subreddit: str
    title: str
    content: str
    author: str
    num_comments: int


@dataclass(frozen=True)
class RedditJsonComment:
    id: str
    parent_id: str
    content: str
    depth: int
    username: str
    date: str
    created_utc: int


@dataclass(frozen=True)
class RedditJsonExport:
    meta: RedditMeta
    post: RedditPost
    comments: tuple[RedditJsonComment, ...]


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RedditJsonError(f"{label} must be an object")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise RedditJsonError(f"{label} must be an array")
    return value


def _text(value: Any, label: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise RedditJsonError(f"{label} must be text")
    if not allow_empty and not value.strip():
        raise RedditJsonError(f"{label} must not be blank")
    return value


def _integer(value: Any, label: str, *, nonnegative: bool = False) -> int:
    if type(value) is not int:
        raise RedditJsonError(f"{label} must be an integer")
    if nonnegative and value < 0:
        raise RedditJsonError(f"{label} must be nonnegative")
    return value


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _normalize_id(value: Any, label: str) -> str:
    raw = _text(value, label)
    prefix = raw[:3]
    if prefix.isascii() and prefix.lower() in ("t1_", "t3_"):
        raw = raw[3:]
    if not raw or not raw.isascii() or not raw.isalnum():
        raise RedditJsonError(f"{label} must be an ASCII alphanumeric ID")
    return raw.lower()


def parse_reddit_json(path: Path) -> RedditJsonExport:
    try:
        root = _object(
            json.loads(path.read_text(encoding="utf-8-sig")),
            "JSON root",
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise RedditJsonError("JSON is not valid UTF-8 JSON") from error

    meta_object = _object(root.get("meta"), "meta")
    post_object = _object(root.get("post"), "post")
    comment_objects = _list(root.get("comments"), "comments")

    if meta_object.get("completeness") != "complete":
        raise RedditJsonError("meta.completeness must equal complete")
    collected = _integer(
        meta_object.get("collectedCommentCount"),
        "meta.collectedCommentCount",
        nonnegative=True,
    )
    reported = _integer(
        meta_object.get("reportedByApi"),
        "meta.reportedByApi",
        nonnegative=True,
    )
    discrepancy = _integer(
        meta_object.get("discrepancy"),
        "meta.discrepancy",
        nonnegative=True,
    )
    if collected != len(comment_objects):
        raise RedditJsonError(
            "meta.collectedCommentCount must equal comments length"
        )
    if reported - collected != discrepancy:
        raise RedditJsonError("meta discrepancy counts are inconsistent")
    if _integer(meta_object.get("failedMore"), "meta.failedMore") != 0:
        raise RedditJsonError("meta.failedMore must equal zero")
    for name in ("failedNodes", "failedReasons", "failedDetails"):
        if not _empty(meta_object.get(name)):
            raise RedditJsonError(f"meta.{name} must be empty")

    post = RedditPost(
        id=_normalize_id(post_object.get("id"), "post.id"),
        subreddit=_text(post_object.get("subreddit"), "post.subreddit"),
        title=_text(post_object.get("title"), "post.title"),
        content=_text(post_object.get("content"), "post.content"),
        author=_text(post_object.get("author"), "post.author"),
        num_comments=_integer(
            post_object.get("num_comments"),
            "post.num_comments",
            nonnegative=True,
        ),
    )
    if post.num_comments != reported:
        raise RedditJsonError(
            "post.num_comments must equal meta.reportedByApi"
        )

    comments: list[RedditJsonComment] = []
    seen: set[str] = set()
    for index, raw_value in enumerate(comment_objects, start=1):
        raw = _object(raw_value, f"comments item {index}")
        comment_id = _normalize_id(raw.get("id"), f"comments item {index} id")
        if comment_id in seen:
            raise RedditJsonError(f"duplicate comment ID at item {index}")
        seen.add(comment_id)
        comments.append(
            RedditJsonComment(
                id=comment_id,
                parent_id=_normalize_id(
                    raw.get("parent_id"),
                    f"comments item {index} parent_id",
                ),
                content=_text(
                    raw.get("content"),
                    f"comments item {index} content",
                ),
                depth=_integer(
                    raw.get("depth"),
                    f"comments item {index} depth",
                    nonnegative=True,
                ),
                username=_text(
                    raw.get("username"),
                    f"comments item {index} username",
                ),
                date=_text(raw.get("date"), f"comments item {index} date"),
                created_utc=_integer(
                    raw.get("created_utc"),
                    f"comments item {index} created_utc",
                ),
            )
        )

    by_id = {item.id: item for item in comments}
    for index, comment in enumerate(comments, start=1):
        if comment.depth == 0:
            if comment.parent_id != post.id:
                raise RedditJsonError(
                    f"comments item {index} root parent must be post ID"
                )
            continue
        parent = by_id.get(comment.parent_id)
        if parent is None:
            raise RedditJsonError(
                f"comments item {index} parent comment is missing"
            )
        if parent.depth != comment.depth - 1:
            raise RedditJsonError(
                f"comments item {index} parent depth is inconsistent"
            )

    return RedditJsonExport(
        meta=RedditMeta(collected, reported, discrepancy),
        post=post,
        comments=tuple(comments),
    )
```

- [ ] **Step 4: Add complete schema and graph regression tests**

Add table-driven tests that mutate one field at a time:

```python
    def test_rejects_incomplete_or_inconsistent_meta(self) -> None:
        cases = (
            ("completeness", "partial", "completeness"),
            ("collectedCommentCount", 1, "comments length"),
            ("reportedByApi", 4, "discrepancy"),
            ("discrepancy", 0, "discrepancy"),
            ("failedMore", 1, "failedMore"),
            ("failedNodes", ["c1"], "failedNodes"),
        )
        for field, value, message in cases:
            with self.subTest(field=field):
                payload = valid_payload()
                payload["meta"][field] = value  # type: ignore[index]
                with self.assertRaisesRegex(ValueError, message):
                    parse_reddit_json(self.write_payload(payload))

    def test_rejects_duplicate_missing_parent_and_wrong_depth(self) -> None:
        duplicate = valid_payload()
        duplicate["comments"][1]["id"] = "C1"  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "duplicate"):
            parse_reddit_json(self.write_payload(duplicate))

        missing_parent = valid_payload()
        missing_parent["comments"][1]["parent_id"] = "missing"  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "parent comment is missing"):
            parse_reddit_json(self.write_payload(missing_parent))

        wrong_depth = valid_payload()
        wrong_depth["comments"][1]["depth"] = 2  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "parent depth"):
            parse_reddit_json(self.write_payload(wrong_depth))
```

Also add explicit tests for:

```python
    def test_rejects_non_ascii_ids_bool_integers_and_invalid_json(self) -> None:
        payload = valid_payload()
        payload["comments"][0]["id"] = "K"  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "ASCII"):
            parse_reddit_json(self.write_payload(payload))

        payload = valid_payload()
        payload["comments"][0]["depth"] = True  # type: ignore[index]
        with self.assertRaisesRegex(ValueError, "integer"):
            parse_reddit_json(self.write_payload(payload))

        invalid = self.tmp / "invalid.json"
        invalid.write_text("{secret invalid", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "valid UTF-8 JSON"):
            parse_reddit_json(invalid)
```

- [ ] **Step 5: Run Task 1 tests and commit**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_json_export -v
```

Expected: all JSON adapter tests pass.

Commit:

```powershell
git add tools/reddit_json_export.py tests/test_reddit_json_export.py
git commit -m "feat: validate Reddit JSON exports"
```

### Task 2: Parse post metrics from copied page text

**Files:**
- Create: `tools/reddit_page_text.py`
- Create: `tests/test_reddit_page_text.py`

- [ ] **Step 1: Write failing decoding and post-metric tests**

Create a fixture based on the approved UI sequence:

```python
PAGE_PREFIX = """转到“desksetup”
r/desksetup
•
8小时前
•
品牌关联
ManBdo

Latest addition to my setup : Screenbar Halo 2
🖼️ • Photos

This is the post body.

赞同
99

反对

5
转到评论
转载
共享
排序方式：
实时（默认）
评论区域
"""
```

Write:

```python
from __future__ import annotations

import shutil
import unittest
from pathlib import Path

from tests.test_reddit_json_export import valid_payload
from tools.reddit_json_export import parse_reddit_json
from tools.reddit_page_text import parse_reddit_page_text


class RedditPageTextPostTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path.cwd() / ".tmp-tests" / "reddit-page-text"
        shutil.rmtree(self.tmp, ignore_errors=True)
        self.tmp.mkdir(parents=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def export(self):
        payload = valid_payload()
        payload["meta"]["reportedByApi"] = 5
        payload["meta"]["discrepancy"] = 3
        payload["post"].update({
            "subreddit": "desksetup",
            "author": "ManBdo",
            "title": "Latest addition to my setup : Screenbar Halo 2",
            "content": "This is the post body.",
            "num_comments": 5,
        })
        path = self.tmp / "post.json"
        path.write_text(
            __import__("json").dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return parse_reddit_json(path)

    def write_text(self, text: str, encoding: str = "utf-8-sig") -> Path:
        path = self.tmp / "page.txt"
        path.write_text(text, encoding=encoding)
        return path

    def test_extracts_raw_time_post_score_and_comment_count(self) -> None:
        result = parse_reddit_page_text(
            self.write_text(PAGE_PREFIX),
            self.export(),
            require_comments=False,
        )
        self.assertEqual("8小时前", result.post_time)
        self.assertEqual(99, result.post_score)
        self.assertEqual(5, result.post_comment_count)
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_page_text.RedditPageTextPostTests -v
```

Expected: import failure because the page-text adapter does not exist.

- [ ] **Step 3: Implement deterministic decoding, normalization, and post parsing**

Create `tools/reddit_page_text.py` with:

```python
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from tools.reddit_json_export import RedditJsonExport


class RedditPageTextError(ValueError):
    """Safe page-text error containing positions/categories, not source text."""


_RELATIVE_TIME = re.compile(
    r"^(?:刚刚|[0-9]+(?:分钟|小时|天|周|个月|年)前)$",
    re.ASCII,
)
_UNSIGNED_INTEGER = re.compile(
    r"^(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)$",
    re.ASCII,
)
_SIGNED_INTEGER = re.compile(
    r"^-?(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)$",
    re.ASCII,
)


@dataclass(frozen=True)
class PageCommentMetric:
    score: int | None


@dataclass(frozen=True)
class RedditPageText:
    post_time: str
    post_score: int
    post_comment_count: int
    comments: tuple[PageCommentMetric, ...]


def _read_page_text(path: Path) -> str:
    raw = path.read_bytes()
    attempts: tuple[tuple[str, bool], ...] = (
        ("utf-8-sig", True),
        ("utf-16", raw.startswith((b"\xff\xfe", b"\xfe\xff"))),
        ("gb18030", True),
    )
    for encoding, enabled in attempts:
        if not enabled:
            continue
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise RedditPageTextError("page text encoding is unsupported")


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]


def normalize_author(value: str) -> str:
    candidate = unicodedata.normalize("NFC", html.unescape(value)).strip()
    if candidate.startswith("u/"):
        candidate = candidate[2:]
    if candidate == "[已删除]":
        return "[deleted]"
    return candidate


def _integer(value: str, *, signed: bool, label: str) -> int:
    pattern = _SIGNED_INTEGER if signed else _UNSIGNED_INTEGER
    if not pattern.fullmatch(value):
        raise RedditPageTextError(f"{label} is not an explicit integer")
    return int(value.replace(",", ""))


def _one_index(lines: list[str], value: str, label: str) -> int:
    matches = [index for index, line in enumerate(lines) if line == value]
    if len(matches) != 1:
        raise RedditPageTextError(f"{label} must occur exactly once")
    return matches[0]


def _post_metrics(
    post_lines: list[str],
    export: RedditJsonExport,
) -> tuple[str, int, int]:
    subreddit_index = _one_index(
        post_lines,
        f"r/{export.post.subreddit}",
        "post subreddit marker",
    )
    title_index = _one_index(post_lines, export.post.title, "post title")
    if subreddit_index >= title_index:
        raise RedditPageTextError("post subreddit marker must precede title")
    pre_title = post_lines[subreddit_index + 1 : title_index]
    author_matches = [
        line for line in pre_title
        if not line.endswith("头像")
        and normalize_author(line) == normalize_author(export.post.author)
    ]
    if len(author_matches) != 1:
        raise RedditPageTextError("post author must match exactly once")
    time_matches = [line for line in pre_title if _RELATIVE_TIME.fullmatch(line)]
    if len(time_matches) != 1:
        raise RedditPageTextError("post time must match exactly once")

    comment_area = _one_index(post_lines, "转到评论", "post comment action")
    if comment_area <= title_index:
        raise RedditPageTextError("post comment action must follow title")
    vote_lines = [line for line in post_lines[title_index:comment_area] if line]
    sequences: list[tuple[str, str]] = []
    for index in range(len(vote_lines) - 3):
        if vote_lines[index] == "赞同" and vote_lines[index + 2] == "反对":
            sequences.append((vote_lines[index + 1], vote_lines[index + 3]))
    if len(sequences) != 1:
        raise RedditPageTextError("post vote sequence must occur exactly once")
    score = _integer(sequences[0][0], signed=False, label="post score")
    count = _integer(
        sequences[0][1],
        signed=False,
        label="post comment count",
    )
    if count != export.post.num_comments:
        raise RedditPageTextError(
            "page post comment count does not match JSON"
        )
    return time_matches[0], score, count


def parse_reddit_page_text(
    path: Path,
    export: RedditJsonExport,
    *,
    require_comments: bool = True,
) -> RedditPageText:
    lines = _lines(_read_page_text(path))
    comment_markers = [
        index for index, line in enumerate(lines) if line == "评论区域"
    ]
    if len(comment_markers) != 1:
        raise RedditPageTextError(
            "comment area marker must occur exactly once"
        )
    marker = comment_markers[0]
    post_time, post_score, post_count = _post_metrics(lines[:marker], export)
    comments = (
        _comment_metrics(lines[marker + 1 :], export)
        if require_comments
        else ()
    )
    return RedditPageText(post_time, post_score, post_count, comments)
```

Task 3 will add `_comment_metrics`; keep `require_comments=False` only as a test seam and never expose it through the CLI.

- [ ] **Step 4: Add post error, integer, and encoding tests**

Add:

```python
    def test_decodes_registered_page_text_encodings(self) -> None:
        for encoding in ("utf-8-sig", "utf-16", "gb18030"):
            with self.subTest(encoding=encoding):
                result = parse_reddit_page_text(
                    self.write_text(PAGE_PREFIX, encoding),
                    self.export(),
                    require_comments=False,
                )
                self.assertEqual(99, result.post_score)

    def test_rejects_abbreviated_score_and_comment_count_conflict(self) -> None:
        abbreviated = PAGE_PREFIX.replace("\n99\n", "\n1.2K\n")
        with self.assertRaisesRegex(ValueError, "post score"):
            parse_reddit_page_text(
                self.write_text(abbreviated),
                self.export(),
                require_comments=False,
            )

        conflict = PAGE_PREFIX.replace("\n5\n转到评论", "\n4\n转到评论")
        with self.assertRaisesRegex(ValueError, "does not match JSON"):
            parse_reddit_page_text(
                self.write_text(conflict),
                self.export(),
                require_comments=False,
            )
```

Add the remaining fixed-boundary cases:

```python
    def test_registered_integer_and_marker_boundaries(self) -> None:
        grouped = PAGE_PREFIX.replace("\n99\n", "\n1,234\n")
        result = parse_reddit_page_text(
            self.write_text(grouped),
            self.export(),
            require_comments=False,
        )
        self.assertEqual(1234, result.post_score)

        cases = (
            (PAGE_PREFIX.replace("评论区域", ""), "comment area marker"),
            (PAGE_PREFIX + "\n评论区域\n", "comment area marker"),
            (PAGE_PREFIX.replace("ManBdo", "wrong", 1), "post author"),
            (PAGE_PREFIX.replace("8小时前", "some time"), "post time"),
            (PAGE_PREFIX.replace("赞同\n99", "赞同\n1.2万"), "post score"),
            (PAGE_PREFIX.replace("转到评论", ""), "post comment action"),
        )
        for text, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    parse_reddit_page_text(
                        self.write_text(text),
                        self.export(),
                        require_comments=False,
                    )

    def test_rejects_unregistered_binary_encoding(self) -> None:
        path = self.tmp / "page.txt"
        path.write_bytes(b"\x81")
        with self.assertRaisesRegex(ValueError, "encoding"):
            parse_reddit_page_text(
                path,
                self.export(),
                require_comments=False,
            )
```

- [ ] **Step 5: Run Task 2 tests and commit**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_page_text.RedditPageTextPostTests -v
```

Expected: all post parser tests pass.

Commit:

```powershell
git add tools/reddit_page_text.py tests/test_reddit_page_text.py
git commit -m "feat: parse Reddit page post metrics"
```

### Task 3: Align page comment blocks and extract comment scores

**Files:**
- Modify: `tools/reddit_page_text.py`
- Modify: `tests/test_reddit_page_text.py`

- [ ] **Step 1: Write failing comment-alignment tests**

Use a full two-comment region:

```python
COMMENT_TEXT = """
AutoModerator
版主
•
8小时前
Wallpaper from **[Basic Apple Guy](https://example.com)** &amp; friends

赞同
3
反对
回复
奖励
共享

u/ad-user 头像
ad-user
•
已推广
Advertisement

eldergooooose__
•
8小时前
What monitor? 👀

赞同投票
反对
回复
奖励
共享
"""
```

Adapt the JSON fixture comments to `AutoModerator` and `eldergooooose__`, then assert:

```python
    def export_for_comments(self):
        from dataclasses import replace

        export = self.export()
        comments = (
            replace(
                export.comments[0],
                username="AutoModerator",
                content=(
                    "Wallpaper from **[Basic Apple Guy]"
                    "(https://example.com)** &amp; friends"
                ),
            ),
            replace(
                export.comments[1],
                username="eldergooooose__",
                content="What monitor? 👀",
            ),
        )
        return replace(export, comments=comments)

    def test_aligns_comments_and_extracts_number_or_blank_score(self) -> None:
        export = self.export_for_comments()
        result = parse_reddit_page_text(
            self.write_text(PAGE_PREFIX + COMMENT_TEXT),
            export,
        )
        self.assertEqual([3, None], [item.score for item in result.comments])
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_page_text -v
```

Expected: failure because `_comment_metrics` is undefined.

- [ ] **Step 3: Implement fixed normalization and block alignment**

Add to `tools/reddit_page_text.py`:

```python
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MARKDOWN_HEADING = re.compile(r"(?m)^\s{0,3}#{1,6}\s*")
_WHITESPACE = re.compile(r"\s+")


def normalize_content(value: str) -> str:
    normalized = unicodedata.normalize("NFC", html.unescape(value))
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = _MARKDOWN_LINK.sub(r"\1", normalized)
    normalized = _MARKDOWN_HEADING.sub("", normalized)
    normalized = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", normalized)
    normalized = re.sub(r"__([^_\n]+)__", r"\1", normalized)
    normalized = re.sub(
        r"(?<!\*)\*([^*\n]+)\*(?!\*)",
        r"\1",
        normalized,
    )
    normalized = re.sub(
        r"(?<!\w)_([^_\n]+)_(?!\w)",
        r"\1",
        normalized,
    )
    return _WHITESPACE.sub(" ", normalized).strip()


def _operation_blocks(comment_lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    start = 0
    for index, line in enumerate(comment_lines):
        if line != "共享":
            continue
        candidate = comment_lines[start : index + 1]
        start = index + 1
        nonblank = [item for item in candidate if item]
        if "反对" in nonblank and "回复" in nonblank:
            blocks.append(candidate)
    trailing = [item for item in comment_lines[start:] if item]
    if trailing and "已推广" not in trailing:
        raise RedditPageTextError("unparsed trailing page comment content")
    return blocks


def _block_author_matches(block: list[str], expected: str) -> bool:
    target = normalize_author(expected)
    return any(
        line
        and not line.endswith("头像")
        and normalize_author(line) == target
        for line in block
    )


def _block_score(block: list[str], comment_number: int) -> int | None:
    nonblank = [line for line in block if line]
    try:
        share = len(nonblank) - 1
        if nonblank[share] != "共享":
            raise ValueError
        reply = max(
            index for index in range(share)
            if nonblank[index] == "回复"
        )
        downvote = max(
            index for index in range(reply)
            if nonblank[index] == "反对"
        )
    except ValueError as error:
        raise RedditPageTextError(
            f"comment {comment_number} operation area is incomplete"
        ) from error
    prefix = nonblank[:downvote]
    if len(prefix) >= 1 and prefix[-1] == "赞同投票":
        return None
    if len(prefix) >= 2 and prefix[-2] == "赞同":
        return _integer(
            prefix[-1],
            signed=True,
            label=f"comment {comment_number} score",
        )
    raise RedditPageTextError(
        f"comment {comment_number} vote display is unsupported"
    )


def _comment_metrics(
    comment_lines: list[str],
    export: RedditJsonExport,
) -> tuple[PageCommentMetric, ...]:
    blocks = _operation_blocks(comment_lines)
    if len(blocks) != len(export.comments):
        raise RedditPageTextError(
            "page comment block count does not match JSON comments"
        )
    metrics: list[PageCommentMetric] = []
    for number, (block, expected) in enumerate(
        zip(blocks, export.comments, strict=True),
        start=1,
    ):
        if not _block_author_matches(block, expected.username):
            raise RedditPageTextError(
                f"comment {number} author does not match JSON"
            )
        flattened = normalize_content("\n".join(block))
        expected_content = normalize_content(expected.content)
        if not expected_content or flattened.count(expected_content) != 1:
            raise RedditPageTextError(
                f"comment {number} content does not match JSON"
            )
        metrics.append(PageCommentMetric(_block_score(block, number)))
    return tuple(metrics)
```

- [ ] **Step 4: Add fixed-normalization and strict-failure tests**

Add actual assertions for:

```python
    def test_deleted_author_and_markdown_html_normalization_are_fixed(self) -> None:
        self.assertEqual("[deleted]", normalize_author("[已删除]"))
        self.assertEqual("[deleted]", normalize_author("[deleted]"))
        self.assertEqual(
            "Rules/Wiki & friends",
            normalize_content(
                "## **[Rules/Wiki](https://example.com)** &amp; friends"
            ),
        )

    def test_rejects_author_content_order_and_score_mismatches(self) -> None:
        export = self.export_for_comments()
        cases = (
            (COMMENT_TEXT.replace("AutoModerator", "wrong", 1), "author"),
            (COMMENT_TEXT.replace("Wallpaper from", "Different text", 1), "content"),
            (COMMENT_TEXT.replace("赞同\n3", "赞同\n1.2K", 1), "score"),
        )
        for text, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    parse_reddit_page_text(
                        self.write_text(PAGE_PREFIX + text),
                        export,
                    )
```

Add a reversed-block test, an extra eligible comment block test, incomplete operation controls, a negative score, `1,234`, `[已删除]`, and a promoted block containing numbers that must not be used.

- [ ] **Step 5: Run Task 3 tests and commit**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_page_text -v
```

Expected: all post and comment page-text tests pass.

Commit:

```powershell
git add tools/reddit_page_text.py tests/test_reddit_page_text.py
git commit -m "feat: align Reddit page comment scores"
```

### Task 4: Build the fixed 14-column row contract

**Files:**
- Create: `tools/reddit_json_text_merge.py`
- Create: `tests/test_reddit_json_text_merge.py`

- [ ] **Step 1: Write failing row-contract tests**

Create:

```python
from __future__ import annotations

import unittest

from tools.reddit_json_export import (
    RedditJsonComment,
    RedditJsonExport,
    RedditMeta,
    RedditPost,
)
from tools.reddit_json_text_merge import (
    JSON_TEXT_OUTPUT_HEADERS,
    reconstruct_json_text_rows,
)
from tools.reddit_page_text import PageCommentMetric, RedditPageText


class RedditJsonTextMergeTests(unittest.TestCase):
    def fixture(self) -> tuple[RedditJsonExport, RedditPageText]:
        export = RedditJsonExport(
            meta=RedditMeta(2, 3, 1),
            post=RedditPost(
                "p1",
                "desksetup",
                "Title",
                "Body",
                "poster",
                3,
            ),
            comments=(
                RedditJsonComment(
                    "c1", "p1", "Root", 0, "alpha", "exact-time-1", 1
                ),
                RedditJsonComment(
                    "c2", "c1", "Reply", 1, "beta", "exact-time-2", 2
                ),
            ),
        )
        page = RedditPageText(
            "8小时前",
            99,
            3,
            (PageCommentMetric(4), PageCommentMetric(None)),
        )
        return export, page

    def test_builds_fixed_rows_in_json_order(self) -> None:
        export, page = self.fixture()

        rows = reconstruct_json_text_rows(export, page)

        self.assertEqual(14, len(JSON_TEXT_OUTPUT_HEADERS))
        self.assertEqual(
            (
                "Title", "Post Body", "Post Author", "Post Time",
                "Post Score", "Post Comment Count", "Author", "Time",
                "Score", "Thread Level", "Is Reply", "Comment",
                "Comment ID", "Parent ID",
            ),
            JSON_TEXT_OUTPUT_HEADERS,
        )
        self.assertEqual(["c1", "c2"], [row["Comment ID"] for row in rows])
        self.assertEqual(["No", "Yes"], [row["Is Reply"] for row in rows])
        self.assertEqual([4, ""], [row["Score"] for row in rows])
        self.assertTrue(all(row["Post Score"] == 99 for row in rows))
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_json_text_merge -v
```

Expected: import failure because the merger does not exist.

- [ ] **Step 3: Implement the exact merger**

Create `tools/reddit_json_text_merge.py`:

```python
from __future__ import annotations

from tools.reddit_json_export import RedditJsonExport
from tools.reddit_page_text import RedditPageText


JSON_TEXT_OUTPUT_HEADERS = (
    "Title",
    "Post Body",
    "Post Author",
    "Post Time",
    "Post Score",
    "Post Comment Count",
    "Author",
    "Time",
    "Score",
    "Thread Level",
    "Is Reply",
    "Comment",
    "Comment ID",
    "Parent ID",
)


def reconstruct_json_text_rows(
    export: RedditJsonExport,
    page: RedditPageText,
) -> list[dict[str, str | int]]:
    if page.post_comment_count != export.post.num_comments:
        raise ValueError("page and JSON post comment counts differ")
    if len(page.comments) != len(export.comments):
        raise ValueError("page and JSON matched comment counts differ")
    rows: list[dict[str, str | int]] = []
    for comment, metric in zip(
        export.comments,
        page.comments,
        strict=True,
    ):
        rows.append({
            "Title": export.post.title,
            "Post Body": export.post.content,
            "Post Author": export.post.author,
            "Post Time": page.post_time,
            "Post Score": page.post_score,
            "Post Comment Count": page.post_comment_count,
            "Author": comment.username,
            "Time": comment.date,
            "Score": "" if metric.score is None else metric.score,
            "Thread Level": comment.depth,
            "Is Reply": "No" if comment.depth == 0 else "Yes",
            "Comment": comment.content,
            "Comment ID": comment.id,
            "Parent ID": comment.parent_id,
        })
    return rows
```

- [ ] **Step 4: Add mismatch and source-fidelity tests**

Add tests proving:

```python
    def test_preserves_json_text_and_rejects_count_mismatches(self) -> None:
        from dataclasses import replace

        export, page = self.fixture()
        export = replace(
            export,
            post=replace(
                export.post,
                content='=not-a-formula\nemoji 🤝',
            ),
        )
        rows = reconstruct_json_text_rows(export, page)
        self.assertEqual('=not-a-formula\nemoji 🤝', rows[0]["Post Body"])

        wrong_page = RedditPageText(
            page.post_time,
            page.post_score,
            page.post_comment_count + 1,
            page.comments,
        )
        with self.assertRaisesRegex(ValueError, "post comment counts"):
            reconstruct_json_text_rows(export, wrong_page)
```

Because records are frozen, implement the fixture with `dataclasses.replace` rather than assigning fields. Add:

```python
    def test_rejects_comment_metric_count_mismatch(self) -> None:
        export, page = self.fixture()
        short_page = RedditPageText(
            page.post_time,
            page.post_score,
            page.post_comment_count,
            page.comments[:1],
        )
        with self.assertRaisesRegex(ValueError, "matched comment counts"):
            reconstruct_json_text_rows(export, short_page)

    def test_reply_flag_is_no_only_for_exact_zero(self) -> None:
        from dataclasses import replace

        export, page = self.fixture()
        synthetic = replace(
            export,
            comments=(
                replace(export.comments[0], depth=-1),
                export.comments[1],
            ),
        )
        rows = reconstruct_json_text_rows(synthetic, page)
        self.assertEqual("Yes", rows[0]["Is Reply"])
```

- [ ] **Step 5: Run Task 4 tests and commit**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reddit_json_text_merge -v
```

Expected: all merger tests pass.

Commit:

```powershell
git add tools/reddit_json_text_merge.py tests/test_reddit_json_text_merge.py
git commit -m "feat: build Reddit JSON text rows"
```

### Task 5: Parameterize the paired writer and replace the formal CLI

**Files:**
- Modify: `tools/reconstruct_reddit_comments.py`
- Modify: `tests/test_reconstruct_reddit_comments.py`

- [ ] **Step 1: Write failing 14-column writer and CLI tests**

Keep all legacy merger and paired-transaction regression tests. Add a writer test that calls:

```python
write_outputs(
    rows,
    headers=JSON_TEXT_OUTPUT_HEADERS,
    input_paths=(json_path, page_text_path),
    output_xlsx=xlsx_path,
    output_csv=csv_path,
    overwrite=False,
)
```

Assert both files contain the exact 14 headers, integer post/comment scores in XLSX, decimal text in CSV, and formula-like JSON text remains XLSX text.

Replace the legacy CLI test class with a JSON + page-text subprocess test:

```python
completed = subprocess.run(
    [
        sys.executable,
        "tools/reconstruct_reddit_comments.py",
        "--json", str(json_path),
        "--page-text", str(page_text_path),
        "--output-xlsx", str(xlsx_path),
        "--output-csv", str(csv_path),
    ],
    cwd=Path.cwd(),
    text=True,
    capture_output=True,
    check=False,
)
self.assertEqual(0, completed.returncode, completed.stderr)
self.assertIn("JSON comment count: 2", completed.stdout)
self.assertIn("Page comment match count: 2", completed.stdout)
self.assertIn("Missing comment score count: 1", completed.stdout)
self.assertIn("Unavailable reported comment gap: 1", completed.stdout)
self.assertNotIn("SECRET-BODY", completed.stdout)
self.assertNotIn("SECRET-COMMENT", completed.stdout)
```

- [ ] **Step 2: Run and verify RED**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reconstruct_reddit_comments -v
```

Expected: failures because `write_outputs` has no `headers` argument and CLI still expects free CSV + HTML.

- [ ] **Step 3: Parameterize writer helpers without changing transaction behavior**

Change signatures:

```python
def _validate_xlsx_string_lengths(
    rows: list[dict[str, str | int]],
    headers: tuple[str, ...],
) -> None:
    for column_number, header in enumerate(headers, start=1):
        if len(header) > _XLSX_STRING_LIMIT:
            raise ValueError(
                "XLSX string exceeds 32,767 characters at "
                f"header row, column {column_number}"
            )
    for row_number, row in enumerate(rows, start=1):
        for header in headers:
            value = row[header]
            if isinstance(value, str) and len(value) > _XLSX_STRING_LIMIT:
                raise ValueError(
                    "XLSX string exceeds 32,767 characters at "
                    f"data row {row_number}, column {header}"
                )

def _write_xlsx(
    rows: list[dict[str, str | int]],
    output_path: Path,
    headers: tuple[str, ...],
) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reddit Comments"
    for column_number, header in enumerate(headers, start=1):
        cell = sheet.cell(1, column_number, header)
        cell.data_type = "s"
    for row_number, row in enumerate(rows, start=2):
        for column_number, header in enumerate(headers, start=1):
            value = row[header]
            cell = sheet.cell(row_number, column_number, value)
            if isinstance(value, str):
                cell.data_type = "s"
    workbook.save(output_path)

def _write_csv(
    rows: list[dict[str, str | int]],
    output_path: Path,
    headers: tuple[str, ...],
) -> None:
    with output_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

def write_outputs(
    rows: list[dict[str, str | int]],
    *,
    headers: tuple[str, ...] = OUTPUT_HEADERS,
    input_paths: tuple[Path, Path],
    output_xlsx: Path,
    output_csv: Path,
    overwrite: bool,
) -> None:
    _validate_input_aliases(input_paths, output_xlsx, output_csv)
    _validate_output_roles(output_xlsx, output_csv)
    _validate_xlsx_string_lengths(rows, headers)
    requested_outputs = (output_xlsx.resolve(), output_csv.resolve())
    with _reserve_output_paths(requested_outputs):
        resolved_xlsx, resolved_csv = ensure_output_paths_safe(
            input_paths,
            requested_outputs,
            overwrite=overwrite,
        )
        staged_xlsx = _transaction_path(resolved_xlsx, "stage")
        staged_csv = _transaction_path(resolved_csv, "stage")
        try:
            with atomic_output_path(staged_xlsx) as temporary_xlsx:
                _write_xlsx(rows, temporary_xlsx, headers)
            with atomic_output_path(staged_csv) as temporary_csv:
                _write_csv(rows, temporary_csv, headers)
            _replace_output_pair(
                (
                    (staged_xlsx, resolved_xlsx),
                    (staged_csv, resolved_csv),
                )
            )
        finally:
            staged_xlsx.unlink(missing_ok=True)
            staged_csv.unlink(missing_ok=True)
```

Update every existing direct helper test to pass `OUTPUT_HEADERS`. Do not change `_reserve_output_paths`, `_replace_output_pair`, backup retention, rollback, or cleanup semantics.

- [ ] **Step 4: Replace the production parser and main workflow**

Update imports:

```python
import json
from openpyxl.utils.exceptions import IllegalCharacterError
from tools.reddit_json_export import RedditJsonError, parse_reddit_json
from tools.reddit_json_text_merge import (
    JSON_TEXT_OUTPUT_HEADERS,
    reconstruct_json_text_rows,
)
from tools.reddit_page_text import (
    RedditPageTextError,
    parse_reddit_page_text,
)
```

Replace `build_parser` and `main`:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Deterministically combine a Reddit JSON export with copied "
            "Reddit page text."
        )
    )
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--page-text", required=True, type=Path)
    parser.add_argument("--output-xlsx", required=True, type=Path)
    parser.add_argument("--output-csv", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _safe_cli_error(error: BaseException) -> str:
    if isinstance(error, IllegalCharacterError):
        return "XLSX output contains an unsupported control character"
    if isinstance(error, json.JSONDecodeError):
        return "JSON is invalid"
    return str(error)


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        json_path = arguments.json.resolve()
        page_text_path = arguments.page_text.resolve()
        output_xlsx = arguments.output_xlsx.resolve()
        output_csv = arguments.output_csv.resolve()
        export = parse_reddit_json(json_path)
        page = parse_reddit_page_text(page_text_path, export)
        rows = reconstruct_json_text_rows(export, page)
        write_outputs(
            rows,
            headers=JSON_TEXT_OUTPUT_HEADERS,
            input_paths=(json_path, page_text_path),
            output_xlsx=output_xlsx,
            output_csv=output_csv,
            overwrite=arguments.overwrite,
        )
    except (
        RedditJsonError,
        RedditPageTextError,
        IllegalCharacterError,
        OSError,
        csv.Error,
        RuntimeError,
        ValueError,
    ) as error:
        print(f"Error: {_safe_cli_error(error)}", file=sys.stderr)
        return 1

    print(f"Reddit JSON input: {json_path}")
    print(f"Reddit page text input: {page_text_path}")
    print(f"XLSX output: {output_xlsx}")
    print(f"CSV output: {output_csv}")
    print(f"JSON comment count: {len(export.comments)}")
    print(f"Page comment match count: {len(page.comments)}")
    print(
        "Missing comment score count: "
        f"{sum(item.score is None for item in page.comments)}"
    )
    print(f"Unavailable reported comment gap: {export.meta.discrepancy}")
    return 0
```

Keep legacy `reconstruct_rows` for development compatibility, but the production parser exposes no free-CSV, HTML, fallback, or paid-sample arguments.

- [ ] **Step 5: Add CLI error, overwrite, and residue regressions**

Add subprocess tests for:

- second run without `--overwrite` returns nonzero and leaves bytes unchanged;
- third run with `--overwrite` succeeds;
- invalid JSON, page author/content/order mismatch, comment-count conflict, illegal XLSX control character, and path-resolution error return nonzero without traceback;
- stderr never contains secret JSON title/body/author/comment or raw malformed page lines;
- missing IDs may be reported only by safe item number or normalized ID;
- no `.reddit-stage`, `.reddit-backup`, `.lock`, XLSX, or CSV residue after pre-commit failures.

Use explicit assertions:

```python
self.assertNotEqual(0, failed.returncode)
self.assertNotIn("Traceback", failed.stderr)
for secret in ("SECRET-TITLE", "SECRET-BODY", "SECRET-AUTHOR", "SECRET-COMMENT"):
    self.assertNotIn(secret, failed.stdout + failed.stderr)
```

- [ ] **Step 6: Run Task 5 tests and commit**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest tests.test_reconstruct_reddit_comments -v
```

Expected: all legacy merger, paired writer, and new CLI tests pass.

Commit:

```powershell
git add tools/reconstruct_reddit_comments.py tests/test_reconstruct_reddit_comments.py
git commit -m "feat: add Reddit JSON page-text CLI"
```

### Task 6: Validate the real JSON and run the complete safety suite

**Files:**
- Modify only if a failing regression proves a defect:
  - `tools/reddit_json_export.py`
  - `tools/reddit_page_text.py`
  - `tools/reddit_json_text_merge.py`
  - `tools/reconstruct_reddit_comments.py`
  - corresponding tests
- Do not generate final XLSX/CSV until the matching full page `.txt` exists

- [ ] **Step 1: Parse the real JSON without exposing content**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -c "from pathlib import Path; from tools.reddit_json_export import parse_reddit_json; r=parse_reddit_json(Path(r'C:\Users\Eddie.J.Lu\Downloads\Reddit-desksetup-1tbschi.json')); print({'post_id': r.post.id, 'reported': r.meta.reported_by_api, 'collected': r.meta.collected_comment_count, 'gap': r.meta.discrepancy, 'comments': len(r.comments), 'max_depth': max(c.depth for c in r.comments)})"
```

Expected:

```text
post_id=1tbschi
reported=65
collected=62
gap=3
comments=62
max_depth=5
```

The command must not print authors, title, body, or comments.

- [ ] **Step 2: Run all tests**

Run:

```powershell
& 'C:\Users\Eddie.J.Lu\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m unittest discover -s tests -p 'test_*.py'
```

Expected: all pre-existing and new tests pass with zero failures.

- [ ] **Step 3: Run deterministic safety scans**

Run:

```powershell
rg -n "openai|anthropic|gemini|llm|fuzzy|difflib|requests|httpx|selenium|playwright" tools/reddit_json_export.py tools/reddit_page_text.py tools/reddit_json_text_merge.py tools/reconstruct_reddit_comments.py
```

Expected: no production matching dependency on AI, fuzzy matching, network clients, or browser automation.

Run:

```powershell
git diff --check
git status --short
```

Expected: no user JSON/TXT, generated XLSX/CSV, author names, comment content, temporary files, or unrelated files are staged.

- [ ] **Step 4: Apply verification-before-completion**

Before claiming code readiness:

- cite the exact focused and full-suite commands with fresh counts;
- confirm the real JSON result is 62 collected / 65 reported / gap 3 / maximum depth 5;
- confirm production CLI accepts only JSON + page TXT;
- confirm free CSV, paid CSV, and HTML are not production dependencies;
- confirm real page-text end-to-end acceptance remains pending until the user supplies the `.txt`;
- confirm no AI, fuzzy matching, or external service is called;
- confirm inputs are never overwritten and paired output rollback tests pass.

- [ ] **Step 5: Commit only test-proven fixes**

If real JSON or the full suite exposes a defect, add a failing regression first, fix it, rerun the focused and full suites, then commit:

```powershell
git add tools/reddit_json_export.py tools/reddit_page_text.py tools/reddit_json_text_merge.py tools/reconstruct_reddit_comments.py tests/test_reddit_json_export.py tests/test_reddit_page_text.py tests/test_reddit_json_text_merge.py tests/test_reconstruct_reddit_comments.py
git commit -m "fix: validate Reddit JSON text reconstruction"
```

If no code changes are required, do not create an empty commit.
