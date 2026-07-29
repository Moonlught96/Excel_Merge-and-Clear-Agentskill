from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from reddit_reconstruction.json_export import (
    RedditJsonComment,
    RedditJsonExport,
    RedditMeta,
    RedditPost,
)
from reddit_reconstruction.page_text import parse_reddit_page_metrics


class RedditPageTextTests(unittest.TestCase):
    def test_extracts_a_controlled_comment_metric_candidate(self) -> None:
        export = RedditJsonExport(
            RedditMeta(1, 1, 0),
            RedditPost("postone", "python", "Portable title", "", "poster", 1),
            (
                RedditJsonComment(
                    "commentone",
                    "postone",
                    "matched comment",
                    0,
                    "commenter",
                    "2026-07-28",
                    1,
                ),
            ),
        )
        page_text = "\n".join(
            (
                "Reddit",
                "r/python",
                "u/poster",
                "poster 头像",
                "8小时前",
                "Portable title",
                "正文",
                "赞同",
                "11",
                "反对",
                "1",
                "转到评论",
                "评论区域",
                "commenter",
                "•8小时前",
                "matched comment",
                "",
                "赞同",
                "7",
                "反对",
                "回复",
                "奖励",
                "分享",
            )
        )
        with tempfile.TemporaryDirectory() as temporary_directory:
            page_text_path = Path(temporary_directory) / "page.txt"
            page_text_path.write_text(page_text, encoding="utf-8")

            snapshot = parse_reddit_page_metrics(page_text_path, export)

        self.assertEqual(1, snapshot.operation_block_count)
        self.assertEqual(1, snapshot.parseable_block_count)
        self.assertEqual(1, len(snapshot.candidates))
        self.assertEqual(7, snapshot.candidates[0].score)
