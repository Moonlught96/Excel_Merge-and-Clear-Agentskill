from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import reddit_reconstruction


def _production_module_paths(source_root: Path) -> tuple[Path, ...]:
    return tuple(
        source_path
        for source_path in source_root.rglob("*.py")
        if "tests" not in source_path.relative_to(source_root).parts
    )


def _imported_modules(source_path: Path) -> tuple[str, ...]:
    parsed = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
    imported_modules: list[str] = []
    for node in ast.walk(parsed):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.append(node.module)
        elif isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
    return tuple(imported_modules)


class RedditPackageIsolationTests(unittest.TestCase):
    def test_primary_package_has_no_tools_or_skills_imports(self) -> None:
        source_root = Path(reddit_reconstruction.__file__).parent
        for source_path in _production_module_paths(source_root):
            with self.subTest(source_path=source_path.relative_to(source_root)):
                imported_modules = _imported_modules(source_path)
                self.assertFalse(
                    any(module == "tools" or module.startswith("tools.") for module in imported_modules),
                )
                self.assertFalse(
                    any(module == "skills" or module.startswith("skills.") for module in imported_modules),
                )

    def test_primary_package_does_not_reference_generic_cleaning_workflow(
        self,
    ) -> None:
        source_root = Path(reddit_reconstruction.__file__).parent
        for source_path in _production_module_paths(source_root):
            with self.subTest(source_path=source_path.name):
                source = source_path.read_text(encoding="utf-8")
                self.assertNotIn("product-user-comment-data-merge-cleaning", source)
                self.assertNotIn("clean_excel_comments", source)
                self.assertNotIn("standardize_excel_headers", source)

    def test_production_module_paths_recurse_and_exclude_tests(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            source_root = Path(temporary_directory)
            (source_root / "nested").mkdir()
            (source_root / "tests").mkdir()
            (source_root / "root.py").write_text("", encoding="utf-8")
            (source_root / "nested" / "module.py").write_text("", encoding="utf-8")
            (source_root / "tests" / "test_module.py").write_text("", encoding="utf-8")

            modules = _production_module_paths(source_root)

        self.assertEqual(
            {Path("root.py"), Path("nested/module.py")},
            {module.relative_to(source_root) for module in modules},
        )


class LegacyWrapperCompatibilityTests(unittest.TestCase):
    legacy_tools_directory = Path(__file__).resolve().parents[2] / "tools"

    @unittest.skipUnless(
        legacy_tools_directory.is_dir(),
        "legacy wrapper tests require the optional repository tools directory",
    )
    def test_reconstruct_wrapper_translates_exposed_output_path_conflict(
        self,
    ) -> None:
        from tools import reconstruct_reddit_comments
        from tools.output_path_safety import OutputPathConflictError

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

    @unittest.skipUnless(
        legacy_tools_directory.is_dir(),
        "legacy wrapper tests require the optional repository tools directory",
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
