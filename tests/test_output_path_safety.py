from __future__ import annotations

import unittest
from pathlib import Path

from tools.output_path_safety import (
    OutputPathConflictError,
    atomic_output_path,
    ensure_output_paths_safe,
)


class OutputPathSafetyTest(unittest.TestCase):
    def test_rejects_output_that_matches_any_input(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-output-safety-input-conflict"
        tmp.mkdir(parents=True, exist_ok=True)
        input_path = tmp / "source.csv"
        input_path.write_text("source", encoding="utf-8")

        with self.assertRaisesRegex(OutputPathConflictError, "input file"):
            ensure_output_paths_safe([input_path], [input_path], overwrite=True)

    def test_requires_explicit_overwrite_for_existing_output(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-output-safety-existing"
        tmp.mkdir(parents=True, exist_ok=True)
        output_path = tmp / "result.xlsx"
        output_path.write_text("existing", encoding="utf-8")

        with self.assertRaisesRegex(OutputPathConflictError, "already exists"):
            ensure_output_paths_safe([], [output_path], overwrite=False)

        ensure_output_paths_safe([], [output_path], overwrite=True)

    def test_atomic_output_keeps_existing_file_when_write_fails(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-output-safety-atomic-failure"
        tmp.mkdir(parents=True, exist_ok=True)
        output_path = tmp / "result.xlsx"
        output_path.write_text("existing", encoding="utf-8")

        with self.assertRaisesRegex(RuntimeError, "simulated failure"):
            with atomic_output_path(output_path) as staged_path:
                staged_path.write_text("partial", encoding="utf-8")
                raise RuntimeError("simulated failure")

        self.assertEqual("existing", output_path.read_text(encoding="utf-8"))
        self.assertEqual([], list(tmp.glob(".result.*.tmp.xlsx")))

    def test_atomic_output_replaces_target_only_after_success(self) -> None:
        tmp = Path.cwd() / ".tmp-tests" / "case-output-safety-atomic-success"
        tmp.mkdir(parents=True, exist_ok=True)
        output_path = tmp / "result.xlsx"
        output_path.write_text("existing", encoding="utf-8")

        with atomic_output_path(output_path) as staged_path:
            staged_path.write_text("complete", encoding="utf-8")
            self.assertEqual("existing", output_path.read_text(encoding="utf-8"))

        self.assertEqual("complete", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
