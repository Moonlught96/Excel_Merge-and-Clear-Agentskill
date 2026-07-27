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
            meta=RedditMeta(2, 2, 0),
            post=RedditPost("p1", "desksetup", "Title", "Body", "poster", 2),
            comments=(
                RedditJsonComment("c1", "p1", "Root", 0, "alpha", "exact-time-1", 1),
                RedditJsonComment("c2", "c1", "Reply", 1, "beta", "exact-time-2", 2),
            ),
        )
        page = RedditPageText(
            "8 hours ago", 99, 2, (PageCommentMetric(4), PageCommentMetric(None))
        )
        return export, page

    def nested_fixture(self) -> tuple[RedditJsonExport, RedditPageText]:
        export = RedditJsonExport(
            meta=RedditMeta(4, 4, 0),
            post=RedditPost("p1", "desksetup", "Title", "Body", "poster", 4),
            comments=(
                RedditJsonComment("c1", "p1", "Root", 0, "alpha", "time-1", 1),
                RedditJsonComment("c2", "c1", "Child", 1, "beta", "time-2", 2),
                RedditJsonComment("c3", "c2", "Grandchild", 2, "gamma", "time-3", 3),
                RedditJsonComment("c4", "p1", "Second root", 0, "delta", "time-4", 4),
            ),
        )
        page = RedditPageText(
            "8 hours ago",
            99,
            4,
            (
                PageCommentMetric(4),
                PageCommentMetric(None),
                PageCommentMetric(7),
                PageCommentMetric(0),
            ),
        )
        return export, page

    def test_emits_post_first_then_comments_without_repeating_post_fields(
        self,
    ) -> None:
        export, page = self.fixture()

        rows = reconstruct_json_text_rows(export, page)

        self.assertEqual(
            (
                "记录类型", "标题", "作者", "时间", "内容", "点赞数",
                "评论/回复数", "层级", "是否回复", "评论ID", "父ID",
            ),
            JSON_TEXT_OUTPUT_HEADERS,
        )
        self.assertEqual(["主帖", "评论", "评论"], [row["记录类型"] for row in rows])
        self.assertEqual("Title", rows[0]["标题"])
        self.assertEqual("", rows[1]["标题"])
        self.assertEqual(2, rows[0]["评论/回复数"])
        self.assertEqual("p1", rows[0]["评论ID"])
        self.assertEqual("", rows[0]["父ID"])
        self.assertEqual(["c1", "c2"], [row["评论ID"] for row in rows[1:]])
        self.assertEqual([4, ""], [row["点赞数"] for row in rows[1:]])
        self.assertEqual(["否", "是"], [row["是否回复"] for row in rows[1:]])

    def test_counts_all_descendants_for_each_retained_comment(self) -> None:
        export, page = self.nested_fixture()

        rows = reconstruct_json_text_rows(export, page)

        comments = rows[1:]
        self.assertEqual([2, 1, 0, 0], [row["评论/回复数"] for row in comments])

    def test_emits_post_row_when_json_has_no_comments(self) -> None:
        export = RedditJsonExport(
            meta=RedditMeta(0, 0, 0),
            post=RedditPost("p1", "desksetup", "Title", "Body", "poster", 0),
            comments=(),
        )
        page = RedditPageText("8 hours ago", 99, 0, ())

        rows = reconstruct_json_text_rows(export, page)

        self.assertEqual(1, len(rows))
        self.assertEqual("主帖", rows[0]["记录类型"])
        self.assertEqual(0, rows[0]["评论/回复数"])

    def collapsed_automoderator_fixture(
        self,
    ) -> tuple[RedditJsonExport, RedditPageText]:
        export = RedditJsonExport(
            meta=RedditMeta(3, 3, 0),
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

    def test_omits_valid_collapsed_automoderator_from_retained_counts(
        self,
    ) -> None:
        export, page = self.collapsed_automoderator_fixture()

        rows = reconstruct_json_text_rows(export, page)

        self.assertEqual(["root", "reply"], [row["评论ID"] for row in rows[1:]])
        self.assertEqual(2, rows[0]["评论/回复数"])
        self.assertEqual(1, rows[1]["评论/回复数"])

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
            post=replace(export.post, content="=not-a-formula\nemoji 🥪"),
        )

        rows = reconstruct_json_text_rows(export, page)

        self.assertEqual("=not-a-formula\nemoji 🥪", rows[0]["内容"])

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

        self.assertEqual("是", rows[1]["是否回复"])
