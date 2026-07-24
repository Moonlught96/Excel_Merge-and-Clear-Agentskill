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
    for comment, metric in zip(export.comments, page.comments, strict=True):
        rows.append(
            {
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
            }
        )
    return rows
