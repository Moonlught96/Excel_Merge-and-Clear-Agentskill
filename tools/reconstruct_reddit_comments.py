from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from reddit_reconstruction.cli import *  # noqa: F401,F403
from reddit_reconstruction import cli as _runtime
from tools.output_path_safety import OutputPathConflictError

_rollback_committed_outputs = _runtime._rollback_committed_outputs
_write_csv = _runtime._write_csv


def ensure_output_paths_safe(*args: object, **kwargs: object) -> list[Path]:
    try:
        return _runtime.ensure_output_paths_safe(*args, **kwargs)
    except _runtime.OutputPathConflictError as error:
        raise OutputPathConflictError(str(error)) from error


def write_outputs(*args: object, **kwargs: object) -> None:
    original_write_csv = _runtime._write_csv
    _runtime._write_csv = _write_csv
    try:
        _runtime.write_outputs(*args, **kwargs)
    except _runtime.OutputPathConflictError as error:
        raise OutputPathConflictError(str(error)) from error
    finally:
        _runtime._write_csv = original_write_csv


if __name__ == "__main__":
    raise SystemExit(main())
