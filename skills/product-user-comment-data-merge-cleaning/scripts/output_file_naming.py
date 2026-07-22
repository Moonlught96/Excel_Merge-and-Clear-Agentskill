from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

try:
    from tools.csv_excel_compat import is_supported_input_path, load_workbook_for_processing
    from tools.standardize_excel_headers import split_comment_date_and_product
except ModuleNotFoundError:
    from csv_excel_compat import is_supported_input_path, load_workbook_for_processing
    from standardize_excel_headers import split_comment_date_and_product


BEIJING_TZ = ZoneInfo("Asia/Shanghai")
STEP_NAME_BY_KEY = {
    "merge": "合并总表",
    "standardized": "标准化总表",
    "cleaned": "清洗后总表",
}
SOURCE_RULES = (
    ("淘宝", "淘宝评论数据"),
    ("天猫", "天猫评论数据"),
    ("京东", "京东评论数据"),
    ("小红书", "小红书评论数据"),
    ("抖音", "抖音评论数据"),
    ("微博", "微博评论数据"),
    ("B站", "B站评论数据"),
    ("哔哩哔哩", "B站评论数据"),
    ("TikTok", "TikTok评论数据"),
    ("Tiktok", "TikTok评论数据"),
    ("tiktok", "TikTok评论数据"),
    ("TTCommentExporter", "TikTok评论数据"),
    ("YouTube", "YouTube评论数据"),
    ("youtube", "YouTube评论数据"),
    ("Youtube", "YouTube评论数据"),
    ("yt-comments", "YouTube评论数据"),
)
PRODUCT_HEADERS = {"产品名", "购买产品", "商品名称", "商品"}
COMMENT_DATE_AND_PRODUCT_HEADERS = {"评论日期与产品"}
GENERIC_PARTS = {
    "专案",
    "未清洗数据",
    "清洗后的数据",
    "02_收集的数据",
    "社媒_小红书",
    "产品数据",
    "电商平台数据",
    "Tiktok",
    "TikTok",
    "youtube数据",
    "长视频评论",
    "Shorts",
    "merged",
    "outputs",
    ".tmp-tests",
}
GENERIC_FILENAME_PATTERNS = (
    r"【[^】]+】",
    r"TTCommentExporter",
    r"yt-comments",
    r"BV[0-9A-Za-z]+",
    r"[0-9a-fA-F]{8}$",
    r"comments[-_ ]?replies",
    r"comments",
    r"根据链接采集笔记评论",
    r"采集笔记评论",
    r"评论数据",
    r"总表",
    r"合并总表",
    r"标准化总表",
    r"清洗后总表",
)
WINDOWS_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass(frozen=True)
class NamingPlan:
    date_text: str
    product_name: str | None
    data_source: str | None
    product_candidates: list[str]
    data_source_candidates: list[str]
    missing_fields: list[str]
    filenames: dict[str, str]


def beijing_date_text(today: datetime | None = None) -> str:
    value = today if today else datetime.now(BEIJING_TZ)
    if value.tzinfo is None:
        value = value.replace(tzinfo=BEIJING_TZ)
    else:
        value = value.astimezone(BEIJING_TZ)
    return value.strftime("%Y%m%d")


def sanitize_filename_component(value: str) -> str:
    sanitized = WINDOWS_INVALID_FILENAME_CHARS.sub(" ", value)
    sanitized = re.sub(r"\s+", " ", sanitized).strip(" .")
    return sanitized


def unique_sorted(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def normalize_stem_for_product(stem: str) -> str:
    value = stem
    for pattern in GENERIC_FILENAME_PATTERNS:
        value = re.sub(pattern, "", value)
    for keyword, source_name in SOURCE_RULES:
        value = value.replace(source_name, "")
        value = value.replace(keyword, "")
    value = re.sub(r"\.(xlsx|xlsm|xls|csv)$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^\d{6,8}_", "", value)
    value = re.sub(r"^\d{8,}", "", value)
    value = re.sub(r"\d{8}-\d{6}", "", value)
    value = re.sub(r"\d{8,14}", "", value)
    value = re.sub(r"(^|[-_ ])\d+(?=$|[-_ ])", " ", value)
    value = re.sub(r"(^|[-_ ])\d+(?=$|[-_ ])", " ", value)
    value = re.sub(r"[-_]+$", "", value)
    value = re.sub(r"^[-_]+", "", value)
    return sanitize_filename_component(value)


def normalize_parent_for_product(part: str) -> str:
    value = part
    for pattern in GENERIC_FILENAME_PATTERNS:
        value = re.sub(pattern, "", value)
    for keyword, source_name in SOURCE_RULES:
        value = value.replace(source_name, "")
        value = value.replace(keyword, "")
    value = re.sub(r"[-_]+$", "", value)
    value = re.sub(r"^[-_]+", "", value)
    return sanitize_filename_component(value)


def source_candidates_from_paths(paths: list[Path]) -> list[str]:
    candidates: list[str] = []
    for path in paths:
        text = " ".join([path.stem, *path.parts])
        for keyword, source_name in SOURCE_RULES:
            if keyword in text:
                candidates.append(source_name)
    return unique_sorted(candidates)


def product_candidates_from_names(paths: list[Path]) -> list[str]:
    candidates: list[str] = []
    for path in paths:
        stem_candidate = normalize_stem_for_product(path.stem)
        if stem_candidate:
            candidates.append(stem_candidate)
            continue

        for part in list(reversed(path.parent.parts))[:2]:
            if part in GENERIC_PARTS:
                continue
            if part.startswith("case-"):
                continue
            if part.endswith("Project") or part.endswith("项目"):
                continue
            if any(keyword in part for keyword, _ in SOURCE_RULES):
                continue
            part_candidate = normalize_parent_for_product(part)
            if part_candidate:
                candidates.append(part_candidate)
                break
    return unique_sorted(candidates)


def product_candidates_from_workbook(path: Path) -> list[str]:
    if not path.exists() or not is_supported_input_path(path):
        return []

    workbook = load_workbook_for_processing(path, read_only=True, data_only=True)
    try:
        candidates: list[str] = []
        for sheet in workbook.worksheets:
            rows = sheet.iter_rows(values_only=True)
            try:
                headers = next(rows)
            except StopIteration:
                continue

            product_columns: list[int] = []
            date_product_columns: list[int] = []
            for column_index, header in enumerate(headers):
                header_text = "" if header is None else str(header).strip()
                if header_text in PRODUCT_HEADERS:
                    product_columns.append(column_index)
                if header_text in COMMENT_DATE_AND_PRODUCT_HEADERS:
                    date_product_columns.append(column_index)

            for row in rows:
                for column_index in product_columns:
                    if column_index < len(row) and row[column_index] is not None:
                        value = sanitize_filename_component(str(row[column_index]))
                        if value:
                            candidates.append(value)
                for column_index in date_product_columns:
                    if column_index < len(row):
                        _, product_name = split_comment_date_and_product(row[column_index])
                        if product_name:
                            value = sanitize_filename_component(str(product_name))
                            if value:
                                candidates.append(value)
        return unique_sorted(candidates)
    finally:
        workbook.close()


def choose_single(candidates: list[str], override: str | None) -> tuple[str | None, list[str], bool]:
    if override:
        return sanitize_filename_component(override), [], False
    unique = unique_sorted(candidates)
    if len(unique) == 1:
        return unique[0], unique, False
    return None, unique, bool(unique)


def output_filenames(date_text: str, product_name: str, data_source: str) -> dict[str, str]:
    base = f"{date_text}_{product_name}_{data_source}"
    filenames = {
        key: f"{base}_{step_name}.xlsx"
        for key, step_name in STEP_NAME_BY_KEY.items()
    }
    filenames["cleaned_csv"] = f"{base}_{STEP_NAME_BY_KEY['cleaned']}.csv"
    return filenames


def build_naming_plan(
    input_paths: list[Path],
    *,
    product_name: str | None = None,
    data_source: str | None = None,
    today: datetime | None = None,
) -> NamingPlan:
    date_text = beijing_date_text(today)
    if data_source:
        detected_source, source_candidates, source_ambiguous = choose_single([], data_source)
    else:
        source_candidates = source_candidates_from_paths(input_paths)
        detected_source, source_candidates, source_ambiguous = choose_single(source_candidates, None)

    if product_name:
        detected_product, product_candidates, product_ambiguous = choose_single([], product_name)
    else:
        product_candidates = product_candidates_from_names(input_paths)
        if not product_candidates:
            for path in input_paths:
                product_candidates.extend(product_candidates_from_workbook(path))
        detected_product, product_candidates, product_ambiguous = choose_single(product_candidates, None)

    missing_fields: list[str] = []
    if not detected_product or product_ambiguous:
        missing_fields.append("product_name")
    if not detected_source or source_ambiguous:
        missing_fields.append("data_source")

    filenames = (
        output_filenames(date_text, detected_product, detected_source)
        if not missing_fields and detected_product and detected_source
        else {}
    )
    return NamingPlan(
        date_text=date_text,
        product_name=detected_product,
        data_source=detected_source,
        product_candidates=product_candidates,
        data_source_candidates=source_candidates,
        missing_fields=missing_fields,
        filenames=filenames,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan confirmed output filenames for Excel/CSV workflow.")
    parser.add_argument("input_paths", type=Path, nargs="+", help="Explicit input .xlsx/.xlsm/.csv files.")
    parser.add_argument("--product-name", default=None, help="Confirmed product name.")
    parser.add_argument("--data-source", default=None, help="Confirmed data source.")
    parser.add_argument("--date", default=None, help="Override date in YYYYMMDD format for tests/manual runs.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    today = datetime.strptime(args.date, "%Y%m%d") if args.date else None
    plan = build_naming_plan(
        args.input_paths,
        product_name=args.product_name,
        data_source=args.data_source,
        today=today,
    )
    print(
        json.dumps(
            {
                "date": plan.date_text,
                "product_name": plan.product_name,
                "data_source": plan.data_source,
                "missing_fields": plan.missing_fields,
                "product_candidates": plan.product_candidates,
                "data_source_candidates": plan.data_source_candidates,
                "filenames": plan.filenames,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
