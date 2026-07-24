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
_SIGNED_INTEGER_PATTERN = re.compile(
    r"(?:-(?:[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)|"
    r"0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)"
)
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MARKDOWN_HEADING = re.compile(r"(?m)^\s{0,3}#{1,6}\s*")
_WHITESPACE = re.compile(r"\s+")
_COMMENT_TIME_PATTERN = re.compile(r"\u2022?" + _TIME_PATTERN.pattern)
_COMMENT_OPERATION_LABELS = frozenset(
    (
        "\u8d5e\u540c",
        "\u8d5e\u540c\u6295\u7968",
        "\u53cd\u5bf9",
        "\u56de\u590d",
        "\u5956\u52b1",
        "\u5206\u4eab",
    )
)


def normalize_author(value: str) -> str:
    normalized = unicodedata.normalize("NFC", html.unescape(value)).strip()
    if normalized.startswith("u/"):
        normalized = normalized[2:]
    if normalized == "[已删除]":
        return "[deleted]"
    return normalized


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
    try:
        return int(value.replace(",", ""))
    except ValueError:
        return None


def _integer(value: str, *, signed: bool, label: str) -> int:
    pattern = _SIGNED_INTEGER_PATTERN if signed else _INTEGER_PATTERN
    if pattern.fullmatch(value) is None:
        raise RedditPageTextError(f"{label} invalid")
    try:
        return int(value.replace(",", ""))
    except ValueError:
        raise RedditPageTextError(f"{label} invalid") from None


def _operation_blocks(comment_lines: list[str]) -> list[list[str]]:
    blocks: list[list[str]] = []
    start = 0
    for index, line in enumerate(comment_lines):
        if line != "\u5206\u4eab":
            continue
        candidate = comment_lines[start : index + 1]
        start = index + 1
        _operation_prefix(candidate, len(blocks) + 1)
        blocks.append(candidate)
    trailing = [item for item in comment_lines[start:] if item]
    if trailing and not _is_promoted_trailing(trailing):
        raise RedditPageTextError("unparsed trailing page comment content")
    return blocks


def _is_promoted_trailing(lines: list[str]) -> bool:
    if len(lines) not in (3, 4):
        return False
    if not lines[0].startswith("u/") or not lines[0].endswith("\u5934\u50cf"):
        return False
    if "\u5df2\u63a8\u5e7f" not in lines[-1]:
        return False
    return not any(
        line in _COMMENT_OPERATION_LABELS
        or _COMMENT_TIME_PATTERN.fullmatch(line) is not None
        for line in lines
    )


def _operation_prefix(
    block: list[str],
    comment_number: int,
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    nonblank = [(index, line) for index, line in enumerate(block) if line]
    try:
        share = len(nonblank) - 1
        if nonblank[share][1] != "\u5206\u4eab":
            raise ValueError
        reply = max(
            index
            for index in range(share)
            if nonblank[index][1] == "\u56de\u590d"
        )
        downvote = max(
            index
            for index in range(reply)
            if nonblank[index][1] == "\u53cd\u5bf9"
        )
    except ValueError as error:
        raise RedditPageTextError(
            f"comment {comment_number} operation area is incomplete"
        ) from error
    return nonblank, nonblank[:downvote]


def _block_score(block: list[str], comment_number: int) -> int | None:
    _nonblank, prefix = _operation_prefix(block, comment_number)
    if prefix and prefix[-1][1] == "\u8d5e\u540c\u6295\u7968":
        return None
    if len(prefix) >= 2 and prefix[-2][1] == "\u8d5e\u540c":
        return _integer(
            prefix[-1][1],
            signed=True,
            label=f"comment {comment_number} score",
        )
    raise RedditPageTextError(
        f"comment {comment_number} vote display is unsupported"
    )


def _block_author_and_content(
    block: list[str],
    comment_number: int,
) -> tuple[str, str]:
    _nonblank, prefix = _operation_prefix(block, comment_number)
    if prefix and prefix[-1][1] == "\u8d5e\u540c\u6295\u7968":
        vote_index = prefix[-1][0]
    elif len(prefix) >= 2 and prefix[-2][1] == "\u8d5e\u540c":
        vote_index = prefix[-2][0]
    else:
        raise RedditPageTextError(
            f"comment {comment_number} vote display is unsupported"
        )
    time_indexes = [
        index
        for index, line in enumerate(block[:vote_index])
        if _COMMENT_TIME_PATTERN.fullmatch(line) is not None
    ]
    if len(time_indexes) != 1:
        raise RedditPageTextError(f"comment {comment_number} metadata is invalid")
    time_index = time_indexes[0]
    separator_indexes = [
        index for index, line in enumerate(block[:time_index]) if not line
    ]
    author_index = separator_indexes[-1] + 1 if separator_indexes else 0
    if author_index >= time_index or not block[author_index]:
        raise RedditPageTextError(f"comment {comment_number} metadata is invalid")
    if any(line in _COMMENT_OPERATION_LABELS for line in block[:author_index]):
        raise RedditPageTextError(
            f"comment {comment_number} operation area is incomplete"
        )
    return block[author_index], normalize_content(
        "\n".join(block[time_index + 1 : vote_index])
    )


def _comment_metrics(
    comment_lines: list[str],
    export: RedditJsonExport,
) -> tuple[PageCommentMetric, ...]:
    blocks = _operation_blocks(comment_lines)
    if len(blocks) != len(export.comments):
        raise RedditPageTextError("page comment block count does not match JSON comments")
    metrics: list[PageCommentMetric] = []
    for number, (block, expected) in enumerate(
        zip(blocks, export.comments, strict=True),
        start=1,
    ):
        actual_author, actual_content = _block_author_and_content(block, number)
        if normalize_author(actual_author) != normalize_author(expected.username):
            raise RedditPageTextError(f"comment {number} author does not match JSON")
        expected_content = normalize_content(expected.content)
        if not expected_content or actual_content != expected_content:
            raise RedditPageTextError(
                f"comment {number} content does not match JSON"
            )
        metrics.append(PageCommentMetric(_block_score(block, number)))
    return tuple(metrics)


def _parse_post_metrics(lines: list[str]) -> tuple[int, int]:
    if len(lines) < 4:
        raise RedditPageTextError("post metrics sequence invalid")
    labels_and_values = lines[-4:]
    if labels_and_values[0] != "赞同" or labels_and_values[2] != "反对":
        raise RedditPageTextError("post metrics sequence invalid")

    score = _parse_integer(labels_and_values[1])
    comment_count = _parse_integer(labels_and_values[3])
    if score is None or comment_count is None:
        raise RedditPageTextError("post metric value invalid")
    return score, comment_count


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

    comments = ()
    if require_comments:
        comments = _comment_metrics(lines[marker_index + 1 :], export)

    return RedditPageText(
        post_time=time_lines[0],
        post_score=score,
        post_comment_count=comment_count,
        comments=comments,
    )
