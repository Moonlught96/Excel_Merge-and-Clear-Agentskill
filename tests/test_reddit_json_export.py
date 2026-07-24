from __future__ import annotations

import json
import unittest
from pathlib import Path
from typing import Any

from tools.reddit_json_export import (
    RedditJsonError,
    RedditJsonExport,
    RedditMeta,
    RedditPost,
    parse_reddit_json,
)


def valid_payload() -> dict[str, Any]:
    return {
        "meta": {
            "completeness": "complete",
            "collectedCommentCount": 2,
            "reportedByApi": 2,
            "discrepancy": 0,
            "failedMore": 0,
            "failedNodes": [],
            "failedReasons": {},
            "failedDetails": None,
        },
        "post": {
            "id": "AbC123",
            "subreddit": "  测试社区  ",
            "title": "  A title\n第二行  ",
            "content": "正文 😀\nnext line",
            "author": "  OriginalAuthor  ",
            "num_comments": 2,
            "link": "https://example.invalid/post",
            "upvote_ratio": 0.95,
        },
        "comments": [
            {
                "id": "t1_Root1",
                "parent_id": "t3_ABC123",
                "content": "  根评论 😀\n第二行  ",
                "depth": 0,
                "username": "  用户一  ",
                "date": "  2026-07-23  ",
                "created_utc": 1753228800,
                "ignored": "extra",
            },
            {
                "id": "Reply2",
                "parent_id": "t1_ROOT1",
                "content": "Reply\nwith details",
                "depth": 1,
                "username": "reply-user",
                "date": "2026-07-23",
                "created_utc": 1753228810,
            },
        ],
        "ignored": {"anything": True},
    }


class RedditJsonExportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path.cwd() / ".tmp-tests" / self._testMethodName
        self.tmp.mkdir(parents=True, exist_ok=True)
        self.path = self.tmp / "reddit.json"

    def write_payload(
        self, payload: Any, *, encoding: str = "utf-8", path: Path | None = None
    ) -> Path:
        target = path or self.path
        target.write_text(
            json.dumps(payload, ensure_ascii=False), encoding=encoding
        )
        return target

    def write_raw(self, text: str) -> Path:
        self.path.write_text(text, encoding="utf-8")
        return self.path

    def assert_invalid(self, payload: Any) -> None:
        self.write_payload(payload)
        with self.assertRaises(RedditJsonError):
            parse_reddit_json(self.path)

    def test_parses_root_and_reply_and_preserves_order_and_text_exactly(self) -> None:
        payload = valid_payload()
        result = parse_reddit_json(self.write_payload(payload))

        self.assertIsInstance(result, RedditJsonExport)
        self.assertEqual(RedditMeta(2, 2, 0), result.meta)
        self.assertEqual(
            RedditPost(
                id="abc123",
                subreddit="  测试社区  ",
                title="  A title\n第二行  ",
                content="正文 😀\nnext line",
                author="  OriginalAuthor  ",
                num_comments=2,
            ),
            result.post,
        )
        self.assertEqual(("root1", "reply2"), tuple(c.id for c in result.comments))
        self.assertEqual("abc123", result.comments[0].parent_id)
        self.assertEqual("root1", result.comments[1].parent_id)
        self.assertEqual(payload["comments"][0]["content"], result.comments[0].content)
        self.assertEqual(payload["comments"][0]["username"], result.comments[0].username)
        self.assertEqual(payload["comments"][0]["date"], result.comments[0].date)
        self.assertEqual((0, 1), tuple(c.depth for c in result.comments))

    def test_accepts_utf8_bom(self) -> None:
        result = parse_reddit_json(
            self.write_payload(valid_payload(), encoding="utf-8-sig")
        )
        self.assertEqual("abc123", result.post.id)

    def test_rejects_invalid_encoding_and_redacts_file_content(self) -> None:
        secret = "PRIVATE_AUTHOR_AND_CONTENT"
        self.path.write_bytes(b"\xff\xfe" + secret.encode("utf-16-le"))
        with self.assertRaises(RedditJsonError) as caught:
            parse_reddit_json(self.path)
        self.assertNotIn(secret, str(caught.exception))

    def test_rejects_malformed_json_and_redacts_file_content(self) -> None:
        secret = "PRIVATE_AUTHOR_AND_CONTENT"
        self.path.write_text('{"post": "' + secret, encoding="utf-8")
        with self.assertRaises(RedditJsonError) as caught:
            parse_reddit_json(self.path)
        self.assertNotIn(secret, str(caught.exception))

    def test_rejects_duplicate_keys_at_every_object_level(self) -> None:
        raw = json.dumps(valid_payload(), ensure_ascii=False)
        duplicates = {
            "root": raw.replace('"meta": {', '"meta": null, "meta": {', 1),
            "meta": raw.replace(
                '"completeness": "complete"',
                '"completeness": "complete", "completeness": "complete"',
                1,
            ),
            "post": raw.replace(
                '"id": "AbC123"', '"id": "other", "id": "AbC123"', 1
            ),
            "comment": raw.replace(
                '"username": "  用户一  "',
                '"username": "other", "username": "  用户一  "',
                1,
            ),
        }
        for level, duplicate_json in duplicates.items():
            with self.subTest(level=level):
                with self.assertRaisesRegex(
                    RedditJsonError, r"^invalid JSON: duplicate object key$"
                ):
                    parse_reddit_json(self.write_raw(duplicate_json))

    def test_rejects_nonstandard_json_numeric_constants(self) -> None:
        raw = json.dumps(valid_payload(), ensure_ascii=False)
        for constant in ("NaN", "Infinity", "-Infinity"):
            document = raw[:-1] + f', "extra": {constant}' + "}"
            with self.subTest(constant=constant):
                with self.assertRaisesRegex(
                    RedditJsonError,
                    r"^invalid JSON: non-standard numeric constant$",
                ):
                    parse_reddit_json(self.write_raw(document))

    def test_translates_huge_integer_decoder_value_error_without_leaking_source(
        self,
    ) -> None:
        huge_integer = "7" * 5000
        raw = json.dumps(valid_payload(), ensure_ascii=False)
        document = raw[:-1] + f', "extra": {huge_integer}' + "}"
        with self.assertRaisesRegex(
            RedditJsonError, r"^unable to read valid UTF-8 JSON export$"
        ) as caught:
            parse_reddit_json(self.write_raw(document))
        self.assertNotIn(huge_integer[:100], str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)

    def test_translates_deep_nesting_recursion_error_without_leaking_source(
        self,
    ) -> None:
        marker = "PRIVATE_DEEP_MARKER"
        nested = "[" * 5000 + json.dumps(marker) + "]" * 5000
        raw = json.dumps(valid_payload(), ensure_ascii=False)
        document = raw[:-1] + f', "extra": {nested}' + "}"
        with self.assertRaisesRegex(
            RedditJsonError, r"^unable to read valid UTF-8 JSON export$"
        ) as caught:
            parse_reddit_json(self.write_raw(document))
        self.assertNotIn(marker, str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)

    def test_requires_root_meta_and_post_objects_and_comments_array(self) -> None:
        cases: list[Any] = [
            [],
            {**valid_payload(), "meta": []},
            {**valid_payload(), "post": []},
            {**valid_payload(), "comments": {}},
        ]
        for payload in cases:
            with self.subTest(payload_type=type(payload).__name__):
                self.assert_invalid(payload)

    def test_requires_all_root_sections(self) -> None:
        for key in ("meta", "post", "comments"):
            payload = valid_payload()
            del payload[key]
            with self.subTest(key=key):
                self.assert_invalid(payload)

    def test_rejects_incomplete_or_missing_completeness(self) -> None:
        for value in (None, "", "Complete", "incomplete"):
            payload = valid_payload()
            if value is None:
                del payload["meta"]["completeness"]
            else:
                payload["meta"]["completeness"] = value
            with self.subTest(value=value):
                self.assert_invalid(payload)

    def test_meta_counts_are_required_exact_nonnegative_integers(self) -> None:
        for field in (
            "collectedCommentCount",
            "reportedByApi",
            "discrepancy",
            "failedMore",
        ):
            for value in (None, True, -1, 1.0, "1"):
                payload = valid_payload()
                if value is None:
                    del payload["meta"][field]
                else:
                    payload["meta"][field] = value
                with self.subTest(field=field, value=value):
                    self.assert_invalid(payload)

    def test_rejects_meta_count_and_discrepancy_mismatches(self) -> None:
        cases = [
            ("collectedCommentCount", 1),
            ("reportedByApi", 3),
            ("discrepancy", 1),
            ("failedMore", 1),
        ]
        for field, value in cases:
            payload = valid_payload()
            payload["meta"][field] = value
            with self.subTest(field=field):
                self.assert_invalid(payload)

    def test_accepts_only_defined_empty_failure_values(self) -> None:
        for field in ("failedNodes", "failedReasons", "failedDetails"):
            for empty in (None, "", [], {}):
                payload = valid_payload()
                payload["meta"][field] = empty
                with self.subTest(field=field, empty=repr(empty)):
                    parse_reddit_json(self.write_payload(payload))

            for nonempty in ("x", [1], {"error": "x"}, 0, False):
                payload = valid_payload()
                payload["meta"][field] = nonempty
                with self.subTest(field=field, nonempty=repr(nonempty)):
                    self.assert_invalid(payload)

    def test_requires_failure_fields(self) -> None:
        for field in ("failedMore", "failedNodes", "failedReasons", "failedDetails"):
            payload = valid_payload()
            del payload["meta"][field]
            with self.subTest(field=field):
                self.assert_invalid(payload)

    def test_requires_all_post_fields(self) -> None:
        for field in ("id", "subreddit", "title", "content", "author", "num_comments"):
            payload = valid_payload()
            del payload["post"][field]
            with self.subTest(field=field):
                self.assert_invalid(payload)

    def test_rejects_blank_or_non_string_post_text(self) -> None:
        for field in ("subreddit", "title", "content", "author"):
            for value in ("", " \t\r\n", None, 3):
                payload = valid_payload()
                payload["post"][field] = value
                with self.subTest(field=field, value=value):
                    self.assert_invalid(payload)

    def test_post_num_comments_is_exact_nonnegative_integer_and_matches_meta(self) -> None:
        for value in (True, -1, 2.0, "2", 1):
            payload = valid_payload()
            payload["post"]["num_comments"] = value
            with self.subTest(value=value):
                self.assert_invalid(payload)

    def test_requires_comment_objects_and_all_comment_fields(self) -> None:
        payload = valid_payload()
        payload["comments"][0] = []
        self.assert_invalid(payload)

        for field in (
            "id",
            "parent_id",
            "content",
            "depth",
            "username",
            "date",
            "created_utc",
        ):
            payload = valid_payload()
            del payload["comments"][0][field]
            with self.subTest(field=field):
                self.assert_invalid(payload)

    def test_rejects_blank_or_non_string_comment_text(self) -> None:
        for field in ("content", "username", "date"):
            for value in ("", " \t\r\n", None, 3):
                payload = valid_payload()
                payload["comments"][0][field] = value
                with self.subTest(field=field, value=value):
                    self.assert_invalid(payload)

    def test_comment_integers_are_exact_and_depth_is_nonnegative(self) -> None:
        for field, values in (
            ("depth", (True, -1, 0.0, "0")),
            ("created_utc", (True, 1.0, "1")),
        ):
            for value in values:
                payload = valid_payload()
                payload["comments"][0][field] = value
                with self.subTest(field=field, value=value):
                    self.assert_invalid(payload)

    def test_rejects_invalid_post_and_comment_ids(self) -> None:
        invalid_ids = (
            "",
            " ",
            "abc-def",
            "abc def",
            "abc%20def",
            "ＡＢＣ123",
            "t3_",
            "t3_a_b",
            "t1_ab-c",
        )
        locations = (
            ("post", "id"),
            ("comments", 0, "id"),
            ("comments", 0, "parent_id"),
        )
        for location in locations:
            for value in invalid_ids:
                payload = valid_payload()
                if location[0] == "post":
                    payload["post"]["id"] = value
                else:
                    payload["comments"][location[1]][location[2]] = value
                with self.subTest(location=location, value=value):
                    self.assert_invalid(payload)

    def test_rejects_fullname_prefixes_for_post_id(self) -> None:
        for value in ("t3_AbC123", "T3_AbC123", "t1_AbC123", "T1_AbC123"):
            payload = valid_payload()
            payload["post"]["id"] = value
            with self.subTest(value=value):
                self.assert_invalid(payload)

    def test_accepts_fullname_prefixes_for_comment_and_parent_ids(self) -> None:
        cases = [
            ("comments", 0, "id", "T3_Root1", "root1"),
            ("comments", 1, "id", "T1_Reply2", "reply2"),
            ("comments", 0, "parent_id", "T1_ABC123", "abc123"),
            ("comments", 1, "parent_id", "T3_ROOT1", "root1"),
        ]
        for section, index, field, value, expected in cases:
            payload = valid_payload()
            payload["comments"][index][field] = value
            with self.subTest(section=section, index=index, field=field, value=value):
                result = parse_reddit_json(self.write_payload(payload))
                actual = getattr(result.comments[index], field)
                self.assertEqual(expected, actual)

    def test_rejects_duplicate_comment_ids_after_case_and_prefix_normalization(self) -> None:
        payload = valid_payload()
        payload["comments"][1]["id"] = "t1_rOoT1"
        self.assert_invalid(payload)

    def test_rejects_missing_parent(self) -> None:
        payload = valid_payload()
        payload["comments"][1]["parent_id"] = "t1_missing"
        with self.assertRaisesRegex(RedditJsonError, r"^comment item 2 parent is missing$"):
            parse_reddit_json(self.write_payload(payload))

    def test_rejects_root_comment_with_wrong_parent(self) -> None:
        payload = valid_payload()
        payload["comments"][0]["parent_id"] = "t3_other"
        with self.assertRaisesRegex(
            RedditJsonError, r"^comment item 1 root parent does not match post$"
        ):
            parse_reddit_json(self.write_payload(payload))

    def test_rejects_parent_with_wrong_depth(self) -> None:
        payload = valid_payload()
        payload["comments"][1]["depth"] = 2
        with self.assertRaisesRegex(
            RedditJsonError, r"^comment item 2 parent depth is inconsistent$"
        ):
            parse_reddit_json(self.write_payload(payload))

    def test_accepts_parent_later_in_array_when_graph_is_valid(self) -> None:
        payload = valid_payload()
        payload["comments"] = list(reversed(payload["comments"]))
        result = parse_reddit_json(self.write_payload(payload))
        self.assertEqual(("reply2", "root1"), tuple(c.id for c in result.comments))

    def test_error_messages_never_embed_author_or_content_fields(self) -> None:
        payload = valid_payload()
        secret_author = "SECRET_AUTHOR_78431"
        secret_content = "SECRET_CONTENT_92517"
        payload["comments"][0]["username"] = secret_author
        payload["comments"][0]["content"] = secret_content
        payload["comments"][1]["parent_id"] = "t1_missing"
        with self.assertRaisesRegex(
            RedditJsonError, r"^comment item 2 parent is missing$"
        ) as caught:
            parse_reddit_json(self.write_payload(payload))
        message = str(caught.exception)
        self.assertNotIn(secret_author, message)
        self.assertNotIn(secret_content, message)


if __name__ == "__main__":
    unittest.main()
