from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .json_export import RedditJsonComment, RedditJsonExport
from .page_text import (
    PageMetricCandidate,
    RedditPageMetricSnapshot,
    RedditPageText,
    normalize_author,
    normalize_content,
)


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


@dataclass(frozen=True)
class JsonPrimaryMetricMatch:
    scores_by_comment_id: dict[str, int]
    unique_score_mapping_count: int
    unmatched_json_comment_count: int
    ambiguous_body_match_count: int
    unavailable_page_score_count: int


def match_json_primary_page_scores(
    export: RedditJsonExport,
    page: RedditPageMetricSnapshot,
) -> JsonPrimaryMetricMatch:
    json_body_counts = Counter(
        normalize_content(comment.content) for comment in export.comments
    )
    candidates_by_body: dict[str, list[PageMetricCandidate]] = defaultdict(list)
    for candidate in page.candidates:
        candidates_by_body[candidate.normalized_content].append(candidate)

    scores_by_comment_id: dict[str, int] = {}
    unique_score_mapping_count = 0
    unmatched_json_comment_count = 0
    ambiguous_body_match_count = 0
    unavailable_page_score_count = 0
    for comment in export.comments:
        json_body = normalize_content(comment.content)
        page_candidates = candidates_by_body.get(json_body, ())
        if not json_body or not page_candidates:
            unmatched_json_comment_count += 1
        elif json_body_counts[json_body] != 1 or len(page_candidates) != 1:
            ambiguous_body_match_count += 1
        elif page_candidates[0].score is None:
            unavailable_page_score_count += 1
        else:
            scores_by_comment_id[comment.id] = page_candidates[0].score
            unique_score_mapping_count += 1

    if (
        unique_score_mapping_count
        + unmatched_json_comment_count
        + ambiguous_body_match_count
        + unavailable_page_score_count
        != len(export.comments)
    ):
        raise ValueError("JSON-primary score classification does not reconcile")
    return JsonPrimaryMetricMatch(
        scores_by_comment_id,
        unique_score_mapping_count,
        unmatched_json_comment_count,
        ambiguous_body_match_count,
        unavailable_page_score_count,
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
        visited_ids: set[str] = set()
        while parent_id in by_id:
            if parent_id in visited_ids:
                raise ValueError("retained comment ancestry is cyclic")
            visited_ids.add(parent_id)
            counts[parent_id] += 1
            parent_id = by_id[parent_id].parent_id
    return counts


def _post_row(
    export: RedditJsonExport,
    post_time: str,
    post_score: int,
    post_comment_count: int,
) -> dict[str, str | int]:
    return dict(
        zip(
            JSON_TEXT_OUTPUT_HEADERS,
            (
                "主帖",
                export.post.title,
                export.post.author,
                post_time,
                export.post.content,
                post_score,
                post_comment_count,
                0,
                "否",
                export.post.id,
                "",
            ),
            strict=True,
        )
    )


def _comment_row(
    comment: RedditJsonComment,
    score: str | int,
    descendant_count: int,
) -> dict[str, str | int]:
    return dict(
        zip(
            JSON_TEXT_OUTPUT_HEADERS,
            (
                "评论",
                "",
                comment.username,
                comment.date,
                comment.content,
                score,
                descendant_count,
                comment.depth,
                "否" if comment.depth == 0 else "是",
                comment.id,
                comment.parent_id,
            ),
            strict=True,
        )
    )


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
    rows = [_post_row(export, page.post_time, page.post_score, len(retained_comments))]
    for comment, metric in zip(retained_comments, page.comments, strict=True):
        score = "" if metric.score is None else metric.score
        rows.append(_comment_row(comment, score, descendant_counts[comment.id]))
    return rows


def reconstruct_json_primary_page_rows(
    export: RedditJsonExport,
    page: RedditPageMetricSnapshot,
    match: JsonPrimaryMetricMatch,
) -> list[dict[str, str | int]]:
    descendant_counts = _all_descendant_counts(export.comments)
    rows = [
        _post_row(
            export,
            page.post_time,
            page.post_score,
            page.post_comment_count,
        )
    ]
    for comment in export.comments:
        rows.append(
            _comment_row(
                comment,
                match.scores_by_comment_id.get(comment.id, ""),
                descendant_counts[comment.id],
            )
        )
    return rows
