from __future__ import annotations

from tools.reddit_json_export import RedditJsonComment, RedditJsonExport
from tools.reddit_page_text import RedditPageText, normalize_author


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


def _retained_comments(
    export: RedditJsonExport,
    page: RedditPageText,
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


def reconstruct_json_text_rows(
    export: RedditJsonExport,
    page: RedditPageText,
) -> list[dict[str, str | int]]:
    if page.post_comment_count != export.post.num_comments:
        raise ValueError("page and JSON post comment counts differ")
    retained_comments = _retained_comments(export, page)
    if len(page.comments) != len(retained_comments):
        raise ValueError("page and JSON matched comment counts differ")

    rows: list[dict[str, str | int]] = []
    for comment, metric in zip(retained_comments, page.comments, strict=True):
        rows.append(
            {
                "Title": export.post.title,
                "Post Body": export.post.content,
                "Post Author": export.post.author,
                "Post Time": page.post_time,
                "Post Score": page.post_score,
                "Post Comment Count": len(retained_comments),
                "Author": comment.username,
                "Time": comment.date,
                "Score": "" if metric.score is None else metric.score,
                "Thread Level": comment.depth,
                "Is Reply": "No" if comment.depth == 0 else "Yes",
                "Comment": comment.content,
                "Comment ID": comment.id,
                "Parent ID": comment.parent_id,
            }
        )
    return rows
