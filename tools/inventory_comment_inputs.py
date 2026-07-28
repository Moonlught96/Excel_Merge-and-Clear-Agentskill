from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from tools.csv_excel_compat import load_workbook_for_processing
    from tools.merge_excel_workbooks import is_blank_row, validate_input_paths
except ModuleNotFoundError:
    from csv_excel_compat import load_workbook_for_processing
    from merge_excel_workbooks import is_blank_row, validate_input_paths


@dataclass(frozen=True)
class SheetInventory:
    sheet_name: str
    data_rows: int


@dataclass(frozen=True)
class FileInventory:
    input_path: Path
    sheets: tuple[SheetInventory, ...]
    data_rows: int


@dataclass(frozen=True)
class InputInventory:
    files: tuple[FileInventory, ...]
    files_processed: int
    sheets_processed: int
    data_rows: int


def _data_row_count(sheet: Any) -> int:
    rows = sheet.iter_rows(values_only=True)
    try:
        header = next(rows)
    except StopIteration:
        return 0
    if is_blank_row(tuple(header)):
        return 0
    return sum(1 for row in rows if not is_blank_row(tuple(row)))


def inventory_comment_inputs(input_paths: list[Path]) -> InputInventory:
    """Count logical data rows from only the explicitly supplied source files."""
    validated_paths = validate_input_paths(input_paths)
    file_inventories: list[FileInventory] = []

    for path in validated_paths:
        workbook = load_workbook_for_processing(path, read_only=True, data_only=False)
        try:
            sheets = tuple(
                SheetInventory(sheet_name=sheet.title, data_rows=_data_row_count(sheet))
                for sheet in workbook.worksheets
            )
        finally:
            workbook.close()

        file_inventories.append(
            FileInventory(
                input_path=path,
                sheets=sheets,
                data_rows=sum(sheet.data_rows for sheet in sheets),
            )
        )

    return InputInventory(
        files=tuple(file_inventories),
        files_processed=len(file_inventories),
        sheets_processed=sum(len(file.sheets) for file in file_inventories),
        data_rows=sum(file.data_rows for file in file_inventories),
    )


def inventory_as_dict(inventory: InputInventory) -> dict[str, Any]:
    return {
        "files_processed": inventory.files_processed,
        "sheets_processed": inventory.sheets_processed,
        "data_rows": inventory.data_rows,
        "files": [
            {
                "input_path": str(file.input_path),
                "data_rows": file.data_rows,
                "sheets": [
                    {"sheet_name": sheet.sheet_name, "data_rows": sheet.data_rows}
                    for sheet in file.sheets
                ],
            }
            for file in inventory.files
        ],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count logical comment records in explicitly supplied Excel/CSV inputs."
    )
    parser.add_argument(
        "input_paths",
        nargs="+",
        type=Path,
        help="Explicit .xlsx/.xlsm/.csv inputs only; folders are rejected and never scanned.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    inventory = inventory_comment_inputs(args.input_paths)
    print(json.dumps(inventory_as_dict(inventory), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
