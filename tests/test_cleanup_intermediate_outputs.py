from __future__ import annotations

import json
import unittest
from pathlib import Path
from tests.test_support import TEST_TEMP_ROOT

from tools.cleanup_intermediate_outputs import (
    FinalOutputVerificationError,
    ProtectedOutputError,
    cleanup_intermediate_outputs,
    parse_args,
)
from tools.output_path_safety import OutputPathConflictError


class CleanupIntermediateOutputsTest(unittest.TestCase):
    def test_cli_requires_exactly_one_final_xlsx_and_csv(self) -> None:
        base_args = [
            "--intermediate",
            "standardized.xlsx",
            "--protect",
            "cleaned.xlsx",
        ]

        with self.assertRaises(SystemExit):
            parse_args(base_args)

        args = parse_args(
            [
                *base_args,
                "--protect",
                "cleaned.csv",
                "--final-output",
                "cleaned.xlsx",
                "--final-output",
                "cleaned.csv",
            ]
        )
        self.assertEqual([Path("cleaned.xlsx"), Path("cleaned.csv")], args.final_output)

    def test_refuses_cleanup_when_a_declared_final_output_is_missing(self) -> None:
        tmp = TEST_TEMP_ROOT / "case-cleanup-missing-final-output"
        tmp.mkdir(parents=True, exist_ok=True)
        intermediate = tmp / "standardized.xlsx"
        cleaned_xlsx = tmp / "cleaned.xlsx"
        missing_csv = tmp / "cleaned.csv"
        intermediate.write_text("intermediate", encoding="utf-8")
        cleaned_xlsx.write_text("cleaned", encoding="utf-8")

        with self.assertRaisesRegex(FinalOutputVerificationError, "does not exist"):
            cleanup_intermediate_outputs(
                intermediate_paths=[intermediate],
                protected_paths=[cleaned_xlsx, missing_csv],
                final_output_paths=[cleaned_xlsx, missing_csv],
            )

        self.assertTrue(intermediate.exists())
        self.assertTrue(cleaned_xlsx.exists())

    def test_existing_cleanup_summary_requires_explicit_overwrite(self) -> None:
        tmp = TEST_TEMP_ROOT / "case-cleanup-summary-no-clobber"
        tmp.mkdir(parents=True, exist_ok=True)
        intermediate = tmp / "standardized.xlsx"
        cleaned_xlsx = tmp / "cleaned.xlsx"
        cleaned_csv = tmp / "cleaned.csv"
        summary = tmp / "cleanup.summary.json"
        intermediate.write_text("intermediate", encoding="utf-8")
        cleaned_xlsx.write_text("cleaned", encoding="utf-8")
        cleaned_csv.write_text("cleaned", encoding="utf-8")
        summary.write_text("keep", encoding="utf-8")

        with self.assertRaises(OutputPathConflictError):
            cleanup_intermediate_outputs(
                intermediate_paths=[intermediate],
                protected_paths=[cleaned_xlsx, cleaned_csv],
                final_output_paths=[cleaned_xlsx, cleaned_csv],
                summary_path=summary,
                overwrite=False,
            )

        self.assertTrue(intermediate.exists())
        self.assertEqual("keep", summary.read_text(encoding="utf-8"))

    def test_refuses_cleanup_without_any_protected_paths(self) -> None:
        tmp = TEST_TEMP_ROOT / "case-cleanup-requires-protection"
        tmp.mkdir(parents=True, exist_ok=True)
        intermediate = tmp / "standardized.xlsx"
        intermediate.write_text("intermediate", encoding="utf-8")

        with self.assertRaisesRegex(ProtectedOutputError, "protected path"):
            cleanup_intermediate_outputs(
                intermediate_paths=[intermediate],
                protected_paths=[],
                final_output_paths=[tmp / "cleaned.xlsx", tmp / "cleaned.csv"],
            )

        self.assertTrue(intermediate.exists())

    def test_deletes_only_declared_intermediate_files_and_keeps_cleaned_outputs(self) -> None:
        tmp = TEST_TEMP_ROOT / "case-cleanup-intermediate-outputs"
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
            final_output_paths=[cleaned_xlsx, cleaned_csv],
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
        tmp = TEST_TEMP_ROOT / "case-cleanup-protected-output"
        tmp.mkdir(parents=True, exist_ok=True)

        cleaned_xlsx = tmp / "20260708_product_source_清洗后总表.xlsx"
        cleaned_csv = tmp / "20260708_product_source_清洗后总表.csv"
        cleaned_xlsx.write_text("cleaned", encoding="utf-8")
        cleaned_csv.write_text("cleaned", encoding="utf-8")

        with self.assertRaisesRegex(ProtectedOutputError, "protected output"):
            cleanup_intermediate_outputs(
                intermediate_paths=[cleaned_xlsx],
                protected_paths=[cleaned_xlsx, cleaned_csv],
                final_output_paths=[cleaned_xlsx, cleaned_csv],
                summary_path=tmp / "cleanup.summary.json",
            )

        self.assertTrue(cleaned_xlsx.exists())

    def test_can_cleanup_without_creating_an_extra_summary_file(self) -> None:
        tmp = TEST_TEMP_ROOT / "case-cleanup-without-summary"
        tmp.mkdir(parents=True, exist_ok=True)
        intermediate = tmp / "standardized.xlsx"
        cleaned_xlsx = tmp / "cleaned.xlsx"
        cleaned_csv = tmp / "cleaned.csv"
        intermediate.write_text("intermediate", encoding="utf-8")
        cleaned_xlsx.write_text("cleaned", encoding="utf-8")
        cleaned_csv.write_text("cleaned", encoding="utf-8")

        try:
            result = cleanup_intermediate_outputs(
                intermediate_paths=[intermediate],
                protected_paths=[cleaned_xlsx, cleaned_csv],
                final_output_paths=[cleaned_xlsx, cleaned_csv],
                summary_path=None,
            )
        except Exception as error:  # pragma: no cover - makes the RED failure explicit
            self.fail(f"summary_path=None should be supported: {error}")

        self.assertIsNone(result.summary_json)
        self.assertFalse(intermediate.exists())
        self.assertTrue(cleaned_xlsx.exists())
        self.assertEqual([], list(tmp.glob("*.json")))

    def test_refuses_summary_path_that_would_overwrite_protected_output(self) -> None:
        tmp = TEST_TEMP_ROOT / "case-cleanup-summary-conflict"
        tmp.mkdir(parents=True, exist_ok=True)
        intermediate = tmp / "standardized.xlsx"
        cleaned_xlsx = tmp / "cleaned.xlsx"
        cleaned_csv = tmp / "cleaned.csv"
        intermediate.write_text("intermediate", encoding="utf-8")
        cleaned_xlsx.write_text("cleaned", encoding="utf-8")
        cleaned_csv.write_text("cleaned", encoding="utf-8")

        with self.assertRaisesRegex(ProtectedOutputError, "protected output"):
            cleanup_intermediate_outputs(
                intermediate_paths=[intermediate],
                protected_paths=[cleaned_xlsx, cleaned_csv],
                final_output_paths=[cleaned_xlsx, cleaned_csv],
                summary_path=cleaned_xlsx,
            )

        self.assertEqual("cleaned", cleaned_xlsx.read_text(encoding="utf-8"))

    def test_refuses_to_recreate_a_cleaning_deletion_log_as_a_summary(self) -> None:
        tmp = TEST_TEMP_ROOT / "case-cleanup-no-log-restoration"
        tmp.mkdir(parents=True, exist_ok=True)
        intermediate = tmp / "standardized.xlsx"
        cleaned_xlsx = tmp / "cleaned.xlsx"
        cleaned_csv = tmp / "cleaned.csv"
        deleted_log = tmp / "cleaned.deletions.csv"
        intermediate.write_text("intermediate", encoding="utf-8")
        cleaned_xlsx.write_text("cleaned", encoding="utf-8")
        cleaned_csv.write_text("cleaned", encoding="utf-8")

        with self.assertRaisesRegex(ProtectedOutputError, "deletion log"):
            cleanup_intermediate_outputs(
                intermediate_paths=[intermediate],
                protected_paths=[cleaned_xlsx, cleaned_csv],
                final_output_paths=[cleaned_xlsx, cleaned_csv],
                summary_path=deleted_log,
            )

        self.assertTrue(intermediate.exists())
        self.assertFalse(deleted_log.exists())

    def test_refuses_cleanup_without_declared_final_outputs(self) -> None:
        tmp = TEST_TEMP_ROOT / "case-cleanup-final-outputs-required"
        tmp.mkdir(parents=True, exist_ok=True)
        intermediate = tmp / "standardized.xlsx"
        cleaned_xlsx = tmp / "cleaned.xlsx"
        intermediate.write_text("intermediate", encoding="utf-8")
        cleaned_xlsx.write_text("cleaned", encoding="utf-8")

        with self.assertRaisesRegex(FinalOutputVerificationError, "final .xlsx"):
            cleanup_intermediate_outputs(
                intermediate_paths=[intermediate],
                protected_paths=[cleaned_xlsx],
            )

        self.assertTrue(intermediate.exists())
        self.assertTrue(cleaned_xlsx.exists())

    def test_refuses_to_recreate_a_final_cleaning_summary_as_cleanup_summary(self) -> None:
        tmp = TEST_TEMP_ROOT / "case-cleanup-no-final-summary-restoration"
        tmp.mkdir(parents=True, exist_ok=True)
        intermediate = tmp / "standardized.xlsx"
        cleaned_xlsx = tmp / "cleaned.xlsx"
        cleaned_csv = tmp / "cleaned.csv"
        cleaned_summary = cleaned_xlsx.with_suffix(".summary.json")
        intermediate.write_text("intermediate", encoding="utf-8")
        cleaned_xlsx.write_text("cleaned", encoding="utf-8")
        cleaned_csv.write_text("cleaned", encoding="utf-8")

        with self.assertRaisesRegex(ProtectedOutputError, "finalized cleaning audit artifact"):
            cleanup_intermediate_outputs(
                intermediate_paths=[intermediate],
                protected_paths=[cleaned_xlsx, cleaned_csv],
                final_output_paths=[cleaned_xlsx, cleaned_csv],
                summary_path=cleaned_summary,
            )

        self.assertTrue(intermediate.exists())
        self.assertFalse(cleaned_summary.exists())


if __name__ == "__main__":
    unittest.main()
