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


if __name__ == "__main__":
    unittest.main()
