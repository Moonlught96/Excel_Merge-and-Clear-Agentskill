from __future__ import annotations

import argparse
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator


class OutputPathConflictError(ValueError):
    pass


BEIJING_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")


def beijing_date_text(now: datetime | None = None) -> str:
    """Return a calendar date using the workflow's fixed Beijing time basis."""
    value = now if now is not None else datetime.now(BEIJING_TIMEZONE)
    if value.tzinfo is None:
        value = value.replace(tzinfo=BEIJING_TIMEZONE)
    return value.astimezone(BEIJING_TIMEZONE).strftime("%Y%m%d")


def resolved_unique_paths(paths: list[Path] | tuple[Path, ...]) -> list[Path]:
    resolved: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        candidate = path.resolve()
        if candidate in seen:
            raise OutputPathConflictError(f"Duplicate output path is not allowed: {candidate}")
        seen.add(candidate)
        resolved.append(candidate)
    return resolved


def add_confirmed_overwrite_arguments(
    parser: argparse.ArgumentParser,
    *,
    overwrite_help: str = "Replace existing outputs only after explicit user confirmation.",
) -> None:
    """Add the workflow's two-part overwrite confirmation arguments to a CLI."""
    parser.add_argument("--overwrite", action="store_true", help=overwrite_help)
    parser.add_argument(
        "--confirm-overwrite",
        type=Path,
        action="append",
        default=[],
        metavar="EXACT_OUTPUT_PATH",
        help=(
            "Exact existing output path explicitly confirmed by the user. "
            "Pass once for every existing output that --overwrite will replace."
        ),
    )


def ensure_output_paths_safe(
    input_paths: list[Path] | tuple[Path, ...],
    output_paths: list[Path] | tuple[Path, ...],
    *,
    overwrite: bool,
    overwrite_confirmations: list[Path] | tuple[Path, ...] | None = None,
) -> list[Path]:
    inputs = {path.resolve() for path in input_paths}
    outputs = resolved_unique_paths(output_paths)
    confirmations = resolved_unique_paths(overwrite_confirmations or ())
    if confirmations and not overwrite:
        raise OutputPathConflictError(
            "--confirm-overwrite requires --overwrite; do not confirm a replacement that was not requested."
        )

    for output in outputs:
        if output in inputs:
            raise OutputPathConflictError(
                f"Output path must be a new path, not an input file: {output}"
            )
        if output.exists() and not overwrite:
            raise OutputPathConflictError(
                f"Output path already exists; pass --overwrite only after explicit confirmation: {output}"
            )

    if overwrite:
        existing_outputs = {output for output in outputs if output.exists()}
        confirmation_set = set(confirmations)
        unexpected_confirmations = confirmation_set - existing_outputs
        if unexpected_confirmations:
            unexpected = sorted(str(path) for path in unexpected_confirmations)[0]
            raise OutputPathConflictError(
                "--confirm-overwrite must name an existing output produced by this command: "
                f"{unexpected}"
            )
        missing_confirmations = existing_outputs - confirmation_set
        if missing_confirmations:
            missing = sorted(str(path) for path in missing_confirmations)[0]
            raise OutputPathConflictError(
                "Existing output requires an exact --confirm-overwrite after user confirmation: "
                f"{missing}"
            )
    return outputs


@contextmanager
def atomic_output_path(output_path: Path) -> Iterator[Path]:
    target = output_path.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(
        f".{target.stem}.{uuid.uuid4().hex}.tmp{target.suffix}"
    )
    try:
        yield staged
        if not staged.is_file():
            raise FileNotFoundError(f"Staged output was not created: {staged}")
        os.replace(staged, target)
    finally:
        staged.unlink(missing_ok=True)
