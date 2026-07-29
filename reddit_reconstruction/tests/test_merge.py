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

    def test_json_primary_marks_duplicate_json_bodies_ambiguous_with_one_page_candidate(
        self,
    ) -> None:
        export = RedditJsonExport(
            RedditMeta(2, 2, 0),
            RedditPost("postone", "python", "Title", "", "poster", 2),
            (
                RedditJsonComment("firstdup", "postone", "duplicate", 0, "a", "t1", 1),
                RedditJsonComment("seconddup", "postone", "duplicate", 0, "b", "t2", 2),
            ),
        )
        page = RedditPageMetricSnapshot(
            "8 hours ago",
            11,
            2,
            1,
            1,
            (PageMetricCandidate(normalize_content("duplicate"), 7),),
        )

        match = match_json_primary_page_scores(export, page)
        rows = reconstruct_json_primary_page_rows(export, page, match)

        self.assertEqual({}, match.scores_by_comment_id)
        self.assertEqual(0, match.unique_score_mapping_count)
        self.assertEqual(2, match.ambiguous_body_match_count)
        self.assertEqual(0, match.unmatched_json_comment_count)
        self.assertEqual(0, match.unavailable_page_score_count)
        self.assertEqual(
            ["", ""],
            [row[JSON_TEXT_OUTPUT_HEADERS[5]] for row in rows[1:]],
        )

    def test_json_primary_marks_duplicate_page_bodies_ambiguous_with_one_json_comment(
        self,
    ) -> None:
        export = RedditJsonExport(
            RedditMeta(1, 1, 0),
            RedditPost("postone", "python", "Title", "", "poster", 1),
            (
                RedditJsonComment("single", "postone", "duplicate", 0, "a", "t1", 1),
            ),
        )
        page = RedditPageMetricSnapshot(
            "8 hours ago",
            11,
            1,
            2,
            2,
            (
                PageMetricCandidate(normalize_content("duplicate"), 7),
                PageMetricCandidate(normalize_content("duplicate"), 8),
            ),
        )

        match = match_json_primary_page_scores(export, page)
        rows = reconstruct_json_primary_page_rows(export, page, match)

        self.assertEqual({}, match.scores_by_comment_id)
        self.assertEqual(0, match.unique_score_mapping_count)
        self.assertEqual(1, match.ambiguous_body_match_count)
        self.assertEqual(0, match.unmatched_json_comment_count)
        self.assertEqual(0, match.unavailable_page_score_count)
        self.assertEqual("", rows[1][JSON_TEXT_OUTPUT_HEADERS[5]])

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
        self.assertEqual("8 hours ago", rows[0][JSON_TEXT_OUTPUT_HEADERS[3]])
        self.assertEqual(11, rows[0][JSON_TEXT_OUTPUT_HEADERS[5]])
        self.assertEqual(3, rows[0][JSON_TEXT_OUTPUT_HEADERS[6]])
        self.assertEqual("Title", rows[0][JSON_TEXT_OUTPUT_HEADERS[1]])
        self.assertEqual("postone", rows[0][JSON_TEXT_OUTPUT_HEADERS[9]])
