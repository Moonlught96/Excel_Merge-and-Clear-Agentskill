import tempfile
import unittest
from pathlib import Path

from tools.reddit_saved_html import (
    HtmlComment,
    SavedRedditHtml,
    parse_saved_reddit_html,
)


class ParseSavedRedditHtmlTests(unittest.TestCase):
    def parse(self, html: str, *, bom: bool = False) -> SavedRedditHtml:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "saved.html"
            encoding = "utf-8-sig" if bom else "utf-8"
            path.write_text(html, encoding=encoding)
            return parse_saved_reddit_html(path)

    def test_parses_post_root_comment_and_reply(self) -> None:
        result = self.parse(
            """
            <shreddit-post thingid="t3_AbC123" author="post_author"
                score="42" comment-count="2">
              <shreddit-comment thingid="t1_Root1" parentid="t3_AbC123"
                  depth="0" score="10">ignored content</shreddit-comment>
              <shreddit-comment thingid="t1_Reply2" parentid="t1_Root1"
                  depth="1">ignored reply</shreddit-comment>
            </shreddit-post>
            """
        )

        self.assertEqual(
            result,
            SavedRedditHtml(
                post_id="abc123",
                post_author="post_author",
                post_score="42",
                post_comment_count="2",
                comments={
                    "root1": HtmlComment("root1", "abc123", 0, "10"),
                    "reply2": HtmlComment("reply2", "root1", 1, ""),
                },
            ),
        )

    def test_registered_attribute_precedence_and_empty_fallback(self) -> None:
        result = self.parse(
            """
            <shreddit-post thingid="post1" score="" data-score="99"
                comment-count="" commentcount="7" author="a">
              <shreddit-comment thingid="comment1" parentid="post1"
                  score="5" data-score="6"></shreddit-comment>
              <shreddit-comment thingid="comment2" parentid="post1"
                  score="" data-score="8"></shreddit-comment>
            </shreddit-post>
            """
        )

        self.assertEqual(result.post_score, "99")
        self.assertEqual(result.post_comment_count, "7")
        self.assertEqual(result.comments["comment1"].score, "5")
        self.assertEqual(result.comments["comment2"].score, "8")

    def test_tags_and_attributes_are_case_insensitive_and_ids_are_normalized(self) -> None:
        result = self.parse(
            """
            <SHREDDIT-POST THINGID="T3_PostABC" AUTHOR="Casey"
                DATA-SCORE="3" COMMENTCOUNT="1">
              <Shreddit-Comment ThingId="T1_CommXYZ" ParentId="T3_PostABC"
                  Depth="0" Data-Score="2"></Shreddit-Comment>
            </SHREDDIT-POST>
            """
        )

        self.assertEqual(result.post_id, "postabc")
        self.assertEqual(result.post_author, "Casey")
        self.assertEqual(result.comments["commxyz"].parent_id, "postabc")

    def test_duplicate_comment_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate comment ID.*sameid"):
            self.parse(
                """
                <shreddit-post thingid="post1">
                  <shreddit-comment thingid="t1_sameid"></shreddit-comment>
                  <shreddit-comment thingid="SAMEID"></shreddit-comment>
                </shreddit-post>
                """
            )

    def test_multiple_different_post_ids_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "multiple.*post ID"):
            self.parse(
                """
                <shreddit-post thingid="post1"></shreddit-post>
                <shreddit-post thingid="post2"></shreddit-post>
                """
            )

    def test_html_without_registered_post_node_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "missing.*post ID"):
            self.parse(
                """
                <article data-post-id="fake1">
                  <div class="promoted">Advertisement</div>
                  <shreddit-comment thingid="t1_orphan"></shreddit-comment>
                </article>
                """
            )

    def test_unrelated_promotional_and_article_nodes_are_ignored(self) -> None:
        result = self.parse(
            """
            <article thingid="t3_fake" score="999">
              <shreddit-ad-post thingid="t3_ad1" comment-count="500"></shreddit-ad-post>
              <div data-comment-id="t1_fake">promoted text</div>
            </article>
            <shreddit-post thingid="t3_real1" author="real" score="1"
                comment-count="0"></shreddit-post>
            """
        )

        self.assertEqual(result.post_id, "real1")
        self.assertEqual(result.post_score, "1")
        self.assertEqual(result.comments, {})

    def test_invalid_post_ids_are_rejected(self) -> None:
        for invalid_id in ("t3_bad-id", "t3_bad%20id", "t3_café", "t3_аbc", "t3_bad&#95;id"):
            with self.subTest(invalid_id=invalid_id):
                with self.assertRaisesRegex(ValueError, "invalid post ID"):
                    self.parse(f'<shreddit-post thingid="{invalid_id}"></shreddit-post>')

    def test_invalid_comment_ids_are_rejected_but_empty_ids_are_ignored(self) -> None:
        result = self.parse(
            """
            <shreddit-post thingid="post1">
              <shreddit-comment></shreddit-comment>
              <shreddit-comment thingid=""></shreddit-comment>
            </shreddit-post>
            """
        )
        self.assertEqual(result.comments, {})

        for invalid_id in ("t1_bad-id", "t1_bad%20id", "t1_café", "t1_аbc", "t1_bad&#95;id"):
            with self.subTest(invalid_id=invalid_id):
                with self.assertRaisesRegex(ValueError, "invalid comment ID"):
                    self.parse(
                        f"""
                        <shreddit-post thingid="post1">
                          <shreddit-comment thingid="{invalid_id}"></shreddit-comment>
                        </shreddit-post>
                        """
                    )

    def test_invalid_parent_ids_are_rejected(self) -> None:
        for invalid_id in (
            "t3_bad-id",
            "t1_bad%20id",
            "t3_café",
            "t1_аbc",
            "t3_bad&#95;id",
        ):
            with self.subTest(invalid_id=invalid_id):
                with self.assertRaisesRegex(ValueError, "invalid parent ID"):
                    self.parse(
                        f"""
                        <shreddit-post thingid="post1">
                          <shreddit-comment thingid="comment1"
                              parentid="{invalid_id}"></shreddit-comment>
                        </shreddit-post>
                        """
                    )

    def test_depth_accepts_only_nonnegative_ascii_digits(self) -> None:
        result = self.parse(
            """
            <shreddit-post thingid="post1">
              <shreddit-comment thingid="zero" depth="0"></shreddit-comment>
              <shreddit-comment thingid="one" depth="1"></shreddit-comment>
              <shreddit-comment thingid="negative" depth="-1"></shreddit-comment>
              <shreddit-comment thingid="letters" depth="one"></shreddit-comment>
              <shreddit-comment thingid="unicode" depth="١"></shreddit-comment>
            </shreddit-post>
            """
        )

        self.assertEqual(result.comments["zero"].thread_level, 0)
        self.assertEqual(result.comments["one"].thread_level, 1)
        self.assertIsNone(result.comments["negative"].thread_level)
        self.assertIsNone(result.comments["letters"].thread_level)
        self.assertIsNone(result.comments["unicode"].thread_level)

    def test_utf8_bom_is_supported(self) -> None:
        result = self.parse(
            '<shreddit-post thingid="t3_bom1" author="作者"></shreddit-post>',
            bom=True,
        )

        self.assertEqual(result.post_id, "bom1")
        self.assertEqual(result.post_author, "作者")


if __name__ == "__main__":
    unittest.main()
