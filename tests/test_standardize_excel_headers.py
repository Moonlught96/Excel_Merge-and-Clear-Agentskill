from __future__ import annotations

import json
import unittest
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook

from tools.standardize_excel_headers import HeaderNotFoundError, load_config, standardize_workbook


EXPECTED_HEADER = ["评论日期", "评论内容", "产品名", "点赞数", "子评论数/追评数", "一级评论", "二级评论", "三级评论"]


class StandardizeExcelHeadersTest(unittest.TestCase):
    def test_standardizes_header_order_and_removes_risk_columns(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-standardize-headers"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.xlsx"
        output_dir = tmp / "out"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SheetA"
        sheet.append(["IP地址", "用户名称", "评论内容", "评论时间", "点赞数", "子评论数", "一级评论内容", "引用的评论内容", "其它列"])
        sheet.append(["广东", "SHANE", "评论 A", "2026/01/05", 3, 2, "一级 A", "二级 A", "extra"])
        workbook.save(input_path)

        result = standardize_workbook(input_path, load_config(), output_dir=output_dir)

        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["SheetA"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(("2026/01/05", "评论 A", None, 3, 2, "一级 A", "二级 A", None), rows[1])
        self.assertTrue(result.summary_json.exists())

        original = load_workbook(input_path, read_only=True, data_only=True)
        original_header = next(original["SheetA"].iter_rows(max_row=1, values_only=True))
        self.assertEqual(
            ("IP地址", "用户名称", "评论内容", "评论时间", "点赞数", "子评论数", "一级评论内容", "引用的评论内容", "其它列"),
            original_header,
        )

    def test_rejects_missing_required_header_without_guessing(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-standardize-missing-header"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.xlsx"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SheetA"
        sheet.append(["评论日期", "评论内容", "子评论数", "一级评论", "二级评论"])
        sheet.append(["2026/01/05", "评论 A", 2, "一级 A", "二级 A"])
        workbook.save(input_path)

        with self.assertRaisesRegex(HeaderNotFoundError, "Available headers"):
            standardize_workbook(input_path, load_config(), output_dir=tmp / "out")

    def test_splits_taobao_comment_date_and_product_into_two_standard_columns(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-taobao-date-product-header"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.xlsx"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SheetA"
        sheet.append(["评论日期与产品", "评论内容", "点赞数", "子评论数", "一级评论", "二级评论", "三级评论", "昵称", "IP属地"])
        sheet.append(["2026年6月21日 已购：触摸开关 / 黑", "评论 A", 3, 2, "一级 A", "二级 A", "三级 A", "user", "广东"])
        workbook.save(input_path)

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["SheetA"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(
            ("2026年6月21日", "评论 A", "触摸开关 / 黑", 3, 2, "一级 A", "二级 A", "三级 A"),
            rows[1],
        )

    def test_maps_direct_product_header_to_product_name(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-direct-product-header"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.xlsx"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SheetA"
        sheet.append(["评论日期", "评论内容", "购买产品", "点赞数", "追评数", "一级评论", "二级评论", "三级评论"])
        sheet.append(["2026/06/21", "评论 A", "无线护眼屏幕挂灯", 3, 2, "一级 A", "二级 A", "三级 A"])
        workbook.save(input_path)

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["SheetA"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(("2026/06/21", "评论 A", "无线护眼屏幕挂灯", 3, 2, "一级 A", "二级 A", "三级 A"), rows[1])

    def test_maps_confirmed_taobao_aliases_to_standard_columns(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-confirmed-taobao-aliases"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.xlsx"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SheetA"
        sheet.append(["用户名", "评论日期与产品", "评论内容", "评论数", "点赞量", "追评"])
        sheet.append(["user1", "2026年2月12日已购：浅灰色[MA270U(27英寸4K)]", "评论 A", 5, 3, "追评 A"])
        workbook.save(input_path)

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["SheetA"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(
            ("2026年2月12日", "评论 A", "浅灰色[MA270U(27英寸4K)]", 3, 5, "追评 A", None, None),
            rows[1],
        )

    def test_maps_confirmed_english_comment_aliases_and_drops_id_risk_columns(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-confirmed-english-comment-aliases"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.xlsx"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SheetA"
        sheet.append(["rpid", "parent_rpid", "username", "content", "like_count", "timestamp", "ip_location", "子评论数"])
        sheet.append([156365080, 0, "user1", "评论 A", 2, 1678870952, "未知", 0])
        workbook.save(input_path)

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["SheetA"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(("2023-03-15", "评论 A", None, 2, 0, None, None, None), rows[1])

        summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
        self.assertEqual(
            ["rpid", "parent_rpid", "username", "ip_location"],
            summary["sheets"][0]["configured_drop_headers_found"],
        )

    def test_keeps_subcomment_count_output_column_blank_when_source_header_is_missing(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-missing-subcomment-count"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.xlsx"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SheetA"
        sheet.append(["timestamp", "content", "like_count", "username", "ip_location"])
        sheet.append(["1678870952", "评论 A", "2", "user1", "未知"])
        workbook.save(input_path)

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["SheetA"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(("2023-03-15", "评论 A", None, "2", None, None, None, None), rows[1])

    def test_standardizes_csv_input_with_same_header_mapping_rules(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-standardize-csv-input"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.csv"
        input_path.write_text(
            "timestamp,content,like_count,子评论数,username,ip_location\n"
            "1678870952,评论 A,2,0,user1,未知\n",
            encoding="utf-8-sig",
        )

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["raw"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(("2023-03-15", "评论 A", None, "2", "0", None, None, None), rows[1])

    def test_maps_tiktok_comment_exporter_aliases_without_ai(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-tiktok-aliases"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.csv"
        input_path.write_text(
            "id,uniqueId,text,diggCount,replyCommentTotal,createTime\n"
            "1001,user_a,This monitor light works great,4,7,1678870952\n",
            encoding="utf-8-sig",
        )

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["raw"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(("2023-03-15", "This monitor light works great", None, "4", "7", None, None, None), rows[1])

        summary = json.loads(result.summary_json.read_text(encoding="utf-8"))
        self.assertEqual(["id", "uniqueId"], summary["sheets"][0]["configured_drop_headers_found"])

    def test_maps_confirmed_tiktok_chinese_exporter_aliases_without_ai(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-tiktok-chinese-aliases"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.csv"
        input_path.write_text(
            "评论ID,回复哪个评论,用户身份,用户名,昵称,评论,评论时间,Digg Count,Author Digged,回复数,固定到顶部,用户主页\n"
            "1001,0,user,user_a,Nick,This monitor light works great,1678870952,4,false,7,false,https://example.com/user\n",
            encoding="utf-8-sig",
        )

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["raw"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(("2023-03-15", "This monitor light works great", None, "4", "7", None, None, None), rows[1])

    def test_maps_confirmed_tiktok_chinese_datetime_without_time_output(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-tiktok-chinese-datetime"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.csv"
        input_path.write_text(
            "评论,评论时间,Digg Count,回复数\n"
            "This monitor light works great,2026/7/7 08:24:05,4,7\n",
            encoding="utf-8-sig",
        )

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["raw"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(("2026-07-07", "This monitor light works great", None, "4", "7", None, None, None), rows[1])

    def test_maps_youtube_comment_aliases_and_iso_time_to_beijing_date(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-youtube-aliases"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.xlsx"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SheetA"
        sheet.append(["authorDisplayName", "commentText", "likeCount", "replyCount", "publishedAt", "videoId", "replyText"])
        sheet.append(["User A", "Great light for my desk", 12, 3, "2026-07-08T23:30:00Z", "abc123", "Thanks for sharing"])
        workbook.save(input_path)

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["SheetA"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(("2026-07-09", "Great light for my desk", None, 12, 3, "Thanks for sharing", None, None), rows[1])

    def test_maps_youtube_relative_published_at_to_beijing_year_or_month(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-youtube-relative-published-at"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.xlsx"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SheetA"
        sheet.append(["published_at", "text", "likes", "reply_count"])
        sheet.append(["1年前", "One year old comment", 1, 0])
        sheet.append(["2年前", "Two years old comment", 2, 0])
        sheet.append(["9个月前", "Nine months old comment", 3, 0])
        sheet.append(["4个月前", "Four months old comment", 4, 0])
        workbook.save(input_path)

        result = standardize_workbook(
            input_path,
            load_config(),
            output_dir=tmp / "out",
            today=date(2026, 7, 9),
        )
        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=True)
        rows = list(standardized["SheetA"].iter_rows(values_only=True))

        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual(("2025", "One year old comment", None, 1, 0, None, None, None), rows[1])
        self.assertEqual(("2024", "Two years old comment", None, 2, 0, None, None, None), rows[2])
        self.assertEqual(("2025-10", "Nine months old comment", None, 3, 0, None, None, None), rows[3])
        self.assertEqual(("2026-03", "Four months old comment", None, 4, 0, None, None, None), rows[4])

    def test_preserves_formula_cells_in_retained_columns(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-standardize-preserves-formulas"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "raw.xlsx"

        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "SheetA"
        sheet.append(["评论日期", "评论内容", "点赞数"])
        sheet.append(["2026-07-08", "评论内容足够完整", "=1+1"])
        workbook.save(input_path)

        result = standardize_workbook(input_path, load_config(), output_dir=tmp / "out")

        standardized = load_workbook(result.output_xlsx, read_only=True, data_only=False)
        rows = list(standardized["SheetA"].iter_rows(values_only=True))
        self.assertEqual(tuple(EXPECTED_HEADER), rows[0])
        self.assertEqual("=1+1", rows[1][3])



if __name__ == "__main__":
    unittest.main()
