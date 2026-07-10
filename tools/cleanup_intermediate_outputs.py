from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable


class ProtectedOutputError(ValueError):
    pass


@dataclass(frozen=True)
class CleanupIntermediateOutputsResult:
    summary_json: Path | None
    files_deleted: int
    files_missing: int


def resolve_paths(paths: list[Path] | tuple[Path, ...]) -> list[Path]:
    return [path.resolve() for path in paths]


def cleanup_intermediate_outputs(
    *,
    intermediate_paths: list[Path] | tuple[Path, ...],
    protected_paths: list[Path] | tuple[Path, ...],
    summary_path: Path | None = None,
    delete_file: Callable[[Path], None] | None = None,
) -> CleanupIntermediateOutputsResult:
    delete = delete_file if delete_file else lambda path: path.unlink()
    intermediates = resolve_paths(intermediate_paths)
    protected = resolve_paths(protected_paths)
    protected_set = set(protected)
    resolved_summary_path = summary_path.resolve() if summary_path is not None else None

    conflicts = [path for path in intermediates if path in protected_set]
    if conflicts:
        raise ProtectedOutputError(f"Refusing to delete protected output: {conflicts[0]}")
    if resolved_summary_path in protected_set:
        raise ProtectedOutputError(f"Refusing to overwrite protected output with cleanup summary: {resolved_summary_path}")
    if resolved_summary_path is not None and resolved_summary_path in set(intermediates):
        raise ProtectedOutputError(
            f"Refusing to recreate an intermediate file as cleanup summary: {resolved_summary_path}"
        )

    deleted_files: list[str] = []
    missing_files: list[str] = []
    for path in intermediates:
        if not path.exists():
            missing_files.append(str(path))
            continue
        if path.is_dir():
            raise IsADirectoryError(f"Intermediate cleanup only deletes files, not directories: {path}")
        delete(path)
        deleted_files.append(str(path))

    if resolved_summary_path is not None:
        resolved_summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary = {
            "created_at": datetime.now().isoformat(sep=" ", timespec="seconds"),
            "deleted_files": deleted_files,
            "missing_files": missing_files,
            "protected_files": [str(path) for path in protected],
            "files_deleted": len(deleted_files),
            "files_missing": len(missing_files),
        }
        resolved_summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    return CleanupIntermediateOutputsResult(
        summary_json=resolved_summary_path,
        files_deleted=len(deleted_files),
        files_missing=len(missing_files),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Delete current-run intermediate files after cleaned outputs are generated and verified.")
    parser.add_argument(
        "--intermediate",
        type=Path,
        action="append",
        required=True,
        help="Intermediate file to delete. Pass once per file.",
    )
    parser.add_argument(
        "--protect",
        type=Path,
        action="append",
        default=[],
        help="Original input or final output file to protect. Pass once per file.",
    )
    parser.add_argument("--summary", type=Path, default=None, help="Optional cleanup summary JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = cleanup_intermediate_outputs(
        intermediate_paths=args.intermediate,
        protected_paths=args.protect,
        summary_path=args.summary,
    )
    if result.summary_json is not None:
        print(f"Cleanup summary: {result.summary_json}")
    print(f"Files deleted: {result.files_deleted}")
    print(f"Files missing: {result.files_missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
