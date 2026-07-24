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
    select_identity_header,
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

    def test_existing_account_id_hash_vector_is_unchanged(self) -> None:
        historical_context = replace(
            self.context,
            project_id="project-screenbar",
            key_version=1,
            secret_key=b"k" * 32,
        )

        self.assertEqual(
            "72bd4fc68258026ac244e1cfbb758e603455defca92af91c577ed9f9b23082c9",
            hash_user_id(
                "UC-secret-user",
                "YouTube",
                historical_context,
                self.config,
            ),
        )

    def test_display_name_hash_uses_length_prefixed_identity_type(self) -> None:
        parts = (
            self.config.algorithm_version,
            self.context.project_id,
            str(self.context.key_version),
            "youtube",
            "display_name",
            "same-user",
        )
        message = b"".join(
            struct.pack(">I", len(part.encode("utf-8"))) + part.encode("utf-8")
            for part in parts
        )
        expected = hmac.new(
            self.context.secret_key,
            message,
            hashlib.sha256,
        ).hexdigest()

        self.assertEqual(
            expected,
            hash_id_pseudonymizer.hash_display_name(
                "same-user",
                "YouTube",
                self.context,
                self.config,
            ),
        )

    def test_same_display_name_is_stable_across_source_header_names(self) -> None:
        username = hash_id_pseudonymizer.SelectedIdentityHeader(
            source_header="username",
            source_column=1,
            identity_type="display_name",
        )
        nickname = hash_id_pseudonymizer.SelectedIdentityHeader(
            source_header="nickname",
            source_column=2,
            identity_type="display_name",
        )

        self.assertEqual(
            hash_id_pseudonymizer.hash_selected_identity(
                "same-user", username, "TikTok", self.context, self.config
            ),
            hash_id_pseudonymizer.hash_selected_identity(
                "same-user", nickname, "TikTok", self.context, self.config
            ),
        )

    def test_display_name_hash_is_isolated_from_account_id_hash(self) -> None:
        self.assertNotEqual(
            hash_id_pseudonymizer.hash_display_name(
                "same-user", "YouTube", self.context, self.config
            ),
            hash_user_id("same-user", "YouTube", self.context, self.config),
        )

    def test_display_name_hash_differs_across_platform_and_project(self) -> None:
        display_hash = hash_id_pseudonymizer.hash_display_name(
            "same-user", "YouTube", self.context, self.config
        )
        other_project = replace(
            self.context,
            project_id="22222222-2222-2222-2222-222222222222",
        )

        self.assertNotEqual(
            display_hash,
            hash_id_pseudonymizer.hash_display_name(
                "same-user", "bilibili", self.context, self.config
            ),
        )
        self.assertNotEqual(
            display_hash,
            hash_id_pseudonymizer.hash_display_name(
                "same-user", "YouTube", other_project, self.config
            ),
        )

    def test_display_name_only_trims_outer_whitespace(self) -> None:
        hash_display_name = hash_id_pseudonymizer.hash_display_name

        self.assertEqual(
            hash_display_name("  Same User  ", "bilibili", self.context, self.config),
            hash_display_name("Same User", "bilibili", self.context, self.config),
        )
        self.assertNotEqual(
            hash_display_name("Same User", "bilibili", self.context, self.config),
            hash_display_name("same User", "bilibili", self.context, self.config),
        )
        self.assertNotEqual(
            hash_display_name("Same User", "bilibili", self.context, self.config),
            hash_display_name("Same  User", "bilibili", self.context, self.config),
        )

    def test_blank_display_names_return_none(self) -> None:
        for value in (None, "", "  \t\r\n"):
            with self.subTest(value=value):
                self.assertIsNone(
                    hash_id_pseudonymizer.hash_display_name(
                        value, "YouTube", self.context, self.config
                    )
                )

    def test_invalid_display_names_fail_without_echoing_raw_value(self) -> None:
        invalid_values = (
            "=private-display-name",
            ["private-display-name"],
            12.5,
        )

        for value in invalid_values:
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises(InvalidUserIdError) as caught:
                    hash_id_pseudonymizer.hash_display_name(
                        value, "YouTube", self.context, self.config
                    )
                self.assertNotIn("private-display-name", str(caught.exception))
                self.assertNotIn("12.5", str(caught.exception))

    def test_display_name_hash_validates_context_without_exposing_raw_value(self) -> None:
        invalid_context = replace(self.context, secret_key=b"short")

        with self.assertRaises(
            hash_id_pseudonymizer.InvalidHashProjectContextError
        ) as caught:
            hash_id_pseudonymizer.hash_display_name(
                "private-display-name",
                "YouTube",
                invalid_context,
                self.config,
            )

        self.assertNotIn("private-display-name", str(caught.exception))

    def test_hash_selected_identity_dispatches_both_identity_types(self) -> None:
        account_id = hash_id_pseudonymizer.SelectedIdentityHeader(
            source_header="author_channel_id",
            source_column=1,
            identity_type="account_id",
        )
        display_name = hash_id_pseudonymizer.SelectedIdentityHeader(
            source_header="author",
            source_column=2,
            identity_type="display_name",
        )

        self.assertEqual(
            hash_user_id("same-user", "YouTube", self.context, self.config),
            hash_id_pseudonymizer.hash_selected_identity(
                "same-user", account_id, "YouTube", self.context, self.config
            ),
        )
        self.assertEqual(
            hash_id_pseudonymizer.hash_display_name(
                "same-user", "YouTube", self.context, self.config
            ),
            hash_id_pseudonymizer.hash_selected_identity(
                "same-user", display_name, "YouTube", self.context, self.config
            ),
        )

    def test_hash_selected_identity_rejects_unsupported_type_without_raw_value(self) -> None:
        unsupported = hash_id_pseudonymizer.SelectedIdentityHeader(
            source_header="private-source-header",
            source_column=1,
            identity_type="unsupported",  # type: ignore[arg-type]
        )

        with self.assertRaises(HashIdConfigError) as caught:
            hash_id_pseudonymizer.hash_selected_identity(
                "private-display-name",
                unsupported,
                "YouTube",
                self.context,
                self.config,
            )

        self.assertNotIn("private-display-name", str(caught.exception))
        self.assertNotIn("private-source-header", str(caught.exception))

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
            "Twitter": "twitter",
            "twitter": "twitter",
            "X": "twitter",
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
            ("schema_version", 3),
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

    def test_config_requires_schema_version_2_and_rejects_v1_explicitly(self) -> None:
        self.assertEqual(2, self.config.schema_version)
        self.assertEqual("bazhuayu-hash-id-v1", self.config.algorithm_version)

        source_path = PROJECT_ROOT / "config" / "hash-id.json"
        old_config = json.loads(source_path.read_text(encoding="utf-8"))
        old_config["schema_version"] = 1
        output_dir = PROJECT_ROOT / ".tmp-tests" / "hash-id-schema-v1-rejection"
        output_dir.mkdir(parents=True, exist_ok=True)
        config_path = output_dir / "schema-v1.json"
        config_path.write_text(
            json.dumps(old_config, ensure_ascii=False),
            encoding="utf-8",
        )

        with self.assertRaisesRegex(
            HashIdConfigError,
            "schema_version must be 2",
        ):
            load_hash_id_config(config_path)

    def test_config_loads_exact_display_name_header_priorities(self) -> None:
        expected = {
            "youtube": ("author", "author_name"),
            "xiaohongshu": ("用户名称",),
            "bilibili": ("username",),
            "tiktok": ("用户名", "昵称"),
            "taobao": ("用户名称", "用户名"),
            "jd": ("用户名",),
            "amazon": ("名称",),
            "rakuten": ("乐天市场昵称",),
            "twitter": ("Twitter昵称",),
        }

        self.assertEqual(
            expected,
            {
                platform.namespace: platform.display_name_headers
                for platform in self.config.platforms
            },
        )

    def test_config_rejects_invalid_display_name_headers(self) -> None:
        source_path = PROJECT_ROOT / "config" / "hash-id.json"
        base_config = json.loads(source_path.read_text(encoding="utf-8"))
        output_dir = PROJECT_ROOT / ".tmp-tests" / "hash-id-display-name-validation"
        output_dir.mkdir(parents=True, exist_ok=True)
        invalid_values = (
            ("missing", None),
            ("not-list", "author"),
            ("non-string", [123]),
            ("blank", [" "]),
            ("duplicate", ["author", "author"]),
            ("overlap", ["author_channel_id"]),
        )

        for case_name, invalid_value in invalid_values:
            with self.subTest(case_name=case_name):
                invalid_config = json.loads(json.dumps(base_config))
                youtube = invalid_config["platforms"][0]
                if case_name == "missing":
                    youtube.pop("display_name_headers", None)
                else:
                    youtube["display_name_headers"] = invalid_value
                config_path = output_dir / f"{case_name}.json"
                config_path.write_text(
                    json.dumps(invalid_config, ensure_ascii=False),
                    encoding="utf-8",
                )

                with self.assertRaises(HashIdConfigError):
                    load_hash_id_config(config_path)

    def test_config_rejects_blank_and_duplicate_user_id_headers(self) -> None:
        source_path = PROJECT_ROOT / "config" / "hash-id.json"
        base_config = json.loads(source_path.read_text(encoding="utf-8"))
        output_dir = PROJECT_ROOT / ".tmp-tests" / "hash-id-user-id-validation"
        output_dir.mkdir(parents=True, exist_ok=True)
        invalid_values = (
            ("blank", [" "]),
            ("duplicate", ["author_channel_id", "author_channel_id"]),
        )

        for case_name, invalid_value in invalid_values:
            with self.subTest(case_name=case_name):
                invalid_config = json.loads(json.dumps(base_config))
                invalid_config["platforms"][0]["user_id_headers"] = invalid_value
                config_path = output_dir / f"{case_name}.json"
                config_path.write_text(
                    json.dumps(invalid_config, ensure_ascii=False),
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
        self.assertEqual("account_id", selected.identity_type)

    def test_twitter_uses_only_registered_account_id_and_display_name_headers(self) -> None:
        account_header = select_user_id_header(
            ["Twitter昵称", "Twitter用户ID"],
            "X",
            self.config,
        )
        display_header = select_identity_header(
            ["Twitter昵称"],
            "twitter",
            self.config,
        )

        self.assertIsNotNone(account_header)
        assert account_header is not None
        self.assertEqual("Twitter用户ID", account_header.source_header)
        self.assertEqual("account_id", account_header.identity_type)
        self.assertIsNotNone(display_header)
        assert display_header is not None
        self.assertEqual("Twitter昵称", display_header.source_header)
        self.assertEqual("display_name", display_header.identity_type)

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

        for platform in ("YouTube", "小红书", "B站", "TikTok", "淘宝", "京东", "乐天市场"):
            with self.subTest(platform=platform):
                self.assertIsNone(
                    select_user_id_header(forbidden_headers, platform, self.config)
                )

    def test_platforms_without_verified_user_id_headers_select_nothing(self) -> None:
        for platform in ("B站", "TikTok", "淘宝", "京东", "乐天市场"):
            with self.subTest(platform=platform):
                self.assertIsNone(
                    select_user_id_header(
                        ["author_channel_id", "用户ID", "id"],
                        platform,
                        self.config,
                    )
                )

    def test_bilibili_username_is_selected_as_display_name(self) -> None:
        selected = select_identity_header(
            ["评论内容", "点赞数", "username"],
            "B站",
            self.config,
        )

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("username", selected.source_header)
        self.assertEqual(3, selected.source_column)
        self.assertEqual("display_name", selected.identity_type)

    def test_youtube_account_id_beats_earlier_display_name(self) -> None:
        selected = select_identity_header(
            ["author", "评论内容", "Author Channel ID"],
            "YouTube",
            self.config,
        )

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("Author Channel ID", selected.source_header)
        self.assertEqual(3, selected.source_column)
        self.assertEqual("account_id", selected.identity_type)

    def test_youtube_author_fallback_is_selected_when_account_id_is_absent(self) -> None:
        selected = select_identity_header(
            ["评论内容", "author", "点赞数"],
            "YouTube",
            self.config,
        )

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("author", selected.source_header)
        self.assertEqual(2, selected.source_column)
        self.assertEqual("display_name", selected.identity_type)

    def test_xiaohongshu_user_name_fallback_is_selected(self) -> None:
        selected = select_identity_header(
            ["评论内容", "用户名称"],
            "小红书",
            self.config,
        )

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("用户名称", selected.source_header)
        self.assertEqual(2, selected.source_column)
        self.assertEqual("display_name", selected.identity_type)

    def test_taobao_user_name_has_priority_over_username(self) -> None:
        selected = select_identity_header(
            ["用户名", "评论内容", "用户名称"],
            "淘宝",
            self.config,
        )

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("用户名称", selected.source_header)
        self.assertEqual(3, selected.source_column)
        self.assertEqual("display_name", selected.identity_type)

    def test_jd_username_fallback_is_selected(self) -> None:
        selected = select_identity_header(
            ["评论内容", "用户名"],
            "京东",
            self.config,
        )

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("用户名", selected.source_header)
        self.assertEqual(2, selected.source_column)
        self.assertEqual("display_name", selected.identity_type)

    def test_tiktok_display_name_priority_ignores_user_identity(self) -> None:
        selected = select_identity_header(
            ["用户身份", "昵称", "用户名"],
            "TikTok",
            self.config,
        )

        self.assertIsNotNone(selected)
        assert selected is not None
        self.assertEqual("用户名", selected.source_header)
        self.assertEqual(3, selected.source_column)
        self.assertEqual("display_name", selected.identity_type)

    def test_unapproved_identity_fields_select_nothing(self) -> None:
        unapproved_headers = [
            "用户身份",
            "comment_id",
            "parent_rpid",
            "profileUrl",
            "ip_location",
        ]

        for platform in ("YouTube", "小红书", "B站", "TikTok", "淘宝", "京东", "乐天市场"):
            with self.subTest(platform=platform):
                self.assertIsNone(
                    select_identity_header(unapproved_headers, platform, self.config)
                )


if __name__ == "__main__":
    unittest.main()
