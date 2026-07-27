from __future__ import annotations

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


def ensure_output_paths_safe(
    input_paths: list[Path] | tuple[Path, ...],
    output_paths: list[Path] | tuple[Path, ...],
    *,
    overwrite: bool,
) -> list[Path]:
    inputs = {path.resolve() for path in input_paths}
    outputs = resolved_unique_paths(output_paths)
    for output in outputs:
        if output in inputs:
            raise OutputPathConflictError(
                f"Output path must be a new path, not an input file: {output}"
            )
        if output.exists() and not overwrite:
            raise OutputPathConflictError(
                f"Output path already exists; pass --overwrite only after explicit confirmation: {output}"
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
