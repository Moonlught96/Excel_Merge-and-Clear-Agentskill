from pathlib import Path
import subprocess
import sys
import unittest

from tools.reddit_free_csv import FreeComment, FreeRedditExport
from tools.reddit_saved_html import HtmlComment, SavedRedditHtml
from tools.reconstruct_reddit_comments import OUTPUT_HEADERS, reconstruct_rows


class ReconstructRedditRowsTests(unittest.TestCase):
    def test_module_imports_from_direct_script_directory_context(self) -> None:
        tools_directory = Path(__file__).resolve().parents[1] / "tools"

        completed = subprocess.run(
            [sys.executable, "-c", "import reconstruct_reddit_comments"],
            cwd=tools_directory,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(0, completed.returncode, completed.stderr)

    def free(self, *comments: FreeComment, post_id: str = "post1") -> FreeRedditExport:
        return FreeRedditExport(
            title="Exact title",
            body="Exact body",
            url="https://www.reddit.com/r/test/comments/post1/example/",
            post_id=post_id,
            comments=comments,
        )

    def comment(
        self,
        comment_id: str,
        *,
        author: str = "free-author",
        time: str = "free-time",
        text: str = "free-comment",
        url: str | None = None,
    ) -> FreeComment:
        return FreeComment(
            author=author,
            time=time,
            comment=text,
            comment_url=url or f"https://reddit.com/comment/{comment_id}/",
            comment_id=comment_id,
        )

    def html(
        self,
        *comments: HtmlComment,
        post_id: str = "post1",
        post_author: str = "html-author",
        post_score: str = "42",
        post_comment_count: str = "2",
    ) -> SavedRedditHtml:
        return SavedRedditHtml(
            post_id=post_id,
            post_author=post_author,
            post_score=post_score,
            post_comment_count=post_comment_count,
            comments={comment.comment_id: comment for comment in comments},
        )

    def html_comment(
        self,
        comment_id: str,
        *,
        parent_id: str = "post1",
        level: int | None = 0,
        score: str = "7",
    ) -> HtmlComment:
        return HtmlComment(
            comment_id=comment_id,
            parent_id=parent_id,
            thread_level=level,
            score=score,
        )

    def test_output_headers_have_exact_order_and_rows_have_no_extra_fields(self) -> None:
        expected = (
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
        rows = reconstruct_rows(
            self.free(self.comment("c1")),
            self.html(self.html_comment("c1")),
        )

        self.assertEqual(expected, OUTPUT_HEADERS)
        self.assertEqual(15, len(OUTPUT_HEADERS))
        self.assertEqual(list(expected), list(rows[0]))

    def test_preserves_source_order_and_marks_root_and_replies(self) -> None:
        free = self.free(self.comment("second"), self.comment("first"))
        html = self.html(
            self.html_comment("first", level=2, parent_id="parent"),
            self.html_comment("second", level=0),
        )

        rows = reconstruct_rows(free, html)

        self.assertEqual(["second", "first"], [row["Comment ID"] for row in rows])
        self.assertEqual(["No", "Yes"], [row["Is Reply"] for row in rows])
        self.assertEqual([0, 2], [row["Thread Level"] for row in rows])

    def test_blank_comment_score_is_allowed_and_preserved(self) -> None:
        rows = reconstruct_rows(
            self.free(self.comment("c1")),
            self.html(self.html_comment("c1", score="")),
        )

        self.assertEqual("", rows[0]["Score"])

    def test_nonempty_html_post_values_including_zero_override_fallbacks(self) -> None:
        rows = reconstruct_rows(
            self.free(self.comment("c1")),
            self.html(
                self.html_comment("c1"),
                post_author="html",
                post_score="0",
                post_comment_count="0",
            ),
            post_author="wrong",
            post_score="wrong",
            post_comment_count="wrong",
        )

        self.assertEqual("html", rows[0]["Post Author"])
        self.assertEqual("0", rows[0]["Post Score"])
        self.assertEqual("0", rows[0]["Post Comment Count"])

    def test_explicit_post_values_are_fallbacks_for_empty_html_values(self) -> None:
        rows = reconstruct_rows(
            self.free(self.comment("c1")),
            self.html(
                self.html_comment("c1"),
                post_author="",
                post_score="",
                post_comment_count="",
            ),
            post_author="fallback-author",
            post_score="fallback-score",
            post_comment_count="fallback-count",
        )

        self.assertEqual("fallback-author", rows[0]["Post Author"])
        self.assertEqual("fallback-score", rows[0]["Post Score"])
        self.assertEqual("fallback-count", rows[0]["Post Comment Count"])

    def test_each_missing_required_post_field_names_needed_cli_value(self) -> None:
        cases = (
            ("Post Author", "post_author", {"post_author": ""}),
            ("Post Score", "post_score", {"post_score": ""}),
            (
                "Post Comment Count",
                "post_comment_count",
                {"post_comment_count": ""},
            ),
        )
        for field_name, cli_name, html_override in cases:
            with self.subTest(field_name=field_name):
                html_values = {
                    "post_author": "author",
                    "post_score": "score",
                    "post_comment_count": "count",
                }
                html_values.update(html_override)
                with self.assertRaisesRegex(
                    ValueError, rf"{field_name}.*{cli_name}"
                ):
                    reconstruct_rows(
                        self.free(self.comment("c1")),
                        self.html(self.html_comment("c1"), **html_values),
                    )

    def test_post_id_mismatch_names_both_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, r"free-id.*html-id"):
            reconstruct_rows(
                self.free(self.comment("c1"), post_id="free-id"),
                self.html(self.html_comment("c1"), post_id="html-id"),
            )

    def test_one_missing_html_comment_is_reported(self) -> None:
        with self.assertRaisesRegex(ValueError, r"Missing HTML comments.*absent"):
            reconstruct_rows(self.free(self.comment("absent")), self.html())

    def test_all_missing_html_comment_ids_are_reported(self) -> None:
        with self.assertRaises(ValueError) as caught:
            reconstruct_rows(
                self.free(self.comment("missing1"), self.comment("missing2")),
                self.html(),
            )

        message = str(caught.exception)
        self.assertIn("Missing HTML comments", message)
        self.assertIn("missing1", message)
        self.assertIn("missing2", message)

    def test_empty_parent_and_none_depth_are_both_reported_as_invalid_hierarchy(self) -> None:
        free = self.free(self.comment("no-parent"), self.comment("no-depth"))
        html = self.html(
            self.html_comment("no-parent", parent_id=""),
            self.html_comment("no-depth", level=None),
        )

        with self.assertRaises(ValueError) as caught:
            reconstruct_rows(free, html)

        message = str(caught.exception)
        self.assertIn("Invalid hierarchy", message)
        self.assertIn("no-parent", message)
        self.assertIn("no-depth", message)

    def test_missing_node_and_invalid_hierarchy_share_one_error(self) -> None:
        free = self.free(self.comment("missing"), self.comment("invalid"))
        html = self.html(self.html_comment("invalid", parent_id=""))

        with self.assertRaises(ValueError) as caught:
            reconstruct_rows(free, html)

        message = str(caught.exception)
        self.assertIn("Missing HTML comments", message)
        self.assertIn("missing", message)
        self.assertIn("Invalid hierarchy", message)
        self.assertIn("invalid", message)

    def test_join_is_exactly_by_comment_id_not_similar_content_or_author(self) -> None:
        free = self.free(
            self.comment("wanted", author="same", text="same text")
        )
        html = self.html(self.html_comment("different"))

        with self.assertRaises(ValueError) as caught:
            reconstruct_rows(free, html)

        self.assertIn("wanted", str(caught.exception))
        self.assertNotIn("different", str(caught.exception))

    def test_preserves_all_free_content_fields_exactly(self) -> None:
        free_comment = self.comment(
            "c1",
            author="=AUTHOR()",
            time="2026-01-01\n12:34",
            text="first line\n=HYPERLINK(\"x\")",
            url="=FORMULA-LIKE-URL",
        )

        row = reconstruct_rows(
            self.free(free_comment),
            self.html(self.html_comment("c1")),
        )[0]

        self.assertEqual("Exact title", row["Title"])
        self.assertEqual("Exact body", row["Post Body"])
        self.assertEqual(
            "https://www.reddit.com/r/test/comments/post1/example/",
            row["Post URL"],
        )
        self.assertEqual("=AUTHOR()", row["Author"])
        self.assertEqual("2026-01-01\n12:34", row["Time"])
        self.assertEqual("first line\n=HYPERLINK(\"x\")", row["Comment"])
        self.assertEqual("=FORMULA-LIKE-URL", row["Comment URL"])


if __name__ == "__main__":
    unittest.main()
