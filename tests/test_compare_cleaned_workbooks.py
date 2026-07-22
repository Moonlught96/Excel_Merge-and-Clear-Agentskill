from __future__ import annotations

import unittest
from pathlib import Path

from openpyxl import Workbook

from tools.compare_cleaned_workbooks import compare_workbooks
from tools.output_path_safety import OutputPathConflictError


def write_workbook(path: Path, rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


class CompareCleanedWorkbooksTest(unittest.TestCase):
    def test_reports_duplicate_row_multiplicity_difference(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-compare-duplicate-multiplicity"
        tmp.mkdir(parents=True, exist_ok=True)
        left = tmp / "left.xlsx"
        right = tmp / "right.xlsx"
        output_dir = tmp / "comparison"
        header = ["评论日期", "评论内容"]
        duplicate = ["2026-07-22", "重复评论内容足够完整"]
        write_workbook(left, [header, duplicate, duplicate])
        write_workbook(right, [header, duplicate])

        report = compare_workbooks(
            left,
            right,
            output_dir,
            left_label="left",
            right_label="right",
            comment_column=2,
        )

        self.assertEqual(1, report["whole_row_only_in_left_count"])
        self.assertEqual(0, report["whole_row_only_in_right_count"])

    def test_compares_formula_text_instead_of_uncalculated_cache_values(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-compare-formulas"
        tmp.mkdir(parents=True, exist_ok=True)
        left = tmp / "left.xlsx"
        right = tmp / "right.xlsx"
        header = ["评论内容", "点赞数"]
        write_workbook(left, [header, ["公式评论内容足够完整", "=1+1"]])
        write_workbook(right, [header, ["公式评论内容足够完整", "=1+2"]])

        report = compare_workbooks(
            left,
            right,
            tmp / "comparison",
            left_label="left",
            right_label="right",
            comment_column=1,
        )

        self.assertEqual(1, report["whole_row_only_in_left_count"])
        self.assertEqual(1, report["whole_row_only_in_right_count"])

    def test_requires_explicit_overwrite_for_existing_comparison_outputs(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-compare-no-clobber"
        tmp.mkdir(parents=True, exist_ok=True)
        left = tmp / "left.xlsx"
        right = tmp / "right.xlsx"
        output_dir = tmp / "comparison"
        output_dir.mkdir(parents=True, exist_ok=True)
        summary_path = output_dir / "comparison-summary.json"
        summary_path.write_text("keep", encoding="utf-8")
        write_workbook(left, [["评论内容"], ["左侧评论内容足够完整"]])
        write_workbook(right, [["评论内容"], ["右侧评论内容足够完整"]])

        with self.assertRaises(OutputPathConflictError):
            compare_workbooks(
                left,
                right,
                output_dir,
                left_label="left",
                right_label="right",
                comment_column=1,
                overwrite=False,
            )

        self.assertEqual("keep", summary_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
