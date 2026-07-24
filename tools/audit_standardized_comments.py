from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from tools.csv_excel_compat import is_supported_input_path, load_workbook_for_processing, unsupported_input_message
    from tools.output_path_safety import atomic_output_path, ensure_output_paths_safe
    from tools.standardize_excel_headers import HeaderStandardizerConfig, load_config
except ModuleNotFoundError:
    from csv_excel_compat import is_supported_input_path, load_workbook_for_processing, unsupported_input_message
    from output_path_safety import atomic_output_path, ensure_output_paths_safe
    from standardize_excel_headers import HeaderStandardizerConfig, load_config


HASH_ID_HEADER = "哈希ID"
HASH_ID_PATTERN = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_IDENTITY_HEADERS = frozenset(
    {
        "名称",
        "用户名称",
        "用户名",
        "昵称",
        "username",
        "author",
        "author_name",
        "author_channel_id",
        "authorChannelId",
        "用户ID",
        "IP地址",
        "IP属地",
        "ip_location",
    }
)


@dataclass(frozen=True)
class AuditIssue:
    code: str
    sheet_name: str | None


@dataclass(frozen=True)
class SheetAuditSummary:
    sheet_name: str
    header_matches: bool
    standardized_data_rows: int
    source_data_rows: int | None
    invalid_hash_id_count: int
    unexpected_headers: tuple[str, ...]
    missing_headers: tuple[str, ...]


@dataclass(frozen=True)
class StandardizedAuditResult:
    input_path: Path
    output_json: Path
    passed: bool
    issue_count: int
    sheets_processed: int
    issues: tuple[AuditIssue, ...]


def normalize_header(value: Any) -> str:
    if value is None:
        return ""
    return "".join(str(value).strip().split())


def _data_row_count(sheet: Any, header_row: int) -> int:
    return max(sheet.max_row - header_row, 0)


def _header_values(sheet: Any, header_row: int) -> tuple[Any, ...]:
    values = next(
        sheet.iter_rows(
            min_row=header_row,
            max_row=header_row,
            max_col=sheet.max_column,
            values_only=True,
        ),
        None,
    )
    return tuple(values) if values is not None else ()


def _sheet_summary(
    sheet: Any,
    config: HeaderStandardizerConfig,
    source_sheet: Any | None,
    issues: list[AuditIssue],
) -> SheetAuditSummary:
    expected_headers = tuple(column.header for column in config.output_columns)
    headers = _header_values(sheet, config.header_row)
    actual_headers = tuple("" if header is None else str(header) for header in headers)
    header_matches = actual_headers == expected_headers
    missing_headers = tuple(
        header for header in expected_headers if header not in actual_headers
    )
    unexpected_headers = tuple(
        header for header in actual_headers if header not in expected_headers
    )
    if not header_matches:
        issues.append(AuditIssue("header_schema_mismatch", sheet.title))
    if len(set(actual_headers)) != len(actual_headers):
        issues.append(AuditIssue("duplicate_output_header", sheet.title))
    if any(header in FORBIDDEN_IDENTITY_HEADERS for header in actual_headers):
        issues.append(AuditIssue("forbidden_identity_header", sheet.title))

    hash_columns = [
        index
        for index, header in enumerate(actual_headers, start=1)
        if header == HASH_ID_HEADER
    ]
    invalid_hash_id_count = 0
    if len(hash_columns) == 1:
        hash_column = hash_columns[0]
        for (value,) in sheet.iter_rows(
            min_row=config.header_row + 1,
            max_row=sheet.max_row,
            min_col=hash_column,
            max_col=hash_column,
            values_only=True,
        ):
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            if not isinstance(value, str) or HASH_ID_PATTERN.fullmatch(value) is None:
                invalid_hash_id_count += 1
        if invalid_hash_id_count:
            issues.append(AuditIssue("invalid_hash_id_format", sheet.title))
    elif hash_columns:
        issues.append(AuditIssue("duplicate_hash_id_header", sheet.title))
    else:
        issues.append(AuditIssue("missing_hash_id_header", sheet.title))

    source_data_rows = None
    if source_sheet is not None:
        source_data_rows = _data_row_count(source_sheet, config.header_row)
        if source_data_rows != _data_row_count(sheet, config.header_row):
            issues.append(AuditIssue("data_row_count_mismatch", sheet.title))

    return SheetAuditSummary(
        sheet_name=sheet.title,
        header_matches=header_matches,
        standardized_data_rows=_data_row_count(sheet, config.header_row),
        source_data_rows=source_data_rows,
        invalid_hash_id_count=invalid_hash_id_count,
        unexpected_headers=unexpected_headers,
        missing_headers=missing_headers,
    )


def default_output_path(input_path: Path) -> Path:
    return input_path.with_suffix(".audit.json")


def audit_standardized_workbook(
    input_path: Path,
    config: HeaderStandardizerConfig,
    *,
    source_path: Path | None = None,
    output_path: Path | None = None,
    overwrite: bool = True,
) -> StandardizedAuditResult:
    input_path = input_path.resolve()
    if not is_supported_input_path(input_path):
        raise ValueError(unsupported_input_message())
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    if source_path is not None:
        source_path = source_path.resolve()
        if not is_supported_input_path(source_path):
            raise ValueError(unsupported_input_message())
        if not source_path.exists():
            raise FileNotFoundError(source_path)

    resolved_output_path = (output_path if output_path else default_output_path(input_path)).resolve()
    protected_inputs = [input_path]
    if source_path is not None:
        protected_inputs.append(source_path)
    ensure_output_paths_safe(protected_inputs, [resolved_output_path], overwrite=overwrite)

    standardized_workbook = load_workbook_for_processing(
        input_path,
        read_only=True,
        data_only=False,
    )
    source_workbook = (
        load_workbook_for_processing(source_path, read_only=True, data_only=False)
        if source_path is not None
        else None
    )
    issues: list[AuditIssue] = []
    summaries: list[SheetAuditSummary] = []
    try:
        source_sheets = (
            {sheet.title: sheet for sheet in source_workbook.worksheets}
            if source_workbook is not None
            else {}
        )
        standardized_sheet_names = [sheet.title for sheet in standardized_workbook.worksheets]
        if source_workbook is not None:
            source_sheet_names = [sheet.title for sheet in source_workbook.worksheets]
            if standardized_sheet_names != source_sheet_names:
                issues.append(AuditIssue("worksheet_name_or_order_mismatch", None))

        for standardized_sheet in standardized_workbook.worksheets:
            source_sheet = source_sheets.get(standardized_sheet.title)
            if source_workbook is not None and source_sheet is None:
                issues.append(AuditIssue("source_worksheet_missing", standardized_sheet.title))
            summaries.append(
                _sheet_summary(
                    standardized_sheet,
                    config,
                    source_sheet,
                    issues,
                )
            )
    finally:
        standardized_workbook.close()
        if source_workbook is not None:
            source_workbook.close()

    payload = {
        "input_path": str(input_path),
        "source_path": str(source_path) if source_path is not None else None,
        "output_json": str(resolved_output_path),
        "passed": not issues,
        "issue_count": len(issues),
        "expected_headers": [column.header for column in config.output_columns],
        "issues": [
            {"code": issue.code, "sheet_name": issue.sheet_name}
            for issue in issues
        ],
        "sheets": [
            {
                "sheet_name": summary.sheet_name,
                "header_matches": summary.header_matches,
                "standardized_data_rows": summary.standardized_data_rows,
                "source_data_rows": summary.source_data_rows,
                "invalid_hash_id_count": summary.invalid_hash_id_count,
                "unexpected_headers": list(summary.unexpected_headers),
                "missing_headers": list(summary.missing_headers),
            }
            for summary in summaries
        ],
    }
    with atomic_output_path(resolved_output_path) as staged_output:
        staged_output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return StandardizedAuditResult(
        input_path=input_path,
        output_json=resolved_output_path,
        passed=not issues,
        issue_count=len(issues),
        sheets_processed=len(summaries),
        issues=tuple(issues),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a standardized comment workbook using deterministic structural checks."
    )
    parser.add_argument("input_path", type=Path, help="Standardized .xlsx/.xlsm/.csv file.")
    parser.add_argument(
        "--source",
        type=Path,
        default=None,
        help="The exact workbook passed to standardization, for deterministic row and sheet checks.",
    )
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None, help="Audit JSON output path.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace a confirmed existing audit output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = audit_standardized_workbook(
        args.input_path,
        load_config(args.config) if args.config else load_config(),
        source_path=args.source,
        output_path=args.output,
        overwrite=args.overwrite,
    )
    print(f"Standardized audit: {result.output_json}")
    print(f"Audit passed: {result.passed}")
    print(f"Issue count: {result.issue_count}")
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
