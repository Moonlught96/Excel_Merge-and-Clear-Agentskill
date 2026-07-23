from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from tools.csv_excel_compat import read_csv_rows


COMMENT_HEADERS = ("author_name", "date_time", "comment", "comment_url")
METADATA_KEYS = ("title", "body", "url")
POST_ID_PATTERN = re.compile(r"/comments/([^/]+)/", re.IGNORECASE)
COMMENT_ID_PATTERN = re.compile(r"/comment/([^/]+)/?$", re.IGNORECASE)


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


def _find_comment_header(rows: list[list[str]]) -> tuple[int, list[str]]:
    required_headers = set(COMMENT_HEADERS)
    for row_index, row in enumerate(rows):
        if required_headers.issubset(row):
            return row_index, row
    raise ValueError(
        "Missing required comment header(s): " + ", ".join(COMMENT_HEADERS)
    )


def _collect_metadata(rows: list[list[str]]) -> dict[str, str]:
    values: dict[str, list[str]] = {key: [] for key in METADATA_KEYS}
    for row in rows:
        if not row or not any(row):
            continue
        key = row[0]
        if key in values:
            values[key].append(row[1] if len(row) > 1 else "")

    metadata: dict[str, str] = {}
    for key in METADATA_KEYS:
        occurrences = values[key]
        if not occurrences:
            raise ValueError(f"Missing metadata key: {key}")
        if len(occurrences) > 1:
            raise ValueError(f"Duplicate metadata key: {key}")
        metadata[key] = occurrences[0]
    return metadata


def _extract_post_id(url: str) -> str:
    match = POST_ID_PATTERN.search(urlsplit(url).path)
    if match is None:
        raise ValueError(f"Invalid Reddit post URL; could not extract post ID: {url}")
    return match.group(1)


def _extract_comment_id(url: str) -> str:
    match = COMMENT_ID_PATTERN.search(urlsplit(url).path)
    if match is None:
        raise ValueError(f"Invalid or missing Reddit comment URL: {url}")
    return match.group(1).lower()


def _cell(row: list[str], index: int) -> str:
    return row[index] if index < len(row) else ""


def parse_free_reddit_csv(path: Path) -> FreeRedditExport:
    rows = read_csv_rows(path).rows
    header_index, header = _find_comment_header(rows)
    metadata = _collect_metadata(rows[:header_index])
    header_indexes = {name: header.index(name) for name in COMMENT_HEADERS}

    comments: list[FreeComment] = []
    seen_comment_ids: set[str] = set()
    for row in rows[header_index + 1 :]:
        if not row or not any(row):
            continue
        comment_url = _cell(row, header_indexes["comment_url"])
        comment_id = _extract_comment_id(comment_url)
        if comment_id in seen_comment_ids:
            raise ValueError(f"Duplicate Comment ID: {comment_id}")
        seen_comment_ids.add(comment_id)
        comments.append(
            FreeComment(
                author=_cell(row, header_indexes["author_name"]),
                time=_cell(row, header_indexes["date_time"]),
                comment=_cell(row, header_indexes["comment"]),
                comment_url=comment_url,
                comment_id=comment_id,
            )
        )

    return FreeRedditExport(
        title=metadata["title"],
        body=metadata["body"],
        url=metadata["url"],
        post_id=_extract_post_id(metadata["url"]),
        comments=tuple(comments),
    )
