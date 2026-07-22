from __future__ import annotations

import unittest
from pathlib import Path

from tools.csv_excel_compat import read_csv_rows


class CsvExcelCompatTest(unittest.TestCase):
    def test_reads_utf16_csv_with_bom_without_type_inference(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-csv-utf16"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "comments.csv"
        input_path.write_text(
            "timestamp,content\n1678870952,Comentario español completo\n",
            encoding="utf-16",
        )

        result = read_csv_rows(input_path)

        self.assertEqual("utf-16", result.encoding)
        self.assertEqual("1678870952", result.rows[1][0])
        self.assertEqual("Comentario español completo", result.rows[1][1])


if __name__ == "__main__":
    unittest.main()
