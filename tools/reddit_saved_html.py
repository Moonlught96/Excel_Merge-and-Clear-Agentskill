"""Deterministically extract registered attributes from saved Reddit HTML."""

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


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


def _attribute_values(
    attributes: list[tuple[str, str | None]],
    name: str,
) -> list[str]:
    registered_name = name.casefold()
    return [
        value or ""
        for attribute_name, value in attributes
        if attribute_name.casefold() == registered_name
    ]


def _first_attribute(
    attributes: list[tuple[str, str | None]],
    name: str,
) -> str:
    values = _attribute_values(attributes, name)
    return values[0] if values else ""


def _first_nonempty_registered_attribute(
    attributes: list[tuple[str, str | None]],
    names: tuple[str, ...],
) -> str:
    for name in names:
        for value in _attribute_values(attributes, name):
            if value.strip():
                return value
    return ""


def _normalize_id(value: str, prefixes: tuple[str, ...], label: str) -> str:
    normalized = value.lower()
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    if not normalized or not normalized.isascii() or not normalized.isalnum():
        raise ValueError(f"invalid {label} ID: {value!r}")
    return normalized


def _parse_depth(value: str) -> int | None:
    if value and value.isascii() and value.isdigit():
        return int(value)
    return None


class _SavedRedditHtmlParser(HTMLParser):
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
        normalized_tag = tag.casefold()
        if normalized_tag == "shreddit-post":
            self._parse_post(attrs)
        elif normalized_tag == "shreddit-comment":
            self._parse_comment(attrs)

    def _parse_post(self, attrs: list[tuple[str, str | None]]) -> None:
        raw_post_id = _first_attribute(attrs, "thingid")
        if not raw_post_id:
            return
        post_id = _normalize_id(raw_post_id, ("t3_",), "post")
        if self.post_id and post_id != self.post_id:
            raise ValueError(
                f"multiple different post IDs: {self.post_id!r} and {post_id!r}"
            )
        if self.post_id:
            return

        self.post_id = post_id
        self.post_author = _first_attribute(attrs, "author")
        self.post_score = _first_nonempty_registered_attribute(
            attrs, ("score", "data-score")
        )
        self.post_comment_count = _first_nonempty_registered_attribute(
            attrs, ("comment-count", "commentcount")
        )

    def _parse_comment(self, attrs: list[tuple[str, str | None]]) -> None:
        raw_comment_id = _first_attribute(attrs, "thingid")
        if not raw_comment_id:
            return
        comment_id = _normalize_id(raw_comment_id, ("t1_",), "comment")
        if comment_id in self.comments:
            raise ValueError(f"duplicate comment ID: {comment_id}")

        raw_parent_id = _first_attribute(attrs, "parentid")
        parent_id = (
            _normalize_id(raw_parent_id, ("t1_", "t3_"), "parent")
            if raw_parent_id
            else ""
        )
        self.comments[comment_id] = HtmlComment(
            comment_id=comment_id,
            parent_id=parent_id,
            thread_level=_parse_depth(_first_attribute(attrs, "depth")),
            score=_first_nonempty_registered_attribute(
                attrs, ("score", "data-score")
            ),
        )

    def result(self) -> SavedRedditHtml:
        if not self.post_id:
            raise ValueError("missing registered post ID")
        return SavedRedditHtml(
            post_id=self.post_id,
            post_author=self.post_author,
            post_score=self.post_score,
            post_comment_count=self.post_comment_count,
            comments=self.comments,
        )


def parse_saved_reddit_html(path: Path) -> SavedRedditHtml:
    parser = _SavedRedditHtmlParser()
    parser.feed(path.read_text(encoding="utf-8-sig"))
    parser.close()
    return parser.result()
