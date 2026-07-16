from __future__ import annotations

import hashlib
import hmac
import json
import struct
import unittest
from dataclasses import replace
from pathlib import Path

from tools import hash_id_pseudonymizer
from tools.hash_id_pseudonymizer import (
    HashIdConfigError,
    HashProjectContext,
    InvalidUserIdError,
    UnknownPlatformError,
    hash_user_id,
    load_hash_id_config,
    normalize_platform,
    normalize_raw_user_id,
    select_user_id_header,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class HashIdPseudonymizerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_hash_id_config(PROJECT_ROOT / "config" / "hash-id.json")
        self.context = HashProjectContext(
            project_id="11111111-1111-1111-1111-111111111111",
            project_name="ScreenBar十周年专案",
            key_version=1,
            key_fingerprint="test-fingerprint",
            secret_key=bytes.fromhex("11" * 32),
        )

    def test_same_project_platform_and_id_produce_same_full_hash(self) -> None:
        first = hash_user_id("UC001", "YouTube", self.context, self.config)
        second = hash_user_id("UC001", "youtube", self.context, self.config)

        self.assertEqual(first, second)
        self.assertRegex(first, r"^[0-9a-f]{64}$")

    def test_hash_uses_length_prefixed_algorithm_project_platform_and_id(self) -> None:
        parts = (
            self.config.algorithm_version,
            self.context.project_id,
            str(self.context.key_version),
            "youtube",
            "UC001",
        )
        message = b"".join(
            struct.pack(">I", len(part.encode("utf-8"))) + part.encode("utf-8")
            for part in parts
        )
        expected = hmac.new(self.context.secret_key, message, hashlib.sha256).hexdigest()

        self.assertEqual(
            expected,
            hash_user_id("UC001", "YouTube", self.context, self.config),
        )

    def test_different_projects_produce_different_hashes(self) -> None:
        other_project = replace(
            self.context,
            project_id="22222222-2222-2222-2222-222222222222",
        )

        self.assertNotEqual(
            hash_user_id("00123", "YouTube", self.context, self.config),
            hash_user_id("00123", "YouTube", other_project, self.config),
        )

    def test_context_repr_does_not_expose_secret_key(self) -> None:
        context_repr = repr(self.context)

        self.assertNotIn("secret_key", context_repr)
        self.assertNotIn(repr(self.context.secret_key), context_repr)
        self.assertNotIn(self.context.secret_key.hex(), context_repr)

    def test_key_version_isolates_hashes(self) -> None:
        other_key_version = replace(self.context, key_version=2)

        self.assertNotEqual(
            hash_user_id("UC001", "YouTube", self.context, self.config),
            hash_user_id("UC001", "YouTube", other_key_version, self.config),
        )

    def test_invalid_project_contexts_fail_without_leaking_secret_key(self) -> None:
        invalid_contexts = (
            replace(self.context, project_id=" \t "),
            replace(self.context, secret_key=b"private-key"),
            replace(self.context, secret_key=b"x" * 33),
            replace(self.context, secret_key=bytearray(b"y" * 32)),
            replace(self.context, key_version=0),
            replace(self.context, key_version=-1),
            replace(self.context, key_version=True),
            replace(self.context, key_version=1.0),
        )

        for context in invalid_contexts:
            with self.subTest(context_field_types=(type(context.secret_key), type(context.key_version))):
                with self.assertRaises(
                    hash_id_pseudonymizer.InvalidHashProjectContextError
                ) as caught:
                    hash_user_id("UC001", "YouTube", context, self.config)
                error_text = str(caught.exception)
                self.assertNotIn(repr(context.secret_key), error_text)
                if isinstance(context.secret_key, bytes):
                    self.assertNotIn(context.secret_key.hex(), error_text)

    def test_different_platforms_produce_different_hashes(self) -> None:
        self.assertNotEqual(
            hash_user_id("00123", "YouTube", self.context, self.config),
            hash_user_id("00123", "小红书", self.context, self.config),
        )

    def test_string_normalization_only_trims_outer_whitespace(self) -> None:
        self.assertEqual("001 AbC", normalize_raw_user_id("  001 AbC\t"))
        self.assertNotEqual(
            hash_user_id("001AbC", "YouTube", self.context, self.config),
            hash_user_id("001abc", "YouTube", self.context, self.config),
        )
        self.assertNotEqual(
            hash_user_id("00123", "YouTube", self.context, self.config),
            hash_user_id("123", "YouTube", self.context, self.config),
        )

    def test_integer_and_integral_float_share_canonical_form(self) -> None:
        self.assertEqual("123", normalize_raw_user_id(123))
        self.assertEqual("123", normalize_raw_user_id(123.0))
        self.assertEqual("-12", normalize_raw_user_id(-12.0))
        self.assertEqual(
            hash_user_id(123, "YouTube", self.context, self.config),
            hash_user_id(123.0, "YouTube", self.context, self.config),
        )

    def test_none_and_blank_values_return_none(self) -> None:
        for value in (None, "", "  \t\r\n"):
            with self.subTest(value=value):
                self.assertIsNone(normalize_raw_user_id(value))
                self.assertIsNone(
                    hash_user_id(value, "YouTube", self.context, self.config)
                )

    def test_invalid_values_fail_without_echoing_raw_value(self) -> None:
        for value in (True, False, 12.5, float("inf"), "=A1", " #REF! "):
            with self.subTest(value=type(value).__name__):
                with self.assertRaises(InvalidUserIdError) as caught:
                    normalize_raw_user_id(value)
                self.assertNotIn(str(value).strip(), str(caught.exception))

    def test_unsupported_value_type_fails_without_echoing_raw_value(self) -> None:
        value = ["private-user-id"]

        with self.assertRaises(InvalidUserIdError) as caught:
            normalize_raw_user_id(value)

        self.assertNotIn("private-user-id", str(caught.exception))

    def test_platform_aliases_normalize_to_fixed_namespaces(self) -> None:
        expected = {
            "YouTube": "youtube",
            "YouTube Shorts": "youtube",
            "youtube": "youtube",
            "yt-comments": "youtube",
            "小红书": "xiaohongshu",
            "B站": "bilibili",
            "哔哩哔哩": "bilibili",
            "bilibili": "bilibili",
            "TikTok": "tiktok",
            "TTCommentExporter": "tiktok",
            "淘宝": "taobao",
            "京东": "jd",
        }

        for alias, namespace in expected.items():
            with self.subTest(alias=alias):
                self.assertEqual(namespace, normalize_platform(alias, self.config))

    def test_unregistered_platform_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(UnknownPlatformError, "not registered"):
            normalize_platform("微博", self.config)


    def test_config_rejects_unsupported_schema_and_algorithm_versions(self) -> None:
        source_path = PROJECT_ROOT / "config" / "hash-id.json"
        base_config = json.loads(source_path.read_text(encoding="utf-8"))
        output_dir = PROJECT_ROOT / ".tmp-tests" / "hash-id-config-validation"
        output_dir.mkdir(parents=True, exist_ok=True)
        invalid_values = (
            ("schema_version", 2),
            ("schema_version", True),
            ("algorithm_version", "bazhuayu-hash-id-v2"),
            ("algorithm_version", ""),
        )

        for field_name, invalid_value in invalid_values:
            with self.subTest(field_name=field_name, invalid_value=invalid_value):
                invalid_config = dict(base_config)
                invalid_config[field_name] = invalid_value
                config_path = output_dir / f"{field_name}-{type(invalid_value).__name__}.json"
                config_path.write_text(
                    json.dumps(invalid_config, ensure_ascii=True),
                    encoding="utf-8",
                )

                with self.assertRaises(HashIdConfigError):
                    load_hash_id_config(config_path)
    def test_youtube_header_selection_uses_only_verified_aliases(self) -> None:
        headers = ["评论内容", "authorChannelId", "点赞数"]

        selected = select_user_id_header(headers, "YouTube Shorts", self.config)

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("authorChannelId", selected.source_header)
        self.assertEqual(2, selected.source_column)

    def test_each_verified_youtube_header_can_be_selected(self) -> None:
        for user_id_header in (
            "author_channel_id",
            "authorChannelId",
            "Author Channel ID",
        ):
            with self.subTest(user_id_header=user_id_header):
                selected = select_user_id_header(
                    [user_id_header],
                    "YouTube Shorts",
                    self.config,
                )

                self.assertIsNotNone(selected)
                assert selected is not None
                self.assertEqual(user_id_header, selected.source_header)
                self.assertEqual(1, selected.source_column)

    def test_multiple_youtube_headers_use_configured_priority(self) -> None:
        selected = select_user_id_header(
            ["Author Channel ID", "authorChannelId", "author_channel_id"],
            "YouTube",
            self.config,
        )

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("author_channel_id", selected.source_header)
        self.assertEqual(3, selected.source_column)

    def test_platform_specific_headers_do_not_cross_match(self) -> None:
        self.assertIsNone(
            select_user_id_header(["\u7528\u6237ID"], "YouTube", self.config)
        )
        self.assertIsNone(
            select_user_id_header(["author_channel_id"], "\u5c0f\u7ea2\u4e66", self.config)
        )

    def test_xiaohongshu_header_selection_uses_verified_user_id(self) -> None:
        selected = select_user_id_header(
            ["评论内容", "用户ID", "昵称"],
            "小红书",
            self.config,
        )

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("用户ID", selected.source_header)
        self.assertEqual(2, selected.source_column)

    def test_unconfirmed_identity_and_comment_fields_are_never_selected(self) -> None:
        forbidden_headers = [
            "用户身份",
            "用户名",
            "昵称",
            "id",
            "评论ID",
            "rpid",
            "parent_rpid",
            "reply_to",
            "youtube_comment_id",
        ]

        for platform in ("YouTube", "小红书", "B站", "TikTok", "淘宝", "京东"):
            with self.subTest(platform=platform):
                self.assertIsNone(
                    select_user_id_header(forbidden_headers, platform, self.config)
                )

    def test_platforms_without_verified_user_id_headers_select_nothing(self) -> None:
        for platform in ("B站", "TikTok", "淘宝", "京东"):
            with self.subTest(platform=platform):
                self.assertIsNone(
                    select_user_id_header(
                        ["author_channel_id", "用户ID", "id"],
                        platform,
                        self.config,
                    )
                )


if __name__ == "__main__":
    unittest.main()
