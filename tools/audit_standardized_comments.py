from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

try:
    from tools.csv_excel_compat import is_supported_input_path, load_workbook_for_processing, unsupported_input_message
    from tools.output_path_safety import (
        add_confirmed_overwrite_arguments,
        atomic_output_path,
        beijing_date_text,
        ensure_output_paths_safe,
    )
    from tools.standardize_excel_headers import (
        DEFAULT_CONFIG_PATH as DEFAULT_STANDARDIZER_CONFIG_PATH,
        DuplicateHeaderError,
        ECOMMERCE_RATING_HEADER,
        HASH_ID_HEADER as STANDARDIZER_HASH_ID_HEADER,
        HeaderNotFoundError,
        HeaderStandardizerConfig,
        LIKES_HEADER as STANDARDIZER_LIKES_HEADER,
        PRODUCT_NAME_HEADER,
        load_config,
        normalize_ecommerce_rating,
        normalize_likes_count,
        require_canonical_standardizer_config_path,
        select_columns,
        value_for_selected_column,
    )
except ModuleNotFoundError:
    from csv_excel_compat import is_supported_input_path, load_workbook_for_processing, unsupported_input_message
    from output_path_safety import (
        add_confirmed_overwrite_arguments,
        atomic_output_path,
        beijing_date_text,
        ensure_output_paths_safe,
    )
    from standardize_excel_headers import (
        DEFAULT_CONFIG_PATH as DEFAULT_STANDARDIZER_CONFIG_PATH,
        DuplicateHeaderError,
        ECOMMERCE_RATING_HEADER,
        HASH_ID_HEADER as STANDARDIZER_HASH_ID_HEADER,
        HeaderNotFoundError,
        HeaderStandardizerConfig,
        LIKES_HEADER as STANDARDIZER_LIKES_HEADER,
        PRODUCT_NAME_HEADER,
        load_config,
        normalize_ecommerce_rating,
        normalize_likes_count,
        require_canonical_standardizer_config_path,
        select_columns,
        value_for_selected_column,
    )


HASH_ID_HEADER = "哈希ID"
LIKES_HEADER = "点赞数"
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
    blank_likes_count: int
    mapped_value_mismatch_count: int
    source_mapping_checked: bool
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


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _as_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _mapped_values_match(expected: Any, actual: Any) -> bool:
    if _is_blank(expected):
        return _is_blank(actual)
    expected_number = _as_decimal(expected)
    actual_number = _as_decimal(actual)
    if expected_number is not None or actual_number is not None:
        return expected_number is not None and actual_number is not None and expected_number == actual_number
    return expected == actual


def _mapped_value_mismatch_count(
    standardized_sheet: Any,
    source_sheet: Any,
    config: HeaderStandardizerConfig,
    reference_date: date | None,
) -> tuple[int, bool]:
    """Compare fixed mappings without recording raw comment or identity values."""
    source_headers = list(_header_values(source_sheet, config.header_row))
    try:
        selected_columns = select_columns(source_headers, config)
    except (HeaderNotFoundError, DuplicateHeaderError):
        # Structural auditing remains useful for generic sources. Real workflow
        # inputs have already passed this mapping step during standardization.
        return 0, False

    output_headers = _header_values(standardized_sheet, config.header_row)
    output_indexes = {
        normalize_header(header): index
        for index, header in enumerate(output_headers)
        if normalize_header(header)
    }
    mismatch_count = 0
    for source_row, standardized_row in zip(
        source_sheet.iter_rows(
            min_row=config.header_row + 1,
            max_row=source_sheet.max_row,
            max_col=source_sheet.max_column,
            values_only=True,
        ),
        standardized_sheet.iter_rows(
            min_row=config.header_row + 1,
            max_row=standardized_sheet.max_row,
            max_col=standardized_sheet.max_column,
            values_only=True,
        ),
    ):
        for column in selected_columns:
            output_key = normalize_header(column.output_header)
            if output_key == normalize_header(STANDARDIZER_HASH_ID_HEADER):
                continue
            output_index = output_indexes.get(output_key)
            if output_index is None or output_index >= len(standardized_row):
                continue

            expected_value = value_for_selected_column(
                source_row,
                column,
                today=reference_date,
            )
            if output_key == normalize_header(PRODUCT_NAME_HEADER) and _is_blank(expected_value):
                # A confirmed per-run product fallback is not stored in the source.
                continue
            if output_key == normalize_header(ECOMMERCE_RATING_HEADER):
                expected_value = normalize_ecommerce_rating(expected_value)
            if output_key == normalize_header(STANDARDIZER_LIKES_HEADER):
                expected_value = normalize_likes_count(expected_value)

            if not _mapped_values_match(expected_value, standardized_row[output_index]):
                mismatch_count += 1
    return mismatch_count, True


def _sheet_summary(
    sheet: Any,
    config: HeaderStandardizerConfig,
    source_sheet: Any | None,
    issues: list[AuditIssue],
    reference_date: date | None,
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

    likes_columns = [
        index
        for index, header in enumerate(actual_headers, start=1)
        if header == LIKES_HEADER
    ]
    blank_likes_count = 0
    if len(likes_columns) == 1:
        likes_column = likes_columns[0]
        for (value,) in sheet.iter_rows(
            min_row=config.header_row + 1,
            max_row=sheet.max_row,
            min_col=likes_column,
            max_col=likes_column,
            values_only=True,
        ):
            if value is None or (isinstance(value, str) and not value.strip()):
                blank_likes_count += 1
        if blank_likes_count:
            issues.append(AuditIssue("blank_likes_value", sheet.title))

    source_data_rows = None
    mapped_value_mismatch_count = 0
    source_mapping_checked = False
    if source_sheet is not None:
        source_data_rows = _data_row_count(source_sheet, config.header_row)
        if source_data_rows != _data_row_count(sheet, config.header_row):
            issues.append(AuditIssue("data_row_count_mismatch", sheet.title))
        mapped_value_mismatch_count, source_mapping_checked = _mapped_value_mismatch_count(
            sheet,
            source_sheet,
            config,
            reference_date,
        )
        if mapped_value_mismatch_count:
            issues.append(AuditIssue("mapped_value_mismatch", sheet.title))

    return SheetAuditSummary(
        sheet_name=sheet.title,
        header_matches=header_matches,
        standardized_data_rows=_data_row_count(sheet, config.header_row),
        source_data_rows=source_data_rows,
        invalid_hash_id_count=invalid_hash_id_count,
        blank_likes_count=blank_likes_count,
        mapped_value_mismatch_count=mapped_value_mismatch_count,
        source_mapping_checked=source_mapping_checked,
        unexpected_headers=unexpected_headers,
        missing_headers=missing_headers,
    )


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{beijing_date_text()}_{input_path.stem}.audit.json")


def load_standardization_reference_date(input_path: Path) -> date | None:
    summary_path = input_path.with_suffix(".standardized.summary.json")
    if not summary_path.is_file():
        return None
    try:
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        value = payload.get("reference_date")
        return date.fromisoformat(value) if isinstance(value, str) else None
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def audit_standardized_workbook(
    input_path: Path,
    config: HeaderStandardizerConfig,
    *,
    source_path: Path | None = None,
    output_path: Path | None = None,
    overwrite: bool = True,
    overwrite_confirmations: tuple[Path, ...] | list[Path] | None = None,
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

    reference_date = load_standardization_reference_date(input_path)

    resolved_output_path = (output_path if output_path else default_output_path(input_path)).resolve()
    protected_inputs = [input_path]
    if source_path is not None:
        protected_inputs.append(source_path)
    ensure_output_paths_safe(
        protected_inputs,
        [resolved_output_path],
        overwrite=overwrite,
        overwrite_confirmations=overwrite_confirmations,
    )

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
                    reference_date,
                )
            )
    finally:
        standardized_workbook.close()
        if source_workbook is not None:
            source_workbook.close()

    payload = {
        "input_path": str(input_path),
        "source_path": str(source_path) if source_path is not None else None,
        "reference_date": reference_date.isoformat() if reference_date else None,
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
                "blank_likes_count": summary.blank_likes_count,
                "mapped_value_mismatch_count": summary.mapped_value_mismatch_count,
                "source_mapping_checked": summary.source_mapping_checked,
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
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_STANDARDIZER_CONFIG_PATH,
        help="Only the bundled canonical standardizer config is accepted.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Explicit current-run audit JSON output path.",
    )
    add_confirmed_overwrite_arguments(
        parser,
        overwrite_help="Replace an existing audit output only after exact user confirmation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = audit_standardized_workbook(
        args.input_path,
        load_config(require_canonical_standardizer_config_path(args.config)),
        source_path=args.source,
        output_path=args.output,
        overwrite=args.overwrite,
        overwrite_confirmations=tuple(args.confirm_overwrite),
    )
    print(f"Standardized audit: {result.output_json}")
    print(f"Audit passed: {result.passed}")
    print(f"Issue count: {result.issue_count}")
    return 0 if result.passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
