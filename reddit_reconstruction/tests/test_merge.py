from __future__ import annotations

import unittest

from reddit_reconstruction.json_export import (
    RedditJsonComment,
    RedditJsonExport,
    RedditMeta,
    RedditPost,
)
from reddit_reconstruction.merge import (
    JSON_TEXT_OUTPUT_HEADERS,
    match_json_primary_page_scores,
    reconstruct_json_primary_page_rows,
)
from reddit_reconstruction.page_text import (
    PageMetricCandidate,
    RedditPageMetricSnapshot,
    normalize_content,
)


class RedditMergeTests(unittest.TestCase):
    def export(self) -> RedditJsonExport:
        return RedditJsonExport(
            RedditMeta(3, 3, 0),
            RedditPost("postone", "python", "Title", "", "poster", 3),
            (
                RedditJsonComment("rootone", "postone", "matched", 0, "a", "t1", 1),
                RedditJsonComment("childone", "rootone", "unmatched", 1, "b", "t2", 2),
                RedditJsonComment("grandone", "childone", "nested", 2, "c", "t3", 3),
            ),
        )

    def test_json_primary_keeps_unmatched_comment_score_blank(self) -> None:
        export = self.export()
        page = RedditPageMetricSnapshot(
            "8 hours ago",
            11,
            3,
            1,
            1,
            (PageMetricCandidate(normalize_content("matched"), 7),),
        )

        rows = reconstruct_json_primary_page_rows(
            export, page, match_json_primary_page_scores(export, page)
        )
        row_for_unmatched_comment = rows[2]

        self.assertEqual("", row_for_unmatched_comment[JSON_TEXT_OUTPUT_HEADERS[5]])

    def test_json_primary_preserves_comment_order_and_descendant_counts(self) -> None:
        export = self.export()
        page = RedditPageMetricSnapshot("8 hours ago", 11, 3, 0, 0, ())

        rows = reconstruct_json_primary_page_rows(
            export, page, match_json_primary_page_scores(export, page)
        )
        comment_rows = rows[1:]
        row_for_parent = comment_rows[0]
        expected_descendant_count = 2
        expected_comment_ids = ["rootone", "childone", "grandone"]

        self.assertEqual(
            expected_descendant_count, row_for_parent[JSON_TEXT_OUTPUT_HEADERS[6]]
        )
        self.assertEqual(
            expected_comment_ids,
            [row[JSON_TEXT_OUTPUT_HEADERS[9]] for row in comment_rows],
        )
