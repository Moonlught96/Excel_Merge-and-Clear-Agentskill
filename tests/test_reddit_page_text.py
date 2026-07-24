from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path

from tools.reddit_json_export import (
    RedditJsonComment,
    RedditJsonExport,
    RedditMeta,
    RedditPost,
)
from tools.reddit_page_text import (
    PageCommentMetric,
    RedditPageText,
    RedditPageTextError,
    normalize_author,
    normalize_content,
    parse_reddit_page_text,
)


def json_export(
    *,
    subreddit: str = "python",
    title: str = "Unicode 标题 🐍",
    author: str = "CaféUser",
    num_comments: int = 5,
) -> RedditJsonExport:
    return RedditJsonExport(
        meta=RedditMeta(
            collected_comment_count=0,
            reported_by_api=num_comments,
            discrepancy=num_comments,
        ),
        post=RedditPost(
            id="post1",
            subreddit=subreddit,
            title=title,
            content="post body",
            author=author,
            num_comments=num_comments,
        ),
        comments=(),
    )


def valid_page(
    *,
    subreddit: str = "python",
    author: str = "CaféUser",
    time: str = "8小时前",
    title: str = "Unicode 标题 🐍",
    score: str = "99",
    comment_count: str = "5",
) -> str:
    return "\n".join(
        (
            "Reddit",
            f"r/{subreddit}",
            f"u/{author}",
            f"{author} 头像",
            time,
            title,
            "正文",
            "赞同",
            score,
            "反对",
            comment_count,
            "转到评论",
            "评论区域",
            "评论内容稍后解析",
        )
    )


PAGE_PREFIX = "\n".join(
    (
        "Reddit",
        "r/python",
        "u/Caf\u00e9User",
        "Caf\u00e9User \u5934\u50cf",
        "8\u5c0f\u65f6\u524d",
        "Unicode \u6807\u9898 \U0001f40d",
        "\u6b63\u6587",
        "\u8d5e\u540c",
        "99",
        "\u53cd\u5bf9",
        "2",
        "\u8f6c\u5230\u8bc4\u8bba",
        "\u8bc4\u8bba\u533a\u57df",
    )
) + "\n"

FIRST_COMMENT = """
AutoModerator
\u7248\u4e3b
\u20228\u5c0f\u65f6\u524d
Wallpaper from **[Basic Apple Guy](https://example.com)** &amp; friends

\u8d5e\u540c
3
\u53cd\u5bf9
\u56de\u590d
\u5956\u52b1
\u5206\u4eab
"""

PROMOTED_BLOCK = """
u/ad-user \u5934\u50cf
ad-user
999
\u2022\u5df2\u63a8\u5e7f Advertisement
"""

SECOND_COMMENT = """
eldergooooose__
\u20228\u5c0f\u65f6\u524d
What monitor? \U0001f914

\u8d5e\u540c\u6295\u7968
\u53cd\u5bf9
\u56de\u590d
\u5956\u52b1
\u5206\u4eab
"""

COMMENT_TEXT = FIRST_COMMENT + PROMOTED_BLOCK + SECOND_COMMENT


class RedditPageTextTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path.cwd() / ".tmp-tests" / self._testMethodName
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.path = self.tmp / "reddit-page.txt"

    def write_text(self, text: str, *, encoding: str = "utf-8") -> Path:
        self.path.write_text(text, encoding=encoding)
        return self.path

    def write_bytes(self, content: bytes) -> Path:
        self.path.write_bytes(content)
        return self.path

    def parse(
        self, text: str, *, export: RedditJsonExport | None = None
    ) -> RedditPageText:
        return parse_reddit_page_text(
            self.write_text(text),
            export or json_export(),
            require_comments=False,
        )

    def export(self) -> RedditJsonExport:
        comments = (
            RedditJsonComment(
                id="comment1",
                parent_id="post1",
                content="first comment",
                depth=0,
                username="first-user",
                date="2026-01-01",
                created_utc=1,
            ),
            RedditJsonComment(
                id="comment2",
                parent_id="post1",
                content="second comment",
                depth=0,
                username="second-user",
                date="2026-01-01",
                created_utc=2,
            ),
        )
        return RedditJsonExport(
            meta=RedditMeta(
                collected_comment_count=2,
                reported_by_api=2,
                discrepancy=0,
            ),
            post=RedditPost(
                id="post1",
                subreddit="python",
                title="Unicode \u6807\u9898 \U0001f40d",
                content="post body",
                author="Caf\u00e9User",
                num_comments=2,
            ),
            comments=comments,
        )

    def export_for_comments(self) -> RedditJsonExport:
        export = self.export()
        comments = (
            replace(
                export.comments[0],
                username="AutoModerator",
                content=(
                    "Wallpaper from **[Basic Apple Guy]"
                    "(https://example.com)** &amp; friends"
                ),
            ),
            replace(
                export.comments[1],
                username="eldergooooose__",
                content="What monitor? \U0001f914",
            ),
        )
        return replace(export, comments=comments)

    def assert_invalid(
        self, text: str, *, export: RedditJsonExport | None = None
    ) -> None:
        with self.assertRaises(RedditPageTextError):
            self.parse(text, export=export)

    def test_parses_approved_post_sample(self) -> None:
        result = self.parse(valid_page())

        self.assertEqual(
            RedditPageText(
                post_time="8小时前",
                post_score=99,
                post_comment_count=5,
                comments=(),
            ),
            result,
        )
        self.assertIsInstance(result.comments, tuple)

    def test_result_models_are_frozen(self) -> None:
        metric = PageCommentMetric(score=3)
        with self.assertRaises(AttributeError):
            metric.score = 4  # type: ignore[misc]
        result = self.parse(valid_page())
        with self.assertRaises(AttributeError):
            result.post_score = 4  # type: ignore[misc]

    def test_rejects_unparsed_comment_content_safely(self) -> None:
        with self.assertRaisesRegex(
            RedditPageTextError, "^unparsed trailing page comment content$"
        ):
            parse_reddit_page_text(self.write_text(valid_page()), json_export())

    def test_aligns_comments_and_extracts_number_or_blank_score(self) -> None:
        result = parse_reddit_page_text(
            self.write_text(PAGE_PREFIX + COMMENT_TEXT),
            self.export_for_comments(),
        )
        self.assertEqual([3, None], [item.score for item in result.comments])

    def test_deleted_author_and_markdown_html_normalization_are_fixed(self) -> None:
        self.assertEqual("[deleted]", normalize_author("[\u5df2\u5220\u9664]"))
        self.assertEqual("[deleted]", normalize_author("[deleted]"))
        self.assertEqual(
            "Rules/Wiki & friends",
            normalize_content(
                "## **[Rules/Wiki](https://example.com)** &amp; friends"
            ),
        )

    def test_rejects_author_content_order_and_score_mismatches(self) -> None:
        export = self.export_for_comments()
        cases = (
            (COMMENT_TEXT.replace("AutoModerator", "wrong", 1), "author"),
            (COMMENT_TEXT.replace("Wallpaper from", "Different text", 1), "content"),
            (
                COMMENT_TEXT.replace("\u8d5e\u540c\n3", "\u8d5e\u540c\n1.2K", 1),
                "score",
            ),
            (SECOND_COMMENT + PROMOTED_BLOCK + FIRST_COMMENT, "author"),
            (COMMENT_TEXT + FIRST_COMMENT, "block count"),
        )
        for text, message in cases:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    parse_reddit_page_text(
                        self.write_text(PAGE_PREFIX + text),
                        export,
                    )

    def test_rejects_incomplete_comment_operation_controls(self) -> None:
        export = self.export_for_comments()
        for label in ("\u53cd\u5bf9", "\u56de\u590d", "\u5206\u4eab"):
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "comment"):
                    parse_reddit_page_text(
                        self.write_text(PAGE_PREFIX + COMMENT_TEXT.replace(label, "", 1)),
                        export,
                    )

    def test_parses_negative_and_grouped_comment_scores(self) -> None:
        text = COMMENT_TEXT.replace("\u8d5e\u540c\n3", "\u8d5e\u540c\n-3", 1).replace(
            "\u8d5e\u540c\u6295\u7968\n", "\u8d5e\u540c\n1,234\n", 1
        )
        result = parse_reddit_page_text(
            self.write_text(PAGE_PREFIX + text),
            self.export_for_comments(),
        )
        self.assertEqual([-3, 1234], [item.score for item in result.comments])

    def test_matches_deleted_author_and_ignores_promoted_numbers(self) -> None:
        export = self.export_for_comments()
        export = replace(export, comments=(replace(export.comments[0], username="[deleted]"), export.comments[1]))
        result = parse_reddit_page_text(
            self.write_text(
                PAGE_PREFIX
                + COMMENT_TEXT.replace("AutoModerator", "[\u5df2\u5220\u9664]", 1)
            ),
            export,
        )
        self.assertEqual([3, None], [item.score for item in result.comments])

    def test_accepts_all_raw_time_forms_without_changing_them(self) -> None:
        for raw_time in (
            "刚刚",
            "0分钟前",
            "12分钟前",
            "3小时前",
            "4天前",
            "5周前",
            "6个月前",
            "7年前",
        ):
            with self.subTest(raw_time=raw_time):
                self.assertEqual(raw_time, self.parse(valid_page(time=raw_time)).post_time)

    def test_rejects_non_ascii_or_non_integer_time_amounts(self) -> None:
        for raw_time in ("１小时前", "-1天前", "+1天前", "1.5天前", "一天前"):
            with self.subTest(raw_time=raw_time):
                self.assert_invalid(valid_page(time=raw_time))

    def test_normalizes_author_entities_unicode_prefix_and_deleted_marker(self) -> None:
        self.assertEqual("Café&User", normalize_author(" u/Cafe\u0301&amp;User "))
        self.assertEqual("[deleted]", normalize_author("[已删除]"))
        self.assertEqual("[deleted]", normalize_author("u/[deleted]"))

    def test_matches_canonically_equal_author_and_ignores_avatar_line(self) -> None:
        export = json_export(author="Café&User")
        page = valid_page(author="Cafe\u0301&amp;User").replace(
            "Cafe\u0301&amp;User 头像", "WrongAuthor 头像"
        )
        self.assertEqual(99, self.parse(page, export=export).post_score)

    def test_requires_exactly_one_comment_area_marker(self) -> None:
        self.assert_invalid(valid_page().replace("评论区域\n", ""))
        self.assert_invalid(valid_page() + "\n评论区域")
        self.assert_invalid(valid_page().replace("评论区域", " 评论区域 extra"))

    def test_requires_exact_unique_subreddit_and_title_in_order(self) -> None:
        self.assert_invalid(valid_page().replace("r/python\n", ""))
        self.assert_invalid(valid_page().replace("r/python", "r/Python"))
        self.assert_invalid(valid_page().replace("r/python", "r/python\nr/python"))
        self.assert_invalid(valid_page().replace("Unicode 标题 🐍", "Unicode 标题"))
        self.assert_invalid(
            valid_page().replace("Unicode 标题 🐍", "Unicode 标题 🐍\nUnicode 标题 🐍")
        )
        lines = valid_page().splitlines()
        subreddit_index = lines.index("r/python")
        title_index = lines.index("Unicode 标题 🐍")
        lines[subreddit_index], lines[title_index] = (
            lines[title_index],
            lines[subreddit_index],
        )
        self.assert_invalid("\n".join(lines))

    def test_requires_one_matching_author_and_one_valid_time_between_anchor_lines(
        self,
    ) -> None:
        self.assert_invalid(valid_page().replace("u/CaféUser\n", "u/Other\n"))
        self.assert_invalid(valid_page().replace("u/CaféUser", "u/CaféUser\nCaféUser"))
        self.assert_invalid(valid_page().replace("8小时前\n", ""))
        self.assert_invalid(valid_page().replace("8小时前", "8小时前\n7小时前"))
        self.assert_invalid(
            valid_page().replace("8小时前", "8小时前").replace(
                "u/CaféUser", "u/CaféUser 头像"
            )
        )

    def test_normalizes_line_endings_and_strips_lines_for_structure(self) -> None:
        padded = "\r\n".join(f"  {line}  " for line in valid_page().splitlines())
        self.assertEqual(99, self.parse(padded).post_score)

    def test_requires_one_exact_go_to_comments_after_title(self) -> None:
        self.assert_invalid(valid_page().replace("转到评论\n", ""))
        self.assert_invalid(valid_page().replace("转到评论", "转到评论\n转到评论"))
        self.assert_invalid(valid_page().replace("转到评论", "转到评论 extra"))
        self.assert_invalid(valid_page().replace("正文\n", "正文\n转到评论\n"))

    def test_score_and_comment_count_are_separated_by_exact_labels(self) -> None:
        self.assert_invalid(valid_page().replace("赞同\n99\n反对\n5", "赞同\n99\n5\n反对"))
        self.assert_invalid(valid_page().replace("赞同", "赞"))
        self.assert_invalid(valid_page().replace("反对", "反对票"))
        self.assert_invalid(valid_page().replace("赞同\n99\n反对\n5", "反对\n99\n赞同\n5"))

    def test_accepts_zero_and_canonical_comma_grouping(self) -> None:
        result = self.parse(
            valid_page(score="0", comment_count="1,234"),
            export=json_export(num_comments=1234),
        )
        self.assertEqual(0, result.post_score)
        self.assertEqual(1234, result.post_comment_count)

    def test_rejects_invalid_integer_forms(self) -> None:
        invalid_values = (
            "-1",
            "+1",
            "01",
            "00",
            "1.2K",
            "1.2万",
            "12,34",
            "1234,567",
            "1,23,456",
            "1 234",
        )
        for value in invalid_values:
            with self.subTest(value=value, field="score"):
                self.assert_invalid(valid_page(score=value))
            with self.subTest(value=value, field="comment_count"):
                self.assert_invalid(valid_page(comment_count=value))

    def test_rejects_comment_count_mismatch_with_json(self) -> None:
        self.assert_invalid(valid_page(comment_count="4"))

    def test_ignores_valid_metric_lookalike_in_body(self) -> None:
        duplicate = "赞同\n20\n反对\n5\n"
        result = self.parse(valid_page().replace("正文\n", f"正文\n{duplicate}"))
        self.assertEqual((99, 5), (result.post_score, result.post_comment_count))

    def test_ignores_malformed_metric_lookalikes_in_body(self) -> None:
        malformed_values = ("1.2K", "-1", "01", "12,34")
        for value in malformed_values:
            with self.subTest(value=value):
                malformed = f"赞同\n{value}\n反对\n5\n"
                result = self.parse(
                    valid_page().replace("正文\n", f"正文\n{malformed}")
                )
                self.assertEqual(
                    (99, 5),
                    (result.post_score, result.post_comment_count),
                )

    def test_rejects_body_lookalike_when_actual_final_ui_sequence_is_missing(
        self,
    ) -> None:
        body_lookalike = "赞同\n99\n反对\n5"
        page = valid_page().replace(
            "正文\n赞同\n99\n反对\n5",
            f"{body_lookalike}\n正文末尾",
        )
        self.assert_invalid(page)

    def test_rejects_nonblank_line_between_metric_count_and_action(self) -> None:
        page = valid_page().replace("5\n转到评论", "5\n广告尾行\n转到评论")
        self.assert_invalid(page)

    def test_oversized_score_and_comment_count_raise_safe_error(self) -> None:
        oversized = "9" * 5000
        cases = (
            ("score", valid_page(score=oversized), json_export()),
            (
                "comment_count",
                valid_page(comment_count=oversized),
                json_export(num_comments=0),
            ),
        )
        for field, page, export in cases:
            with self.subTest(field=field):
                self.write_text(page)
                with self.assertRaises(RedditPageTextError) as caught:
                    parse_reddit_page_text(
                        self.path,
                        export,
                        require_comments=False,
                    )
                self.assertNotIn(oversized, str(caught.exception))

    def test_accepts_utf8_bom_utf16_bom_and_gb18030(self) -> None:
        export = json_export()
        page = valid_page()
        encoded_pages = (
            page.encode("utf-8-sig"),
            page.encode("utf-16"),
            page.encode("gb18030"),
        )
        for index, encoded in enumerate(encoded_pages):
            with self.subTest(index=index):
                result = parse_reddit_page_text(
                    self.write_bytes(encoded), export, require_comments=False
                )
                self.assertEqual(99, result.post_score)

    def test_rejects_utf16_without_bom_and_invalid_bytes(self) -> None:
        for content in (valid_page().encode("utf-16-le"), b"\xff\xff\x81"):
            with self.subTest(content=content[:4]):
                with self.assertRaises(RedditPageTextError):
                    parse_reddit_page_text(
                        self.write_bytes(content),
                        json_export(),
                        require_comments=False,
                    )

    def test_rejects_utf32_as_an_unsupported_encoding(self) -> None:
        self.write_bytes(valid_page().encode("utf-32"))
        with self.assertRaisesRegex(RedditPageTextError, "encoding unsupported"):
            parse_reddit_page_text(
                self.path,
                json_export(),
                require_comments=False,
            )

    def test_preserves_source_file(self) -> None:
        original = valid_page().encode("utf-8")
        self.write_bytes(original)
        parse_reddit_page_text(self.path, json_export(), require_comments=False)
        self.assertEqual(original, self.path.read_bytes())

    def test_errors_are_category_only_and_never_leak_source_text(self) -> None:
        secret = "PRIVATE_UNIQUE_AUTHOR_AND_CONTENT"
        malformed = valid_page(author=secret).replace("r/python", "wrong-community")
        self.write_text(malformed)

        with self.assertRaises(RedditPageTextError) as caught:
            parse_reddit_page_text(
                self.path,
                json_export(author=secret),
                require_comments=False,
            )

        message = str(caught.exception)
        self.assertNotIn(secret, message)
        self.assertNotIn("wrong-community", message)


if __name__ == "__main__":
    unittest.main()
