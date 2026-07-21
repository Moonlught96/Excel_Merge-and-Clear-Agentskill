from __future__ import annotations

import json
import unittest
from pathlib import Path


SKILL_ROOT = Path("skills/product-user-comment-data-merge-cleaning")


class SkillReferenceCoverageTest(unittest.TestCase):
    def test_header_config_is_fully_documented_in_references(self) -> None:
        config = json.loads(
            (SKILL_ROOT / "config" / "header-standardizer.json").read_text(encoding="utf-8")
        )
        reference = (SKILL_ROOT / "references" / "header-standardization.md").read_text(
            encoding="utf-8"
        )

        for output_column in config["output_columns"]:
            self.assertIn(f"`{output_column['header']}`", reference)
            for alias in output_column["aliases"]:
                self.assertIn(f"`{alias}`", reference, f"Undocumented header alias: {alias}")

        for header in config["drop_headers"]:
            self.assertIn(f"`{header}`", reference, f"Undocumented dropped header: {header}")

    def test_hash_identity_config_is_fully_documented_in_references(self) -> None:
        config = json.loads(
            (SKILL_ROOT / "config" / "hash-id.json").read_text(encoding="utf-8")
        )
        reference_docs = {
            name: (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")
            for name in (
                "data-contract.md",
                "header-standardization.md",
                "tool-reference.md",
                "extension-policy.md",
            )
        }
        references = "\n".join(reference_docs.values())

        expected_account_id_headers = {
            "youtube": (
                "author_channel_id",
                "authorChannelId",
                "Author Channel ID",
            ),
            "xiaohongshu": ("用户ID",),
            "bilibili": (),
            "tiktok": (),
            "taobao": (),
            "jd": (),
        }

        expected_display_name_headers = {
            "youtube": ("author",),
            "xiaohongshu": ("用户名称",),
            "bilibili": ("username",),
            "tiktok": ("用户名", "昵称"),
            "taobao": ("用户名称", "用户名"),
            "jd": ("用户名",),
        }
        platforms = {platform["namespace"]: platform for platform in config["platforms"]}

        self.assertEqual(2, config["schema_version"])
        self.assertEqual("bazhuayu-hash-id-v1", config["algorithm_version"])
        self.assertEqual(set(expected_account_id_headers), set(platforms))
        self.assertEqual(set(expected_display_name_headers), set(platforms))
        for namespace, expected_headers in expected_account_id_headers.items():
            self.assertEqual(expected_headers, tuple(platforms[namespace]["user_id_headers"]))
        for namespace, expected_headers in expected_display_name_headers.items():
            self.assertEqual(
                expected_headers,
                tuple(platforms[namespace].get("display_name_headers", ())),
            )
        # Exact documentation assertions use complete platform/type mapping blocks.

        header_reference = reference_docs["header-standardization.md"]
        account_mapping_block = (
            "- Exact account-ID mappings:\n"
            "  - YouTube: `author_channel_id`, then `authorChannelId`, then `Author Channel ID`.\n"
            "  - 小红书: `用户ID`."
        )
        display_mapping_block = (
            "- Exact display-name fallback mappings:\n"
            "  - YouTube: `author`.\n"
            "  - 小红书: `用户名称`.\n"
            "  - B站: `username`.\n"
            "  - TikTok: `用户名`, then `昵称`; never `用户身份`.\n"
            "  - 淘宝: `用户名称`, then `用户名`.\n"
            "  - 京东: `用户名`."
        )
        self.assertIn(account_mapping_block, header_reference)
        self.assertIn(display_mapping_block, header_reference)

        for phrase in (
            "Stable account ID is selected first for the whole worksheet.",
            "Display-name fallback is allowed only when no registered account-ID column exists.",
            "weak pseudonymization, not legal anonymization",
            "nickname changes can split the same user",
            "different users with the same normalized name can merge",
            "platform-specific evidence",
        ):
            self.assertIn(phrase, references)

        self.assertNotIn("`用户身份` as a display-name", references)

    def test_display_name_normalization_is_exactly_documented(self) -> None:
        data_contract = (SKILL_ROOT / "references" / "data-contract.md").read_text(
            encoding="utf-8"
        )

        for statement in (
            "Display-name normalization trims outer whitespace only.",
            "It preserves case, internal whitespace, punctuation, and Unicode code points.",
            "Do not apply Unicode normalization, full-width/half-width conversion, traditional/simplified Chinese conversion, or fuzzy matching.",
        ):
            self.assertIn(statement, data_contract)

    def test_cleaner_config_content_rules_are_fully_documented_in_references(self) -> None:
        config = json.loads(
            (SKILL_ROOT / "config" / "comment-cleaner.json").read_text(encoding="utf-8")
        )
        reference = (SKILL_ROOT / "references" / "cleaning-rules.md").read_text(
            encoding="utf-8"
        )

        content_rules = (
            *config["delete_exact_texts"],
            *config["delete_contains_texts"],
            *config["delete_contains_case_insensitive_texts"],
            *config["subcomment_deduplicate_headers"],
        )
        for rule in content_rules:
            self.assertIn(rule, reference, f"Undocumented cleaner content rule: {rule}")

        numeric_rules = {
            "min_trimmed_length": "less than or equal to 7 characters",
            "non_chinese_max_short_words": "four or fewer words",
            "non_chinese_max_short_unspaced_chars": "four or fewer characters",
            "random_digit_min_length": "pure digit token length at least 9",
            "random_letter_min_length": "letter-only token length at least 10",
            "random_mixed_min_length": "mixed letter/digit token length at least 10",
            "subcomment_min_trimmed_length": "less than or equal to 5 characters",
        }
        for config_key, documented_rule in numeric_rules.items():
            self.assertIn(config_key, config)
            self.assertIn(documented_rule, reference)

        for language_isolation_rule in (
            "Fixed delete words are isolated by deterministic script group.",
            "Latin-script fixed words use complete lexical boundaries",
            "`TESTV`, `contest`, and `testing` do not",
            "A Han-only Japanese comment cannot be distinguished from Chinese without semantic inference",
        ):
            self.assertIn(language_isolation_rule, reference)

        data_contract = (SKILL_ROOT / "references" / "data-contract.md").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "CSV values beginning with `=` must remain text cells when written to XLSX",
            data_contract,
        )


if __name__ == "__main__":
    unittest.main()
