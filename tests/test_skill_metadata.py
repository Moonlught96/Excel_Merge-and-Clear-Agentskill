from __future__ import annotations

import re
import unittest
from pathlib import Path


class SkillMetadataTest(unittest.TestCase):
    def test_openai_yaml_has_standard_interface_metadata(self) -> None:
        metadata = Path("skills/bazhuayu-excel-cleaning/agents/openai.yaml").read_text(
            encoding="utf-8"
        )

        display_match = re.search(r'^  display_name: "([^"]+)"$', metadata, re.MULTILINE)
        description_match = re.search(r'^  short_description: "([^"]+)"$', metadata, re.MULTILINE)
        prompt_match = re.search(r'^  default_prompt: "([^"]+)"$', metadata, re.MULTILINE)

        self.assertIsNotNone(display_match)
        self.assertIsNotNone(description_match)
        self.assertIsNotNone(prompt_match)
        self.assertGreaterEqual(len(description_match.group(1)), 25)
        self.assertLessEqual(len(description_match.group(1)), 64)
        self.assertIn("$bazhuayu-excel-cleaning", prompt_match.group(1))
        self.assertIn("allow_implicit_invocation: true", metadata)


if __name__ == "__main__":
    unittest.main()
