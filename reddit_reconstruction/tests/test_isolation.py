from __future__ import annotations

from pathlib import Path
import unittest

import reddit_reconstruction


class RedditPackageIsolationTests(unittest.TestCase):
    def test_primary_package_has_no_tools_or_skills_imports(self) -> None:
        source_root = Path(reddit_reconstruction.__file__).parent
        source = "\n".join(
            item.read_text(encoding="utf-8")
            for item in source_root.glob("*.py")
        )
        self.assertNotIn("from tools.", source)
        self.assertNotIn("import tools.", source)
        self.assertNotIn("from skills.", source)
        self.assertNotIn("import skills.", source)
