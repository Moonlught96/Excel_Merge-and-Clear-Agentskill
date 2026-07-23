from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from tools.reddit_json_export import RedditJsonExport


class RedditPageTextError(ValueError):
    """Raised when copied Reddit page text fails structural checks."""


@dataclass(frozen=True)
class PageCommentMetric:
    score: int | None


@dataclass(frozen=True)
class RedditPageText:
    post_time: str
    post_score: int
    post_comment_count: int
    comments: tuple[PageCommentMetric, ...]


_TIME_PATTERN = re.compile(
    r"(?:刚刚|[0-9]+(?:分钟前|小时前|天前|周前|个月前|年前))"
)
_INTEGER_PATTERN = re.compile(r"(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)")


def normalize_author(value: str) -> str:
    normalized = unicodedata.normalize("NFC", html.unescape(value)).strip()
    if normalized.startswith("u/"):
        normalized = normalized[2:]
    if normalized == "[已删除]":
        return "[deleted]"
    return normalized


def _decode_page(path: Path) -> str:
    try:
        content = path.read_bytes()
    except OSError:
        raise RedditPageTextError("page text read failed") from None

    if content.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        raise RedditPageTextError("page text encoding unsupported")

    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return content.decode("utf-16")
        except UnicodeError:
            raise RedditPageTextError("page text encoding unsupported") from None

    try:
        return content.decode("utf-8-sig")
    except UnicodeError:
        try:
            return content.decode("gb18030")
        except UnicodeError:
            raise RedditPageTextError("page text encoding unsupported") from None


def _unique_index(lines: list[str], value: str, category: str) -> int:
    indexes = [index for index, line in enumerate(lines) if line == value]
    if len(indexes) != 1:
        raise RedditPageTextError(category)
    return indexes[0]


def _parse_integer(value: str) -> int | None:
    if _INTEGER_PATTERN.fullmatch(value) is None:
        return None
    return int(value.replace(",", ""))


def _parse_post_metrics(lines: list[str]) -> tuple[int, int]:
    matches: list[tuple[int, int]] = []
    for index in range(len(lines) - 3):
        if lines[index] != "赞同" or lines[index + 2] != "反对":
            continue
        score = _parse_integer(lines[index + 1])
        comment_count = _parse_integer(lines[index + 3])
        if score is not None and comment_count is not None:
            matches.append((score, comment_count))

    if len(matches) != 1:
        raise RedditPageTextError("post metrics invalid or ambiguous")
    return matches[0]


def parse_reddit_page_text(
    path: Path,
    export: RedditJsonExport,
    *,
    require_comments: bool = True,
) -> RedditPageText:
    text = _decode_page(path).replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n")]

    marker_index = _unique_index(lines, "评论区域", "comment area marker invalid")
    post_lines = lines[:marker_index]

    subreddit_index = _unique_index(
        post_lines,
        f"r/{export.post.subreddit}",
        "post subreddit marker invalid",
    )
    title_index = _unique_index(
        post_lines,
        export.post.title,
        "post title marker invalid",
    )
    if subreddit_index >= title_index:
        raise RedditPageTextError("post anchor order invalid")

    identity_lines = post_lines[subreddit_index + 1 : title_index]
    expected_author = normalize_author(export.post.author)
    matching_authors = [
        line
        for line in identity_lines
        if not line.endswith("头像") and normalize_author(line) == expected_author
    ]
    if len(matching_authors) != 1:
        raise RedditPageTextError("post author invalid or ambiguous")

    time_lines = [
        line for line in identity_lines if _TIME_PATTERN.fullmatch(line) is not None
    ]
    if len(time_lines) != 1:
        raise RedditPageTextError("post time invalid or ambiguous")

    go_to_comments_index = _unique_index(
        post_lines, "转到评论", "go to comments marker invalid"
    )
    if go_to_comments_index <= title_index:
        raise RedditPageTextError("post metric anchor order invalid")

    metric_lines = [
        line
        for line in post_lines[title_index + 1 : go_to_comments_index]
        if line
    ]
    score, comment_count = _parse_post_metrics(metric_lines)
    if comment_count != export.post.num_comments:
        raise RedditPageTextError("post comment count mismatch")

    if require_comments:
        raise RedditPageTextError("comment parsing not implemented")

    return RedditPageText(
        post_time=time_lines[0],
        post_score=score,
        post_comment_count=comment_count,
        comments=(),
    )
