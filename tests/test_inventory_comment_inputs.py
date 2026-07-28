from __future__ import annotations

import unittest
from pathlib import Path

from openpyxl import Workbook

from tools.inventory_comment_inputs import inventory_comment_inputs


class InventoryCommentInputsTest(unittest.TestCase):
    def test_counts_csv_logical_rows_and_xlsx_rows_from_explicit_inputs(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-comment-input-inventory"
        tmp.mkdir(parents=True, exist_ok=True)
        csv_path = tmp / "comments.csv"
        xlsx_path = tmp / "comments.xlsx"
        csv_path.write_text(
            "date,comment\n"
            "2026-07-01,\"first logical line\nsecond physical line\"\n"
            "2026-07-02,another comment\n",
            encoding="utf-8-sig",
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Sheet1"
        sheet.append(["date", "comment"])
        sheet.append(["2026-07-03", "xlsx comment"])
        workbook.save(xlsx_path)
        workbook.close()

        result = inventory_comment_inputs([csv_path, xlsx_path])

        self.assertEqual(2, result.files_processed)
        self.assertEqual(2, result.sheets_processed)
        self.assertEqual(3, result.data_rows)
        self.assertEqual(2, result.files[0].data_rows)
        self.assertEqual(1, result.files[1].data_rows)

    def test_rejects_duplicate_explicit_input_path(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-comment-input-inventory-duplicates"
        tmp.mkdir(parents=True, exist_ok=True)
        csv_path = tmp / "comments.csv"
        csv_path.write_text("date,comment\n2026-07-01,comment\n", encoding="utf-8-sig")

        with self.assertRaisesRegex(ValueError, "Duplicate input path"):
            inventory_comment_inputs([csv_path, csv_path])


if __name__ == "__main__":
    unittest.main()
