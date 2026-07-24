from __future__ import annotations

import json
import unittest
from pathlib import Path

from openpyxl import Workbook

from tools.audit_standardized_comments import audit_standardized_workbook
from tools.standardize_excel_headers import load_config


STANDARD_HEADERS = (
    "评论日期",
    "评论内容",
    "产品名",
    "电商平台评分",
    "用户属性",
    "哈希ID",
    "点赞数",
    "子评论数/追评数",
    "一级评论",
    "二级评论",
    "三级评论",
)
VALID_HASH_ID = "a" * 64


def write_workbook(path: Path, headers: tuple[str, ...], rows: list[list[object]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "评论"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    workbook.close()


class AuditStandardizedCommentsTest(unittest.TestCase):
    def test_accepts_exact_schema_valid_hashes_and_matching_source_rows(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-standardized-audit-pass"
        tmp.mkdir(parents=True, exist_ok=True)
        source_path = tmp / "source.xlsx"
        standardized_path = tmp / "standardized.xlsx"
        write_workbook(source_path, ("原始字段",), [["one"], ["two"]])
        write_workbook(
            standardized_path,
            STANDARD_HEADERS,
            [
                ["2025-09-10", "足够长的评论内容", None, "4.0", None, VALID_HASH_ID, 4, None, None, None, None],
                ["2025-09-11", "另一条足够长评论内容", None, "5.0", None, None, 0, None, None, None, None],
            ],
        )

        result = audit_standardized_workbook(
            standardized_path,
            load_config(),
            source_path=source_path,
            output_path=tmp / "audit.json",
        )

        self.assertTrue(result.passed)
        self.assertEqual(0, result.issue_count)
        payload = json.loads(result.output_json.read_text(encoding="utf-8"))
        self.assertTrue(payload["passed"])
        self.assertEqual([], payload["issues"])
        self.assertEqual(2, payload["sheets"][0]["source_data_rows"])
        self.assertEqual(2, payload["sheets"][0]["standardized_data_rows"])

    def test_blocks_an_invalid_schema_or_raw_hash_value(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-standardized-audit-fail"
        tmp.mkdir(parents=True, exist_ok=True)
        standardized_path = tmp / "standardized-invalid.xlsx"
        invalid_headers = (*STANDARD_HEADERS[:-1], "名称")
        write_workbook(
            standardized_path,
            invalid_headers,
            [["2025-09-10", "足够长的评论内容", None, None, None, "Raw Nickname", 4, None, None, None, "Ricky"]],
        )

        result = audit_standardized_workbook(
            standardized_path,
            load_config(),
            output_path=tmp / "audit.json",
        )

        self.assertFalse(result.passed)
        self.assertGreaterEqual(result.issue_count, 2)
        payload = json.loads(result.output_json.read_text(encoding="utf-8"))
        self.assertFalse(payload["passed"])
        self.assertNotIn("Ricky", result.output_json.read_text(encoding="utf-8"))
        self.assertIn("header_schema_mismatch", {item["code"] for item in payload["issues"]})
        self.assertIn("invalid_hash_id_format", {item["code"] for item in payload["issues"]})

    def test_blocks_when_the_standardized_row_count_does_not_match_its_source(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-standardized-audit-row-count"
        tmp.mkdir(parents=True, exist_ok=True)
        source_path = tmp / "source.xlsx"
        standardized_path = tmp / "standardized.xlsx"
        write_workbook(source_path, ("原始字段",), [["one"], ["two"]])
        write_workbook(
            standardized_path,
            STANDARD_HEADERS,
            [["2025-09-10", "足够长的评论内容", None, None, None, VALID_HASH_ID, 4, None, None, None, None]],
        )

        result = audit_standardized_workbook(
            standardized_path,
            load_config(),
            source_path=source_path,
            output_path=tmp / "audit.json",
        )

        self.assertFalse(result.passed)
        self.assertIn("data_row_count_mismatch", {issue.code for issue in result.issues})


if __name__ == "__main__":
    unittest.main()
