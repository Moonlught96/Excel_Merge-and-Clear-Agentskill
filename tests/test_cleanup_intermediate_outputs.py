from __future__ import annotations

import json
import unittest
from pathlib import Path

from tools.cleanup_intermediate_outputs import (
    ProtectedOutputError,
    cleanup_intermediate_outputs,
)


class CleanupIntermediateOutputsTest(unittest.TestCase):
    def test_deletes_only_declared_intermediate_files_and_keeps_cleaned_outputs(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-cleanup-intermediate-outputs"
        tmp.mkdir(parents=True, exist_ok=True)

        merged = tmp / "20260708_product_source_合并总表.xlsx"
        merged_summary = tmp / "20260708_product_source_合并总表.summary.json"
        prefix_stripped = tmp / "20260708_product_source_合并总表_回复前缀已清理.xlsx"
        standardized = tmp / "20260708_product_source_标准化总表.xlsx"
        standardized_summary = tmp / "20260708_product_source_标准化总表.standardized.summary.json"
        cleaned_xlsx = tmp / "20260708_product_source_清洗后总表.xlsx"
        cleaned_csv = tmp / "20260708_product_source_清洗后总表.csv"
        cleaned_deletions = tmp / "20260708_product_source_清洗后总表.deletions.csv"
        cleaned_summary = tmp / "20260708_product_source_清洗后总表.summary.json"

        for path in [
            merged,
            merged_summary,
            prefix_stripped,
            standardized,
            standardized_summary,
            cleaned_xlsx,
            cleaned_csv,
            cleaned_deletions,
            cleaned_summary,
        ]:
            path.write_text(path.name, encoding="utf-8")

        deleted_paths: list[Path] = []
        result = cleanup_intermediate_outputs(
            intermediate_paths=[
                merged,
                merged_summary,
                prefix_stripped,
                standardized,
                standardized_summary,
                cleaned_deletions,
                cleaned_summary,
            ],
            protected_paths=[cleaned_xlsx, cleaned_csv],
            summary_path=tmp / "cleanup.summary.json",
            delete_file=deleted_paths.append,
        )

        self.assertEqual(7, result.files_deleted)
        self.assertEqual(0, result.files_missing)
        self.assertEqual(
            [
                path.resolve()
                for path in [
                    merged,
                    merged_summary,
                    prefix_stripped,
                    standardized,
                    standardized_summary,
                    cleaned_deletions,
                    cleaned_summary,
                ]
            ],
            deleted_paths,
        )
        self.assertTrue(cleaned_xlsx.exists())
        self.assertTrue(cleaned_csv.exists())

        summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
        self.assertEqual(7, len(summary["deleted_files"]))
        self.assertEqual([str(cleaned_xlsx.resolve()), str(cleaned_csv.resolve())], summary["protected_files"])

    def test_refuses_to_delete_protected_cleaned_output(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-cleanup-protected-output"
        tmp.mkdir(parents=True, exist_ok=True)

        cleaned_xlsx = tmp / "20260708_product_source_清洗后总表.xlsx"
        cleaned_xlsx.write_text("cleaned", encoding="utf-8")

        with self.assertRaisesRegex(ProtectedOutputError, "protected output"):
            cleanup_intermediate_outputs(
                intermediate_paths=[cleaned_xlsx],
                protected_paths=[cleaned_xlsx],
                summary_path=tmp / "cleanup.summary.json",
            )

        self.assertTrue(cleaned_xlsx.exists())


if __name__ == "__main__":
    unittest.main()
