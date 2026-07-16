from __future__ import annotations

import re
import unittest
from pathlib import Path


class SkillMetadataTest(unittest.TestCase):
    def test_openai_yaml_has_standard_interface_metadata(self) -> None:
        metadata = Path(
            "skills/product-user-comment-data-merge-cleaning/agents/openai.yaml"
        ).read_text(
            encoding="utf-8"
        )

        display_match = re.search(r'^  display_name: "([^"]+)"$', metadata, re.MULTILINE)
        description_match = re.search(r'^  short_description: "([^"]+)"$', metadata, re.MULTILINE)
        prompt_match = re.search(r'^  default_prompt: "([^"]+)"$', metadata, re.MULTILINE)

        self.assertIsNotNone(display_match)
        self.assertIsNotNone(description_match)
        self.assertIsNotNone(prompt_match)
        self.assertEqual("产品用户评论数据合并与清洗 Skill", display_match.group(1))
        self.assertEqual(
            "为抓取的大量用户评论数据进行文档合并、标准化和清洗，并输出 XLSX 与 CSV",
            description_match.group(1),
        )
        self.assertGreaterEqual(len(description_match.group(1)), 25)
        self.assertLessEqual(len(description_match.group(1)), 64)
        self.assertIn("$product-user-comment-data-merge-cleaning", prompt_match.group(1))
        self.assertIn("allow_implicit_invocation: true", metadata)


if __name__ == "__main__":
    unittest.main()
