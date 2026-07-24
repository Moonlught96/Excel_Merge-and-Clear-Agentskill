from __future__ import annotations

import shutil
import subprocess
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SKILL_NAME = "product-user-comment-data-merge-cleaning"
SKILL_ROOT = PROJECT_ROOT / "skills" / SKILL_NAME
CLI_SCRIPTS = (
    "audit_standardized_comments.py",
    "cleanup_intermediate_outputs.py",
    "clean_excel_comments.py",
    "compare_cleaned_workbooks.py",
    "filter_comments_by_keywords.py",
    "merge_excel_workbooks.py",
    "output_file_naming.py",
    "preprocess_platform_comments.py",
    "standardize_excel_headers.py",
    "strip_bilibili_reply_prefixes.py",
)


class SkillEntrypointsTest(unittest.TestCase):
    def test_all_cli_entrypoints_start_from_an_isolated_skill_copy(self) -> None:
        temp_root = PROJECT_ROOT / ".tmp-tests" / "standalone-entrypoints"
        if temp_root.exists():
            shutil.rmtree(temp_root)
        copied_skill = temp_root / SKILL_NAME
        copied_skill.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SKILL_ROOT, copied_skill)

        for script_name in CLI_SCRIPTS:
            result = subprocess.run(
                [sys.executable, str(copied_skill / "scripts" / script_name), "--help"],
                cwd=temp_root,
                capture_output=True,
            )
            self.assertEqual(
                0,
                result.returncode,
                f"Standalone entrypoint failed: {script_name}\n{result.stderr!r}",
            )

        shutil.rmtree(temp_root)


if __name__ == "__main__":
    unittest.main()
