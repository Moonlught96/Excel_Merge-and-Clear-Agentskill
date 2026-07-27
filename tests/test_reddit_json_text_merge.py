from __future__ import annotations

import unittest
from dataclasses import replace

from tools.reddit_json_export import (
    RedditJsonComment,
    RedditJsonExport,
    RedditMeta,
    RedditPost,
)
from tools.reddit_json_text_merge import (
    JSON_TEXT_OUTPUT_HEADERS,
    reconstruct_json_text_rows,
)
from tools.reddit_page_text import PageCommentMetric, RedditPageText


class RedditJsonTextMergeTests(unittest.TestCase):
    def fixture(self) -> tuple[RedditJsonExport, RedditPageText]:
        export = RedditJsonExport(
            meta=RedditMeta(2, 3, 1),
            post=RedditPost("p1", "desksetup", "Title", "Body", "poster", 3),
            comments=(
                RedditJsonComment("c1", "p1", "Root", 0, "alpha", "exact-time-1", 1),
                RedditJsonComment("c2", "c1", "Reply", 1, "beta", "exact-time-2", 2),
            ),
        )
        page = RedditPageText(
            "8 hours ago", 99, 3, (PageCommentMetric(4), PageCommentMetric(None))
        )
        return export, page

    def test_builds_fixed_rows_in_json_order(self) -> None:
        export, page = self.fixture()

        rows = reconstruct_json_text_rows(export, page)

        self.assertEqual(14, len(JSON_TEXT_OUTPUT_HEADERS))
        self.assertEqual(
            (
                "Title", "Post Body", "Post Author", "Post Time",
                "Post Score", "Post Comment Count", "Author", "Time",
                "Score", "Thread Level", "Is Reply", "Comment",
                "Comment ID", "Parent ID",
            ),
            JSON_TEXT_OUTPUT_HEADERS,
        )
        self.assertEqual(["c1", "c2"], [row["Comment ID"] for row in rows])
        self.assertEqual(["No", "Yes"], [row["Is Reply"] for row in rows])
        self.assertEqual([4, ""], [row["Score"] for row in rows])
        self.assertEqual([2, 2], [row["Post Comment Count"] for row in rows])
        self.assertTrue(all(row["Post Score"] == 99 for row in rows))

    def collapsed_automoderator_fixture(
        self,
    ) -> tuple[RedditJsonExport, RedditPageText]:
        export = RedditJsonExport(
            meta=RedditMeta(3, 3, 1),
            post=RedditPost("p1", "desksetup", "Title", "Body", "poster", 3),
            comments=(
                RedditJsonComment(
                    "automod", "p1", "notice", 0, "AutoModerator", "time-0", 0
                ),
                RedditJsonComment("root", "p1", "Root", 0, "alpha", "time-1", 1),
                RedditJsonComment("reply", "root", "Reply", 1, "beta", "time-2", 2),
            ),
        )
        page = RedditPageText(
            "8 hours ago",
            99,
            3,
            (PageCommentMetric(4), PageCommentMetric(None)),
            ("automod",),
        )
        return export, page

    def test_omits_valid_collapsed_automoderator_and_counts_retained_comments(
        self,
    ) -> None:
        export, page = self.collapsed_automoderator_fixture()

        rows = reconstruct_json_text_rows(export, page)

        self.assertEqual(["root", "reply"], [row["Comment ID"] for row in rows])
        self.assertEqual([2, 2], [row["Post Comment Count"] for row in rows])

    def test_rejects_unknown_collapsed_automoderator_exclusion(self) -> None:
        export, page = self.collapsed_automoderator_fixture()
        page = replace(page, excluded_comment_ids=("unknown",))

        with self.assertRaisesRegex(ValueError, "collapsed AutoModerator exclusion"):
            reconstruct_json_text_rows(export, page)

    def test_rejects_duplicated_collapsed_automoderator_exclusion(self) -> None:
        export, page = self.collapsed_automoderator_fixture()
        page = replace(page, excluded_comment_ids=("automod", "automod"))

        with self.assertRaisesRegex(ValueError, "collapsed AutoModerator exclusion"):
            reconstruct_json_text_rows(export, page)

    def test_rejects_nonfirst_collapsed_automoderator_exclusion(self) -> None:
        export, page = self.collapsed_automoderator_fixture()
        page = replace(page, excluded_comment_ids=("root",))

        with self.assertRaisesRegex(ValueError, "collapsed AutoModerator exclusion"):
            reconstruct_json_text_rows(export, page)

    def test_rejects_child_owning_collapsed_automoderator_exclusion(self) -> None:
        export, page = self.collapsed_automoderator_fixture()
        export = replace(
            export,
            comments=(
                export.comments[0],
                replace(export.comments[1], parent_id="automod"),
                export.comments[2],
            ),
        )

        with self.assertRaisesRegex(ValueError, "collapsed AutoModerator exclusion"):
            reconstruct_json_text_rows(export, page)

    def test_preserves_json_text_and_rejects_count_mismatches(self) -> None:
        export, page = self.fixture()
        export = replace(
            export,
            post=replace(export.post, content="=not-a-formula\nemoji 馃"),
        )

        rows = reconstruct_json_text_rows(export, page)

        self.assertEqual("=not-a-formula\nemoji 馃", rows[0]["Post Body"])

        wrong_page = RedditPageText(
            page.post_time,
            page.post_score,
            page.post_comment_count + 1,
            page.comments,
        )
        with self.assertRaisesRegex(ValueError, "post comment counts"):
            reconstruct_json_text_rows(export, wrong_page)

    def test_rejects_comment_metric_count_mismatch(self) -> None:
        export, page = self.fixture()
        short_page = RedditPageText(
            page.post_time,
            page.post_score,
            page.post_comment_count,
            page.comments[:1],
        )

        with self.assertRaisesRegex(ValueError, "matched comment counts"):
            reconstruct_json_text_rows(export, short_page)

    def test_reply_flag_is_no_only_for_exact_zero(self) -> None:
        export, page = self.fixture()
        synthetic = replace(
            export,
            comments=(
                replace(export.comments[0], depth=-1),
                export.comments[1],
            ),
        )

        rows = reconstruct_json_text_rows(synthetic, page)

        self.assertEqual("Yes", rows[0]["Is Reply"])
