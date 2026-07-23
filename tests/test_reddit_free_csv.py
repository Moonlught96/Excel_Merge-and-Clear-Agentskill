from __future__ import annotations

import csv
import io
import tempfile
import unittest
from pathlib import Path

from tools.reddit_free_csv import FreeComment, FreeRedditExport, parse_free_reddit_csv


class RedditFreeCsvTest(unittest.TestCase):
    def setUp(self) -> None:
        self._temporary_directory = tempfile.TemporaryDirectory(
            dir=Path.cwd() / ".tmp-tests"
        )
        self.tmp = Path(self._temporary_directory.name)

    def tearDown(self) -> None:
        self._temporary_directory.cleanup()

    def _write_rows(
        self,
        rows: list[list[str]],
        *,
        encoding: str = "utf-8",
        filename: str = "reddit.csv",
    ) -> Path:
        stream = io.StringIO(newline="")
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerows(rows)
        path = self.tmp / filename
        path.write_text(stream.getvalue(), encoding=encoding, newline="")
        return path

    @staticmethod
    def _valid_rows() -> list[list[str]]:
        return [
            ["title", "A post title"],
            ["body", "First line\nSecond line"],
            ["url", "https://www.reddit.com/r/example/comments/AbC123/a_post_title/"],
            [],
            [
                "author_name",
                "date_time",
                "comment",
                "comment_url",
                "upvote_number",
            ],
            [
                "alice",
                "2026-07-20 10:00",
                "First comment",
                "https://www.reddit.com/r/example/comments/AbC123/a_post_title/comment/DeF456/",
                "10",
            ],
            [
                "bob",
                "2026-07-20 11:00",
                "Second comment",
                "https://www.reddit.com/r/example/comments/AbC123/a_post_title/comment/GhI789/?context=3#reply",
                "20",
            ],
        ]

    def test_parses_metadata_and_comments_in_source_order(self) -> None:
        path = self._write_rows(self._valid_rows())

        result = parse_free_reddit_csv(path)

        self.assertEqual(
            FreeRedditExport(
                title="A post title",
                body="First line\nSecond line",
                url="https://www.reddit.com/r/example/comments/AbC123/a_post_title/",
                post_id="AbC123",
                comments=(
                    FreeComment(
                        author="alice",
                        time="2026-07-20 10:00",
                        comment="First comment",
                        comment_url=(
                            "https://www.reddit.com/r/example/comments/AbC123/"
                            "a_post_title/comment/DeF456/"
                        ),
                        comment_id="def456",
                    ),
                    FreeComment(
                        author="bob",
                        time="2026-07-20 11:00",
                        comment="Second comment",
                        comment_url=(
                            "https://www.reddit.com/r/example/comments/AbC123/"
                            "a_post_title/comment/GhI789/?context=3#reply"
                        ),
                        comment_id="ghi789",
                    ),
                ),
            ),
            result,
        )

    def test_rejects_each_missing_metadata_key(self) -> None:
        for missing_key in ("title", "body", "url"):
            with self.subTest(missing_key=missing_key):
                rows = [
                    row
                    for row in self._valid_rows()
                    if not row or row[0] != missing_key
                ]
                path = self._write_rows(rows, filename=f"missing-{missing_key}.csv")

                with self.assertRaisesRegex(ValueError, missing_key):
                    parse_free_reddit_csv(path)

    def test_rejects_each_duplicate_metadata_key(self) -> None:
        for duplicate_key in ("title", "body", "url"):
            with self.subTest(duplicate_key=duplicate_key):
                rows = self._valid_rows()
                rows.insert(1, [duplicate_key, "duplicate value"])
                path = self._write_rows(
                    rows, filename=f"duplicate-{duplicate_key}.csv"
                )

                with self.assertRaisesRegex(ValueError, duplicate_key):
                    parse_free_reddit_csv(path)

    def test_rejects_missing_required_comment_header(self) -> None:
        for required_header in (
            "author_name",
            "date_time",
            "comment",
            "comment_url",
        ):
            with self.subTest(required_header=required_header):
                rows = self._valid_rows()
                rows[4] = [
                    header for header in rows[4] if header != required_header
                ]
                path = self._write_rows(
                    rows, filename=f"missing-header-{required_header}.csv"
                )

                with self.assertRaisesRegex(ValueError, required_header):
                    parse_free_reddit_csv(path)

    def test_rejects_invalid_post_url(self) -> None:
        rows = self._valid_rows()
        rows[2][1] = "https://www.reddit.com/r/example/a_post_title/"
        path = self._write_rows(rows)

        with self.assertRaisesRegex(ValueError, "post ID"):
            parse_free_reddit_csv(path)

    def test_rejects_invalid_or_missing_comment_url(self) -> None:
        invalid_urls = (
            "",
            "https://www.reddit.com/r/example/comments/abc123/a_post_title/",
            "https://www.reddit.com/comment/id/not-at-the-end/",
        )
        for index, invalid_url in enumerate(invalid_urls):
            with self.subTest(invalid_url=invalid_url):
                rows = self._valid_rows()
                rows[5][3] = invalid_url
                path = self._write_rows(rows, filename=f"invalid-comment-{index}.csv")

                with self.assertRaisesRegex(ValueError, "comment URL"):
                    parse_free_reddit_csv(path)

    def test_rejects_duplicate_comment_ids_case_insensitively(self) -> None:
        rows = self._valid_rows()
        rows[6][3] = (
            "https://www.reddit.com/r/example/comments/abc123/"
            "a_post_title/comment/DEF456/"
        )
        path = self._write_rows(rows)

        with self.assertRaisesRegex(ValueError, "def456"):
            parse_free_reddit_csv(path)

    def test_reads_all_supported_csv_encodings(self) -> None:
        cases = (
            ("utf-8-sig", "utf8-bom.csv"),
            ("utf-16", "utf16-bom.csv"),
            ("gb18030", "gb18030.csv"),
        )
        for encoding, filename in cases:
            with self.subTest(encoding=encoding):
                rows = self._valid_rows()
                rows[0][1] = "中文标题"
                path = self._write_rows(rows, encoding=encoding, filename=filename)

                result = parse_free_reddit_csv(path)

                self.assertEqual("中文标题", result.title)
                self.assertEqual(("def456", "ghi789"), tuple(
                    comment.comment_id for comment in result.comments
                ))

    def test_preserves_multiline_comment_exactly(self) -> None:
        rows = self._valid_rows()
        rows[5][2] = "line one\nline two\r\nline three"
        path = self._write_rows(rows)

        result = parse_free_reddit_csv(path)

        self.assertEqual("line one\nline two\r\nline three", result.comments[0].comment)

    def test_ignores_extra_columns_and_fills_missing_trailing_cells(self) -> None:
        rows = self._valid_rows()
        rows[4] = [
            "unregistered_before",
            "comment_url",
            "author_name",
            "date_time",
            "comment",
            "unregistered_after",
        ]
        rows[5] = [
            "ignored",
            "https://www.reddit.com/r/example/comments/AbC123/"
            "a_post_title/comment/DeF456/",
            "alice",
            "2026-07-20 10:00",
            "First comment",
            "also ignored",
        ]
        rows[6] = [
            "ignored",
            "https://www.reddit.com/r/example/comments/AbC123/"
            "a_post_title/comment/GhI789/",
        ]
        path = self._write_rows(rows)

        result = parse_free_reddit_csv(path)

        self.assertEqual("alice", result.comments[0].author)
        self.assertEqual("", result.comments[1].author)
        self.assertEqual("", result.comments[1].time)
        self.assertEqual("", result.comments[1].comment)
        self.assertEqual(2, len(result.comments))


if __name__ == "__main__":
    unittest.main()
