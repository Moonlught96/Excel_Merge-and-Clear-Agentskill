import csv
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from openpyxl import load_workbook

from tools.reddit_free_csv import FreeComment, FreeRedditExport
from tools.reddit_saved_html import HtmlComment, SavedRedditHtml
from tools.output_path_safety import OutputPathConflictError
from tools import reconstruct_reddit_comments
from tools.reconstruct_reddit_comments import (
    OUTPUT_HEADERS,
    reconstruct_rows,
    write_outputs,
)


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

    def test_only_exact_zero_thread_level_is_not_a_reply(self) -> None:
        rows = reconstruct_rows(
            self.free(self.comment("synthetic-negative")),
            self.html(self.html_comment("synthetic-negative", level=-1)),
        )

        self.assertEqual("Yes", rows[0]["Is Reply"])

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

    def test_whitespace_only_html_post_fields_are_missing(self) -> None:
        cases = (
            ("Post Author", "post_author"),
            ("Post Score", "post_score"),
            ("Post Comment Count", "post_comment_count"),
        )
        for field_name, field_key in cases:
            with self.subTest(field_name=field_name):
                html_values = {
                    "post_author": "author",
                    "post_score": "score",
                    "post_comment_count": "count",
                }
                html_values[field_key] = " \t "
                with self.assertRaisesRegex(ValueError, field_name):
                    reconstruct_rows(
                        self.free(self.comment("c1")),
                        self.html(self.html_comment("c1"), **html_values),
                    )

    def test_whitespace_only_explicit_post_fallbacks_are_missing(self) -> None:
        cases = (
            ("Post Author", "post_author"),
            ("Post Score", "post_score"),
            ("Post Comment Count", "post_comment_count"),
        )
        for field_name, field_key in cases:
            with self.subTest(field_name=field_name):
                html_values = {
                    "post_author": "author",
                    "post_score": "score",
                    "post_comment_count": "count",
                }
                html_values[field_key] = ""
                fallback_values = {field_key: " \r\n "}
                with self.assertRaisesRegex(ValueError, field_name):
                    reconstruct_rows(
                        self.free(self.comment("c1")),
                        self.html(self.html_comment("c1"), **html_values),
                        **fallback_values,
                    )

    def test_whitespace_html_uses_valid_fallbacks_without_stripping_them(self) -> None:
        rows = reconstruct_rows(
            self.free(self.comment("c1")),
            self.html(
                self.html_comment("c1"),
                post_author=" ",
                post_score="\t",
                post_comment_count="\r\n",
            ),
            post_author=" fallback author ",
            post_score=" 7 ",
            post_comment_count=" 1 ",
        )

        self.assertEqual(" fallback author ", rows[0]["Post Author"])
        self.assertEqual(" 7 ", rows[0]["Post Score"])
        self.assertEqual(" 1 ", rows[0]["Post Comment Count"])

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


class RedditOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.directory = Path(self.temporary_directory.name)
        self.input_csv = self.directory / "input.csv"
        self.input_html = self.directory / "input.html"
        self.input_csv.write_bytes(b"original csv input")
        self.input_html.write_bytes(b"original html input")
        self.output_xlsx = self.directory / "output.xlsx"
        self.output_csv = self.directory / "output.csv"

    def row(self, **overrides: str | int) -> dict[str, str | int]:
        values: dict[str, str | int] = {
            "Title": "A title",
            "Post Body": "A body",
            "Post URL": "https://reddit.com/r/test/comments/post1/",
            "Post Author": "post-author",
            "Post Score": "10",
            "Post Comment Count": "1",
            "Author": "comment-author",
            "Time": "2026-07-23",
            "Score": "5",
            "Thread Level": 0,
            "Is Reply": "No",
            "Comment": "A comment",
            "Comment URL": "https://reddit.com/comment/c1/",
            "Comment ID": "c1",
            "Parent ID": "post1",
        }
        values.update(overrides)
        return values

    def write(self, rows: list[dict[str, str | int]], *, overwrite: bool = False) -> None:
        write_outputs(
            rows,
            input_paths=(self.input_csv, self.input_html),
            output_xlsx=self.output_xlsx,
            output_csv=self.output_csv,
            overwrite=overwrite,
        )

    def csv_rows(self) -> list[list[str]]:
        with self.output_csv.open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.reader(handle))

    def test_writes_matching_exact_headers_row_count_and_values(self) -> None:
        rows = [self.row(), self.row(**{"Comment ID": "c2", "Thread Level": 2})]

        self.write(rows)

        workbook = load_workbook(self.output_xlsx, data_only=False)
        sheet = workbook.active
        xlsx_rows = list(sheet.iter_rows(values_only=True))
        csv_rows = self.csv_rows()
        self.assertEqual("Reddit Comments", sheet.title)
        self.assertEqual(list(OUTPUT_HEADERS), list(xlsx_rows[0]))
        self.assertEqual(list(OUTPUT_HEADERS), csv_rows[0])
        self.assertEqual(len(rows) + 1, len(xlsx_rows))
        self.assertEqual(len(rows) + 1, len(csv_rows))
        for row_number, source_row in enumerate(rows, start=1):
            expected = [source_row[header] for header in OUTPUT_HEADERS]
            self.assertEqual(expected, list(xlsx_rows[row_number]))
            self.assertEqual([str(value) for value in expected], csv_rows[row_number])

    def test_csv_has_utf8_bom_and_round_trips_special_content(self) -> None:
        special = '中文 😀, "quoted"\nsecond line'
        self.write([self.row(**{"Comment": special})])

        self.assertTrue(self.output_csv.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertEqual(special, self.csv_rows()[1][OUTPUT_HEADERS.index("Comment")])
        workbook = load_workbook(self.output_xlsx)
        self.assertEqual(
            special,
            workbook.active.cell(2, OUTPUT_HEADERS.index("Comment") + 1).value,
        )

    def test_formula_like_xlsx_values_are_text(self) -> None:
        markers = ("=SUM(1,2)", "+123", "-456", "@mention")
        rows = [
            self.row(**{"Comment ID": f"c{index}", "Comment": value})
            for index, value in enumerate(markers)
        ]

        self.write(rows)

        sheet = load_workbook(self.output_xlsx, data_only=False).active
        column = OUTPUT_HEADERS.index("Comment") + 1
        for row_number, expected in enumerate(markers, start=2):
            cell = sheet.cell(row_number, column)
            self.assertEqual(expected, cell.value)
            self.assertEqual("s", cell.data_type)

    def test_missing_optional_score_is_written_as_blank_in_both_outputs(self) -> None:
        self.write([self.row(**{"Score": ""})])

        sheet = load_workbook(self.output_xlsx).active
        score_column = OUTPUT_HEADERS.index("Score") + 1
        self.assertIsNone(sheet.cell(2, score_column).value)
        self.assertEqual("", self.csv_rows()[1][score_column - 1])

    def test_existing_outputs_are_rejected_without_overwrite_and_unchanged(self) -> None:
        self.output_xlsx.write_bytes(b"old xlsx")
        self.output_csv.write_bytes(b"old csv")

        with self.assertRaises(OutputPathConflictError):
            self.write([self.row()])

        self.assertEqual(b"old xlsx", self.output_xlsx.read_bytes())
        self.assertEqual(b"old csv", self.output_csv.read_bytes())

    def test_overwrite_true_updates_both_outputs(self) -> None:
        self.output_xlsx.write_bytes(b"old xlsx")
        self.output_csv.write_bytes(b"old csv")

        self.write([self.row(**{"Comment": "replacement"})], overwrite=True)

        self.assertEqual(
            "replacement",
            load_workbook(self.output_xlsx).active.cell(
                2, OUTPUT_HEADERS.index("Comment") + 1
            ).value,
        )
        self.assertEqual(
            "replacement",
            self.csv_rows()[1][OUTPUT_HEADERS.index("Comment")],
        )

    def test_input_output_alias_is_rejected_even_with_overwrite(self) -> None:
        with self.assertRaises(OutputPathConflictError):
            write_outputs(
                [self.row()],
                input_paths=(self.input_csv, self.input_html),
                output_xlsx=self.input_csv,
                output_csv=self.output_csv,
                overwrite=True,
            )

        self.assertEqual(b"original csv input", self.input_csv.read_bytes())
        self.assertFalse(self.output_csv.exists())

    def test_duplicate_output_paths_are_rejected(self) -> None:
        with self.assertRaises(OutputPathConflictError):
            write_outputs(
                [self.row()],
                input_paths=(self.input_csv, self.input_html),
                output_xlsx=self.output_xlsx,
                output_csv=self.output_xlsx,
                overwrite=False,
            )

        self.assertFalse(self.output_xlsx.exists())

    def test_csv_staging_failure_preserves_existing_outputs_and_cleans_stages(
        self,
    ) -> None:
        self.output_xlsx.write_bytes(b"old xlsx")
        self.output_csv.write_bytes(b"old csv")

        with patch.object(
            reconstruct_reddit_comments,
            "_write_csv",
            side_effect=RuntimeError("simulated CSV failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "simulated CSV failure"):
                self.write([self.row()], overwrite=True)

        self.assertEqual(b"old xlsx", self.output_xlsx.read_bytes())
        self.assertEqual(b"old csv", self.output_csv.read_bytes())
        self.assertEqual(
            {"input.csv", "input.html", "output.xlsx", "output.csv"},
            {path.name for path in self.directory.iterdir()},
        )

    def test_success_leaves_no_extra_files(self) -> None:
        self.write([self.row()])

        self.assertEqual(
            {"input.csv", "input.html", "output.xlsx", "output.csv"},
            {path.name for path in self.directory.iterdir()},
        )


if __name__ == "__main__":
    unittest.main()
