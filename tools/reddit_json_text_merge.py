from __future__ import annotations

from tools.reddit_json_export import RedditJsonComment, RedditJsonExport
from tools.reddit_page_text import RedditPageText, normalize_author


JSON_TEXT_OUTPUT_HEADERS = (
    "记录类型",
    "标题",
    "作者",
    "时间",
    "内容",
    "点赞数",
    "评论/回复数",
    "层级",
    "是否回复",
    "评论ID",
    "父ID",
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


def _all_descendant_counts(
    comments: tuple[RedditJsonComment, ...],
) -> dict[str, int]:
    by_id = {comment.id: comment for comment in comments}
    counts = {comment.id: 0 for comment in comments}
    for descendant in comments:
        parent_id = descendant.parent_id
        while parent_id in by_id:
            counts[parent_id] += 1
            parent_id = by_id[parent_id].parent_id
    return counts


def reconstruct_json_text_rows(
    export: RedditJsonExport,
    page: RedditPageText,
) -> list[dict[str, str | int]]:
    if page.post_comment_count != export.post.num_comments:
        raise ValueError("page and JSON post comment counts differ")
    retained_comments = _retained_comments(export, page)
    if len(page.comments) != len(retained_comments):
        raise ValueError("page and JSON matched comment counts differ")

    descendant_counts = _all_descendant_counts(retained_comments)
    rows: list[dict[str, str | int]] = [
        {
            "记录类型": "主帖",
            "标题": export.post.title,
            "作者": export.post.author,
            "时间": page.post_time,
            "内容": export.post.content,
            "点赞数": page.post_score,
            "评论/回复数": len(retained_comments),
            "层级": 0,
            "是否回复": "否",
            "评论ID": export.post.id,
            "父ID": "",
        }
    ]
    for comment, metric in zip(retained_comments, page.comments, strict=True):
        rows.append(
            {
                "记录类型": "评论",
                "标题": "",
                "作者": comment.username,
                "时间": comment.date,
                "内容": comment.content,
                "点赞数": "" if metric.score is None else metric.score,
                "评论/回复数": descendant_counts[comment.id],
                "层级": comment.depth,
                "是否回复": "否" if comment.depth == 0 else "是",
                "评论ID": comment.id,
                "父ID": comment.parent_id,
            }
        )
    return rows
