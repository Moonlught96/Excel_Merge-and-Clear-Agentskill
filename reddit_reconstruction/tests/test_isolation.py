from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import reddit_reconstruction
from tools.output_path_safety import OutputPathConflictError
from tools import reconstruct_reddit_comments


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


class LegacyWrapperCompatibilityTests(unittest.TestCase):
    def test_reconstruct_wrapper_translates_exposed_output_path_conflict(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            input_path = directory / "input.json"
            input_path.write_text("{}", encoding="utf-8")

            with self.assertRaises(OutputPathConflictError):
                reconstruct_reddit_comments.ensure_output_paths_safe(
                    (input_path,),
                    (input_path,),
                    overwrite=False,
                )

    def test_reddit_reexport_wrappers_import_from_tools_directory(self) -> None:
        repo_root = Path(reddit_reconstruction.__file__).parent.parent
        tools_directory = repo_root / "tools"
        for module_name in (
            "reddit_json_export",
            "reddit_page_text",
            "reddit_json_text_merge",
        ):
            with self.subTest(module_name=module_name):
                completed = subprocess.run(
                    [sys.executable, "-c", f"import {module_name}"],
                    cwd=tools_directory,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(0, completed.returncode, completed.stderr)
