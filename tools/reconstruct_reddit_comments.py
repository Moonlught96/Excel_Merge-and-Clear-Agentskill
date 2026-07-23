"""Reconstruct Reddit comment rows using exact Comment ID matches."""

from __future__ import annotations

import csv
import sys
from contextlib import ExitStack
from pathlib import Path

from openpyxl import Workbook

try:
    from tools.output_path_safety import atomic_output_path, ensure_output_paths_safe
    from tools.reddit_free_csv import FreeRedditExport
    from tools.reddit_saved_html import SavedRedditHtml
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from tools.output_path_safety import atomic_output_path, ensure_output_paths_safe
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


def _write_xlsx(rows: list[dict[str, str | int]], output_path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Reddit Comments"
    for column_number, header in enumerate(OUTPUT_HEADERS, start=1):
        cell = sheet.cell(1, column_number, header)
        cell.data_type = "s"
    for row_number, row in enumerate(rows, start=2):
        for column_number, header in enumerate(OUTPUT_HEADERS, start=1):
            value = row[header]
            cell = sheet.cell(row_number, column_number, value)
            if isinstance(value, str):
                cell.data_type = "s"
    workbook.save(output_path)


def _write_csv(rows: list[dict[str, str | int]], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_HEADERS)
        writer.writeheader()
        writer.writerows(rows)


def write_outputs(
    rows: list[dict[str, str | int]],
    *,
    input_paths: tuple[Path, Path],
    output_xlsx: Path,
    output_csv: Path,
    overwrite: bool,
) -> None:
    resolved_xlsx, resolved_csv = ensure_output_paths_safe(
        input_paths,
        (output_xlsx, output_csv),
        overwrite=overwrite,
    )
    with ExitStack() as stack:
        staged_xlsx = stack.enter_context(atomic_output_path(resolved_xlsx))
        staged_csv = stack.enter_context(atomic_output_path(resolved_csv))
        _write_xlsx(rows, staged_xlsx)
        _write_csv(rows, staged_csv)


def _required_post_value(
    html_value: str,
    fallback: str | None,
    field_name: str,
    cli_name: str,
) -> str:
    if html_value.strip():
        return html_value
    if fallback is not None and fallback.strip():
        return fallback
    raise ValueError(
        f"Missing required post field {field_name}; explicit CLI value "
        f"{cli_name} is needed"
    )


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
                "Is Reply": "No" if thread_level == 0 else "Yes",
                "Comment": comment.comment,
                "Comment URL": comment.comment_url,
                "Comment ID": comment.comment_id,
                "Parent ID": html_comment.parent_id,
            }
        )
    return rows
