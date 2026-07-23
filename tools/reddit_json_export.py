from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class RedditJsonError(ValueError):
    """Raised when a Reddit JSON export fails structural or integrity checks."""


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


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RedditJsonError("invalid JSON: duplicate object key")
        result[key] = value
    return result


def _reject_nonstandard_constant(_constant: str) -> None:
    raise RedditJsonError("invalid JSON: non-standard numeric constant")


def _required(mapping: dict[str, Any], name: str, section: str) -> Any:
    if name not in mapping:
        raise RedditJsonError(f"{section} is missing required field {name}")
    return mapping[name]


def _object(value: Any, section: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RedditJsonError(f"{section} must be an object")
    return value


def _exact_int(
    value: Any, field: str, *, nonnegative: bool = False
) -> int:
    if type(value) is not int:
        raise RedditJsonError(f"{field} must be an integer")
    if nonnegative and value < 0:
        raise RedditJsonError(f"{field} must be nonnegative")
    return value


def _nonblank_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RedditJsonError(f"{field} must be nonblank text")
    return value


def _normalize_id(value: Any, field: str) -> str:
    if not isinstance(value, str):
        raise RedditJsonError(f"{field} must be an ASCII identifier")

    identifier = value
    if (
        len(identifier) >= 3
        and identifier[0] in ("t", "T")
        and identifier[1] in ("1", "3")
        and identifier[2] == "_"
    ):
        identifier = identifier[3:]

    if not identifier or not identifier.isascii() or not identifier.isalnum():
        raise RedditJsonError(f"{field} must be an ASCII alphanumeric identifier")
    return identifier.lower()


def _parse_meta(raw: dict[str, Any], comment_count: int) -> RedditMeta:
    completeness = _required(raw, "completeness", "meta")
    if completeness != "complete":
        raise RedditJsonError("meta.completeness must be complete")

    collected = _exact_int(
        _required(raw, "collectedCommentCount", "meta"),
        "meta.collectedCommentCount",
        nonnegative=True,
    )
    reported = _exact_int(
        _required(raw, "reportedByApi", "meta"),
        "meta.reportedByApi",
        nonnegative=True,
    )
    discrepancy = _exact_int(
        _required(raw, "discrepancy", "meta"),
        "meta.discrepancy",
        nonnegative=True,
    )
    failed_more = _exact_int(
        _required(raw, "failedMore", "meta"),
        "meta.failedMore",
        nonnegative=True,
    )

    if collected != comment_count:
        raise RedditJsonError("meta collected count does not match comments")
    if reported - collected != discrepancy:
        raise RedditJsonError("meta discrepancy is inconsistent")
    if failed_more != 0:
        raise RedditJsonError("meta.failedMore must be zero")

    accepted_empty = (None, "", [], {})
    for name in ("failedNodes", "failedReasons", "failedDetails"):
        value = _required(raw, name, "meta")
        if value not in accepted_empty:
            raise RedditJsonError(f"meta.{name} must be empty")

    return RedditMeta(collected, reported, discrepancy)


def _parse_post(raw: dict[str, Any], reported_by_api: int) -> RedditPost:
    post_id = _normalize_id(_required(raw, "id", "post"), "post.id")
    subreddit = _nonblank_text(
        _required(raw, "subreddit", "post"), "post.subreddit"
    )
    title = _nonblank_text(_required(raw, "title", "post"), "post.title")
    content = _nonblank_text(_required(raw, "content", "post"), "post.content")
    author = _nonblank_text(_required(raw, "author", "post"), "post.author")
    num_comments = _exact_int(
        _required(raw, "num_comments", "post"),
        "post.num_comments",
        nonnegative=True,
    )
    if num_comments != reported_by_api:
        raise RedditJsonError("post.num_comments does not match meta.reportedByApi")
    return RedditPost(
        id=post_id,
        subreddit=subreddit,
        title=title,
        content=content,
        author=author,
        num_comments=num_comments,
    )


def _parse_comment(raw: dict[str, Any], index: int) -> RedditJsonComment:
    section = f"comments[{index}]"
    return RedditJsonComment(
        id=_normalize_id(
            _required(raw, "id", section), f"{section}.id"
        ),
        parent_id=_normalize_id(
            _required(raw, "parent_id", section),
            f"{section}.parent_id",
        ),
        content=_nonblank_text(
            _required(raw, "content", section), f"{section}.content"
        ),
        depth=_exact_int(
            _required(raw, "depth", section),
            f"{section}.depth",
            nonnegative=True,
        ),
        username=_nonblank_text(
            _required(raw, "username", section), f"{section}.username"
        ),
        date=_nonblank_text(_required(raw, "date", section), f"{section}.date"),
        created_utc=_exact_int(
            _required(raw, "created_utc", section), f"{section}.created_utc"
        ),
    )


def _validate_graph(
    post_id: str, comments: tuple[RedditJsonComment, ...]
) -> None:
    by_id: dict[str, RedditJsonComment] = {}
    for item_number, comment in enumerate(comments, start=1):
        if comment.id in by_id:
            raise RedditJsonError(
                f"comment item {item_number} has a duplicate ID"
            )
        by_id[comment.id] = comment

    for item_number, comment in enumerate(comments, start=1):
        if comment.depth == 0:
            if comment.parent_id != post_id:
                raise RedditJsonError(
                    f"comment item {item_number} root parent does not match post"
                )
            continue

        parent = by_id.get(comment.parent_id)
        if parent is None:
            raise RedditJsonError(
                f"comment item {item_number} parent is missing"
            )
        if parent.depth != comment.depth - 1:
            raise RedditJsonError(
                f"comment item {item_number} parent depth is inconsistent"
            )


def parse_reddit_json(path: Path) -> RedditJsonExport:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError):
        raise RedditJsonError("unable to read valid UTF-8 JSON export") from None

    try:
        loaded = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_constant,
        )
    except RedditJsonError:
        raise
    except (ValueError, RecursionError):
        raise RedditJsonError("unable to read valid UTF-8 JSON export") from None

    root = _object(loaded, "root")
    meta_raw = _object(_required(root, "meta", "root"), "meta")
    post_raw = _object(_required(root, "post", "root"), "post")
    comments_raw = _required(root, "comments", "root")
    if not isinstance(comments_raw, list):
        raise RedditJsonError("comments must be an array")

    meta = _parse_meta(meta_raw, len(comments_raw))
    post = _parse_post(post_raw, meta.reported_by_api)
    comments = tuple(
        _parse_comment(_object(raw, f"comments[{index}]"), index)
        for index, raw in enumerate(comments_raw)
    )
    _validate_graph(post.id, comments)
    return RedditJsonExport(meta=meta, post=post, comments=comments)
