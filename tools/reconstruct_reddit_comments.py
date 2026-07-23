"""Reconstruct Reddit comment rows using exact Comment ID matches."""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from tools.reddit_free_csv import FreeRedditExport
    from tools.reddit_saved_html import SavedRedditHtml
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.reddit_free_csv import FreeRedditExport
    from tools.reddit_saved_html import SavedRedditHtml


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
    fallback: str | None,
    field_name: str,
    cli_name: str,
) -> str:
    value = html_value if html_value != "" else fallback
    if value is None or value == "":
        raise ValueError(
            f"Missing required post field {field_name}; explicit CLI value "
            f"{cli_name} is needed"
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
            f"Reddit post ID mismatch: free CSV {free.post_id!r}, "
            f"saved HTML {html.post_id!r}"
        )

    resolved_post_author = _required_post_value(
        html.post_author, post_author, "Post Author", "post_author"
    )
    resolved_post_score = _required_post_value(
        html.post_score, post_score, "Post Score", "post_score"
    )
    resolved_post_comment_count = _required_post_value(
        html.post_comment_count,
        post_comment_count,
        "Post Comment Count",
        "post_comment_count",
    )

    missing_ids: list[str] = []
    invalid_hierarchy_ids: list[str] = []
    for comment in free.comments:
        html_comment = html.comments.get(comment.comment_id)
        if html_comment is None:
            missing_ids.append(comment.comment_id)
        elif html_comment.parent_id == "" or html_comment.thread_level is None:
            invalid_hierarchy_ids.append(comment.comment_id)

    if missing_ids or invalid_hierarchy_ids:
        categories: list[str] = []
        if missing_ids:
            categories.append("Missing HTML comments: " + ", ".join(missing_ids))
        if invalid_hierarchy_ids:
            categories.append(
                "Invalid hierarchy: " + ", ".join(invalid_hierarchy_ids)
            )
        raise ValueError("; ".join(categories))

    rows: list[dict[str, str | int]] = []
    for comment in free.comments:
        html_comment = html.comments[comment.comment_id]
        thread_level = html_comment.thread_level
        assert thread_level is not None
        rows.append(
            {
                "Title": free.title,
                "Post Body": free.body,
                "Post URL": free.url,
                "Post Author": resolved_post_author,
                "Post Score": resolved_post_score,
                "Post Comment Count": resolved_post_comment_count,
                "Author": comment.author,
                "Time": comment.time,
                "Score": html_comment.score,
                "Thread Level": thread_level,
                "Is Reply": "Yes" if thread_level > 0 else "No",
                "Comment": comment.comment,
                "Comment URL": comment.comment_url,
                "Comment ID": comment.comment_id,
                "Parent ID": html_comment.parent_id,
            }
        )
    return rows
