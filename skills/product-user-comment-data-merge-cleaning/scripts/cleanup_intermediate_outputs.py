from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

try:
    from tools.output_path_safety import (
        add_confirmed_overwrite_arguments,
        atomic_output_path,
        ensure_output_paths_safe,
    )
except ModuleNotFoundError:
    from output_path_safety import (
        add_confirmed_overwrite_arguments,
        atomic_output_path,
        ensure_output_paths_safe,
    )


class ProtectedOutputError(ValueError):
    pass


class FinalOutputVerificationError(ValueError):
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
    final_output_paths: list[Path] | tuple[Path, ...] | None = None,
    summary_path: Path | None = None,
    delete_file: Callable[[Path], None] | None = None,
    overwrite: bool = True,
    overwrite_confirmations: tuple[Path, ...] | list[Path] | None = None,
) -> CleanupIntermediateOutputsResult:
    delete = delete_file if delete_file else lambda path: path.unlink()
    intermediates = resolve_paths(intermediate_paths)
    protected = resolve_paths(protected_paths)
    if not protected:
        raise ProtectedOutputError(
            "At least one protected path is required before intermediate cleanup."
        )
    protected_set = set(protected)
    resolved_summary_path = summary_path.resolve() if summary_path is not None else None

    if final_output_paths is None:
        raise FinalOutputVerificationError(
            "Exactly one final .xlsx and one final .csv output must be declared before intermediate cleanup."
        )
    verified_final_outputs = resolve_paths(final_output_paths)
    final_suffixes = {path.suffix.casefold() for path in verified_final_outputs}
    if len(verified_final_outputs) != 2 or final_suffixes != {".xlsx", ".csv"}:
        raise FinalOutputVerificationError(
            "Exactly one final .xlsx and one final .csv output must be declared before intermediate cleanup."
        )
    missing_final_outputs = [
        path for path in verified_final_outputs if not path.is_file()
    ]
    if missing_final_outputs:
        raise FinalOutputVerificationError(
            f"Declared final output does not exist: {missing_final_outputs[0]}"
        )
    unprotected_final_outputs = [
        path for path in verified_final_outputs if path not in protected_set
    ]
    if unprotected_final_outputs:
        raise FinalOutputVerificationError(
            "Declared final output must also be protected from cleanup: "
            f"{unprotected_final_outputs[0]}"
        )

    conflicts = [path for path in intermediates if path in protected_set]
    if conflicts:
        raise ProtectedOutputError(f"Refusing to delete protected output: {conflicts[0]}")
    if resolved_summary_path in protected_set:
        raise ProtectedOutputError(f"Refusing to overwrite protected output with cleanup summary: {resolved_summary_path}")
    if resolved_summary_path is not None and resolved_summary_path in set(intermediates):
        raise ProtectedOutputError(
            f"Refusing to recreate an intermediate file as cleanup summary: {resolved_summary_path}"
        )
    if (
        resolved_summary_path is not None
        and resolved_summary_path.name.casefold().endswith(".deletions.csv")
    ):
        raise ProtectedOutputError(
            "Refusing to recreate a finalized cleaning deletion log as a cleanup summary: "
            f"{resolved_summary_path}"
        )
    finalized_audit_artifacts = {
        final_output.with_suffix(suffix)
        for final_output in verified_final_outputs
        for suffix in (".deletions.csv", ".summary.json")
    }
    if resolved_summary_path is not None and resolved_summary_path in finalized_audit_artifacts:
        raise ProtectedOutputError(
            "Refusing to recreate a finalized cleaning audit artifact as a cleanup summary: "
            f"{resolved_summary_path}"
        )
    if resolved_summary_path is not None:
        ensure_output_paths_safe(
            [],
            [resolved_summary_path],
            overwrite=overwrite,
            overwrite_confirmations=overwrite_confirmations,
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
            "verified_final_outputs": [str(path) for path in verified_final_outputs],
            "files_deleted": len(deleted_files),
            "files_missing": len(missing_files),
        }
        with atomic_output_path(resolved_summary_path) as staged_summary:
            staged_summary.write_text(
                json.dumps(summary, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    return CleanupIntermediateOutputsResult(
        summary_json=resolved_summary_path,
        files_deleted=len(deleted_files),
        files_missing=len(missing_files),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
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
        required=True,
        help="Original input or final output file to protect. Pass once per file.",
    )
    parser.add_argument(
        "--final-output",
        type=Path,
        action="append",
        required=True,
        help="Verified final cleaned output. Pass the final .xlsx and .csv once each.",
    )
    parser.add_argument("--summary", type=Path, default=None, help="Optional cleanup summary JSON path.")
    add_confirmed_overwrite_arguments(
        parser,
        overwrite_help="Replace an existing cleanup summary only after exact user confirmation.",
    )
    args = parser.parse_args(argv)
    final_suffixes = {path.suffix.casefold() for path in args.final_output}
    if len(args.final_output) != 2 or final_suffixes != {".xlsx", ".csv"}:
        parser.error("--final-output must declare exactly one final .xlsx and one final .csv")
    return args


def main() -> int:
    args = parse_args()
    result = cleanup_intermediate_outputs(
        intermediate_paths=args.intermediate,
        protected_paths=args.protect,
        final_output_paths=args.final_output,
        summary_path=args.summary,
        overwrite=args.overwrite,
        overwrite_confirmations=tuple(args.confirm_overwrite),
    )
    if result.summary_json is not None:
        print(f"Cleanup summary: {result.summary_json}")
    print(f"Files deleted: {result.files_deleted}")
    print(f"Files missing: {result.files_missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
